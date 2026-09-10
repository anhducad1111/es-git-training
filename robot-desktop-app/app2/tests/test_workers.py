import warnings

import cv2
import numpy as np

from esp32_mjpeg_detector import workers
from esp32_mjpeg_detector.detectors import Detection, NullDetector
from esp32_mjpeg_detector.latest_frame import LatestFrame
from esp32_mjpeg_detector.workers import FramePacket, decode_jpeg


def test_decode_jpeg_returns_bgr_image_and_timestamp():
    image = np.zeros((3, 4, 3), dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok

    decoded = decode_jpeg(encoded.tobytes(), timestamp=12.5)

    assert decoded is not None
    assert decoded.image.shape[:2] == (3, 4)
    assert decoded.timestamp == 12.5


def test_decode_jpeg_drops_frame_when_turbojpeg_only_warns(monkeypatch):
    # libjpeg-turbo reports a truncated/corrupt frame as a recoverable
    # warning and still returns a (garbage) decoded image instead of
    # raising. decode_jpeg must not treat that as a successful decode.
    class WarningOnlyTurboJpeg:
        def decode(self, data):
            warnings.warn("Corrupt JPEG data: premature end of data segment")
            return np.zeros((3, 4, 3), dtype=np.uint8)

    monkeypatch.setattr(workers, "_turbojpeg", WarningOnlyTurboJpeg())

    decoded = decode_jpeg(b"not a real jpeg", timestamp=1.0)

    assert decoded is None


def test_null_detector_returns_no_boxes():
    result = NullDetector().detect(np.zeros((4, 4, 3), dtype=np.uint8))

    assert result == Detection([], [], [])


def test_frame_packet_can_be_handed_through_latest_slot():
    slot = LatestFrame[FramePacket]()
    packet = FramePacket(np.zeros((1, 1, 3), dtype=np.uint8), 1.0)
    slot.put(packet)

    assert slot.get(timeout=0.1) is packet
