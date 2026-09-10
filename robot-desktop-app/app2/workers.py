from __future__ import annotations

import os
import threading
import time
import urllib.parse
import urllib.request
import warnings
from dataclasses import dataclass
from time import monotonic
from typing import Callable

import cv2
import numpy as np

from .detectors import Detection, Detector
from .latest_frame import LatestFrame
from .mjpeg import MjpegParser


def set_camera_quality(stream_url: str, value: int, timeout: float = 3.0) -> bool:
    """Best-effort call to the ESP32-Cam's GET /api/quality?val={0-63} endpoint.

    Lower value = higher quality/larger frames; higher value = more compression.
    Fast motion in the scene can spike individual JPEG frame sizes enough to
    destabilize the stream over Wi-Fi; raising this trades a bit of image
    quality for smaller, more consistent frame sizes. Silently returns False
    on any failure (wrong host, endpoint missing, etc.) since this is a
    non-essential tuning step, not required for the stream itself to work.
    """
    parsed = urllib.parse.urlsplit(stream_url)
    quality_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "/api/quality", f"val={value}", ""))
    try:
        with urllib.request.urlopen(quality_url, timeout=timeout):
            return True
    except Exception:
        return False

# Well-known install locations for libjpeg-turbo's shared library on Windows,
# in case it isn't on PATH. Override with the TURBOJPEG_LIB_PATH env var if
# it's installed somewhere else.
_TURBOJPEG_LIB_CANDIDATES = [
    r"C:\libjpeg-turbo-gcc64\bin\libturbojpeg.dll",
    r"C:\libjpeg-turbo64\bin\turbojpeg.dll",
]


def _load_turbojpeg():
    from turbojpeg import TurboJPEG

    lib_path = os.environ.get("TURBOJPEG_LIB_PATH")
    if lib_path:
        return TurboJPEG(lib_path)
    for candidate in _TURBOJPEG_LIB_CANDIDATES:
        if os.path.isfile(candidate):
            return TurboJPEG(candidate)
    return TurboJPEG()


try:
    _turbojpeg = _load_turbojpeg()
except Exception:
    # PyTurboJPEG not installed, or the shared library it wraps couldn't be
    # found/loaded. Fall back to OpenCV's decoder below.
    _turbojpeg = None


@dataclass
class FramePacket:
    image: np.ndarray
    timestamp: float
    detection: Detection | None = None


def decode_jpeg(data: bytes, timestamp: float | None = None) -> FramePacket | None:
    image = None
    if _turbojpeg is not None:
        try:
            # libjpeg-turbo treats a truncated/corrupt frame (frequent on
            # ESP32-Cam streams, e.g. Wi-Fi hiccups mid-frame) as a
            # recoverable warning rather than an error: __report_error()
            # calls warnings.warn() and still returns whatever partial image
            # it decoded, instead of raising. Left unchecked, that silently
            # feeds a corrupted frame into detection/calibration. Promoting
            # warnings to exceptions here makes decode_jpeg treat that case
            # the same as any other decode failure (falls through to the
            # cv2 decoder, then to dropping the frame).
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                image = _turbojpeg.decode(data)
        except Exception:
            image = None
    if image is None:
        image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        return None
    return FramePacket(image=image, timestamp=monotonic() if timestamp is None else timestamp)


def publish_frame(packet: FramePacket, *outputs: LatestFrame[FramePacket]) -> None:
    """Publish one captured frame to all consumers without buffering history."""
    for output in outputs:
        output.put(packet)


class CaptureWorker:
    """Splits network I/O and JPEG decoding into separate threads.

    The network thread only reads bytes and hands the newest raw JPEG to a
    capacity-one slot; it never waits on decode. The decode thread always
    decodes whatever is currently newest, dropping any frame that arrived
    and was overwritten before it got to it. This keeps socket reads from
    ever stalling behind CPU-bound decode work, which is what let backlog
    (and therefore latency) build up when both were done in one thread.
    """

    def __init__(
        self,
        url: str,
        output: LatestFrame[FramePacket],
        *additional_outputs: LatestFrame[FramePacket],
        status: Callable[[str], None] | None = None,
        reconnect_delay: float = 1.0,
        quality: int | None = None,
    ) -> None:
        self.url = url
        self.output = output
        self.additional_outputs = additional_outputs
        self.status = status or (lambda message: None)
        self.reconnect_delay = reconnect_delay
        self.quality = quality
        self._stop = threading.Event()
        self._raw_slot: LatestFrame[bytes] = LatestFrame()
        self._network_thread: threading.Thread | None = None
        self._decode_thread: threading.Thread | None = None

    def start(self) -> None:
        self._network_thread = threading.Thread(target=self._run_network, name="mjpeg-network", daemon=True)
        self._decode_thread = threading.Thread(target=self._run_decode, name="mjpeg-decode", daemon=True)
        self._network_thread.start()
        self._decode_thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._raw_slot.close()
        self.output.close()
        if self._network_thread:
            self._network_thread.join(timeout=2)
        if self._decode_thread:
            self._decode_thread.join(timeout=2)

    def _run_network(self) -> None:
        while not self._stop.is_set():
            try:
                self.status(f"Connecting: {self.url}")
                if self.quality is not None:
                    set_camera_quality(self.url, self.quality)
                request = urllib.request.Request(self.url, headers={"Cache-Control": "no-cache"})
                with urllib.request.urlopen(request, timeout=5) as response:
                    parser = MjpegParser()
                    self.status("Receiving")
                    # response.read(n) blocks until n bytes have arrived (it's
                    # backed by io.BufferedReader), which can silently coalesce
                    # several MJPEG frames' worth of network time into one
                    # call. read1() returns as soon as any data is available
                    # (at most one underlying socket read), matching how a
                    # browser consumes the same stream with low latency.
                    fp = getattr(response, "fp", None)
                    read1 = fp.read1 if not getattr(response, "chunked", False) and hasattr(fp, "read1") else None
                    while not self._stop.is_set():
                        data = read1(64 * 1024) if read1 else response.read(64 * 1024)
                        if not data:
                            raise ConnectionError("stream ended")
                        frames = parser.feed(data)
                        if frames:
                            # Only the newest frame matters; put() is a cheap,
                            # non-blocking overwrite so this loop never waits
                            # on the decode thread.
                            self._raw_slot.put(frames[-1])
            except Exception as exc:  # network implementations expose varied exception types
                if not self._stop.is_set():
                    self.status(f"Reconnecting: {exc}")
                    self._stop.wait(self.reconnect_delay)

    def _run_decode(self) -> None:
        while not self._stop.is_set():
            jpeg = self._raw_slot.get(timeout=0.2)
            if jpeg is None:
                continue
            packet = decode_jpeg(jpeg)
            if packet:
                publish_frame(packet, self.output, *self.additional_outputs)


class InferenceWorker:
    def __init__(
        self,
        input_slot: LatestFrame[FramePacket],
        output: LatestFrame[FramePacket],
        detector: Detector,
        status: Callable[[str], None] | None = None,
    ) -> None:
        self.input = input_slot
        self.output = output
        self.detector = detector
        self.status = status or (lambda message: None)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self.run, name="object-inference", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self.input.close()
        self.output.close()
        if self._thread:
            self._thread.join(timeout=2)

    def run(self) -> None:
        while not self._stop.is_set():
            packet = self.input.get(timeout=0.2)
            if packet is None:
                continue
            try:
                packet.detection = self.detector.detect(packet.image)
                self.output.put(packet)
            except Exception as exc:
                self.status(f"Inference error: {exc}")
