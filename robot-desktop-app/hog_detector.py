import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal


class HOGDetector(QThread):
    detected = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._running = False
        self._frame = None
        self._lock = False

    def start_detection(self):
        self._running = True
        self._hog = cv2.HOGDescriptor()
        self._hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        if not self.isRunning():
            self.start()

    def stop_detection(self):
        self._running = False

    def set_frame(self, frame):
        if not self._lock:
            self._frame = frame

    def run(self):
        while self._running:
            if self._frame is not None:
                self._lock = True
                try:
                    frame = self._frame.copy()
                    self._lock = False
                    boxes, weights = self._hog.detectMultiScale(
                        frame,
                        winStride=(8, 8),
                        padding=(4, 4),
                        scale=1.05
                    )
                    detections = []
                    for (x, y, w, h), weight in zip(boxes, weights):
                        detections.append({
                            "x": int(x),
                            "y": int(y),
                            "w": int(w),
                            "h": int(h),
                            "confidence": float(weight)
                        })
                    self.detected.emit(detections)
                except Exception as e:
                    self._lock = False
                    self.error.emit(str(e)[:100])
            self.msleep(100)
