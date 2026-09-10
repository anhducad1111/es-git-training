import numpy as np

from esp32_mjpeg_detector.latest_frame import LatestFrame
from esp32_mjpeg_detector.workers import FramePacket, publish_frame


def test_publish_frame_fans_out_to_display_and_inference_slots():
    display = LatestFrame[FramePacket]()
    inference = LatestFrame[FramePacket]()
    packet = FramePacket(np.zeros((1, 1, 3), dtype=np.uint8), 1.0)

    publish_frame(packet, display, inference)

    assert display.get(timeout=0.1) is packet
    assert inference.get(timeout=0.1) is packet
