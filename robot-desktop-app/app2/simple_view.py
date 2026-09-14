"""Minimal OpenCV viewer: connect to the ESP32-Cam MJPEG stream and show it.

Usage:
    python -m esp32_mjpeg_detector.simple_view [url] [quality]

quality (0-63, optional) is sent to the camera's /api/quality endpoint before
connecting. Higher = more compression/smaller frames, which reduces the
frame-size spikes that destabilize the stream during fast motion.

Press 'q' to quit.
"""

import sys

import cv2

from .workers import set_camera_quality

DEFAULT_URL = "http://192.168.4.1/640x480.mjpeg"


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    if len(sys.argv) > 2:
        quality = int(sys.argv[2])
        if set_camera_quality(url, quality):
            print(f"Set JPEG quality to {quality}")
        else:
            print(f"Could not set JPEG quality (continuing anyway)")
    cap = cv2.VideoCapture(url)
    if not cap.isOpened():
        print(f"Failed to open stream: {url}")
        return 1

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Stream ended or read failed")
                break
            cv2.imshow("ESP32-Cam", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
