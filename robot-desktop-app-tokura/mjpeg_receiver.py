import re
import threading
import time
import urllib.parse
import urllib.request
import requests
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtGui import QImage


class MjpegParser:
    """Incrementally extracts JPEG payloads from a multipart MJPEG stream.

    Parses the actual multipart Content-Length header for each part instead
    of scanning raw bytes for JPEG SOI/EOI markers, which is the correct way
    to find frame boundaries in this format.
    """

    _length_re = re.compile(rb"(?:^|\r\n)content-length\s*:\s*(\d+)\s*(?:\r\n|$)", re.I)

    def __init__(self, max_frame_bytes=8 * 1024 * 1024):
        self.max_frame_bytes = max_frame_bytes
        self._buffer = bytearray()
        self._expected = None

    def feed(self, data):
        self._buffer.extend(data)
        frames = []
        while True:
            if self._expected is None:
                header_end = self._buffer.find(b"\r\n\r\n")
                if header_end < 0:
                    if len(self._buffer) > 64 * 1024:
                        self._buffer = self._buffer[-4096:]
                    break
                header = bytes(self._buffer[: header_end + 4])
                del self._buffer[: header_end + 4]
                match = self._length_re.search(header)
                if not match:
                    continue
                self._expected = int(match.group(1))
                if not 0 < self._expected <= self.max_frame_bytes:
                    self._expected = None
                    continue
            if len(self._buffer) < self._expected:
                break
            frames.append(bytes(self._buffer[: self._expected]))
            del self._buffer[: self._expected]
            self._expected = None
            while self._buffer.startswith(b"\r\n"):
                del self._buffer[:2]
        return frames


def set_camera_quality(stream_url, value, timeout=3.0):
    """Best-effort call to the ESP32-Cam's GET /api/quality?val={0-63} endpoint.

    Lower value = higher quality/larger frames; higher value = more
    compression. Called on every (re)connect so the configured quality
    survives an ESP32 reboot (which resets it to firmware default).
    """
    parsed = urllib.parse.urlsplit(stream_url)
    quality_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "/api/quality", f"val={value}", ""))
    try:
        requests.get(quality_url, timeout=timeout)
        return True
    except Exception:
        return False


class LatestSlot:
    def __init__(self):
        self._item = None
        self._has_item = False
        self._lock = threading.Lock()
        self._event = threading.Event()

    def publish(self, item):
        with self._lock:
            self._item = item
            self._has_item = True
        self._event.set()

    def take(self):
        with self._lock:
            if self._has_item:
                item = self._item
                self._item = None
                self._has_item = False
                self._event.clear()
                return item
            return None

    def wait_and_take(self, timeout=None):
        if self._event.wait(timeout):
            return self.take()
        return None


class ReceiveThread(QThread):
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error = pyqtSignal(str)
    parser_stats = pyqtSignal(int, int)  # bytes/s, frames/s - diagnostic only

    def __init__(self, stream_url, raw_slot, quality=None):
        super().__init__()
        self.stream_url = stream_url
        self.raw_slot = raw_slot
        self.quality = quality
        self._running = False
        self._bytes_read = 0
        self._frames_parsed = 0
        self._last_parser_stats_time = time.time()

    def run(self):
        self._running = True
        while self._running:
            try:
                if self.quality is not None:
                    set_camera_quality(self.stream_url, self.quality)
                request = urllib.request.Request(
                    self.stream_url, headers={"Cache-Control": "no-cache"}
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    self.connected.emit()
                    self._receive(response)
            except Exception as e:
                self.error.emit(str(e)[:80])
            finally:
                self.disconnected.emit()

            if self._running:
                self.msleep(2000)

    def _receive(self, response):
        parser = MjpegParser()
        # response.read(n) blocks until n bytes have arrived, which can
        # silently coalesce several MJPEG frames' worth of network time
        # into one call. read1() returns as soon as any data is available
        # (at most one underlying socket read), matching how a browser
        # consumes the same stream with low latency.
        fp = getattr(response, "fp", None)
        read1 = fp.read1 if not getattr(response, "chunked", False) and hasattr(fp, "read1") else None
        while self._running:
            data = read1(64 * 1024) if read1 else response.read(64 * 1024)
            if not data:
                raise ConnectionError("stream ended")
            self._bytes_read += len(data)
            frames = parser.feed(data)
            if frames:
                self._frames_parsed += len(frames)
                # Only the newest frame matters - always overwrite so a
                # slow decode never leaves a stale frame stuck in the slot.
                self.raw_slot.publish(frames[-1])

            now = time.time()
            if now - self._last_parser_stats_time >= 1.0:
                self.parser_stats.emit(self._bytes_read, self._frames_parsed)
                self._bytes_read = 0
                self._frames_parsed = 0
                self._last_parser_stats_time = now

    def stop(self):
        self._running = False
        self.wait()


class DecodeThread(QThread):
    def __init__(self, raw_slot, display_slot):
        super().__init__()
        self.raw_slot = raw_slot
        self.display_slot = display_slot
        self._running = False

    def run(self):
        self._running = True
        while self._running:
            raw = self.raw_slot.wait_and_take(timeout=0.1)
            if raw:
                # Skip if another frame is already waiting
                if self.raw_slot._has_item:
                    continue

                image = QImage()
                image.loadFromData(raw, "JPEG")
                if not image.isNull():
                    # Tag with the decode time so the display side can
                    # compute latency (time from decode to actually being
                    # shown on screen), matching esp32_mjpeg_detector's
                    # FramePacket.timestamp approach.
                    self.display_slot.publish((image, time.time()))

    def stop(self):
        self._running = False
        self.wait()


class PingThread(QThread):
    """Measures stream latency independently of decoding.

    Runs its own HEAD request loop on a dedicated thread so a slow or
    stalled response never blocks DecodeThread from processing frames
    (a HEAD request sharing the busy ESP32-CAM connection was previously
    issued from inside the decode loop, which visibly stalled the video
    once per second while waiting for it).
    """
    ping_updated = pyqtSignal(float)

    def __init__(self, stream_url, interval_s=1.0):
        super().__init__()
        self._stream_url = stream_url
        self._interval_s = interval_s
        self._running = False

    def run(self):
        self._running = True
        while self._running:
            ping_ms = 0.0
            if self._stream_url:
                try:
                    start = time.time()
                    requests.head(self._stream_url, timeout=2)
                    ping_ms = (time.time() - start) * 1000
                except Exception:
                    ping_ms = 0.0
            self.ping_updated.emit(round(ping_ms, 1))
            self.msleep(int(self._interval_s * 1000))

    def stop(self):
        self._running = False
        self.wait()


class MJPEGReceiver(QObject):
    stats_updated = pyqtSignal(dict)

    def __init__(self, stream_url, quality=None):
        super().__init__()
        self.raw_slot = LatestSlot()
        self.display_slot = LatestSlot()
        self.receive_thread = ReceiveThread(stream_url, self.raw_slot, quality=quality)
        self.decode_thread = DecodeThread(self.raw_slot, self.display_slot)
        self.ping_thread = PingThread(stream_url)
        self.connected = self.receive_thread.connected
        self.disconnected = self.receive_thread.disconnected
        self.error = self.receive_thread.error
        self.parser_stats = self.receive_thread.parser_stats

        self.ping_thread.ping_updated.connect(self._on_ping)

    def _on_ping(self, ping_ms):
        self.stats_updated.emit({"ping_ms": ping_ms})

    def start(self):
        self.decode_thread.start()
        self.receive_thread.start()
        self.ping_thread.start()

    def take_frame(self):
        return self.display_slot.take()

    def stop(self):
        self.receive_thread.stop()
        self.decode_thread.stop()
        self.ping_thread.stop()