import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal


class YOLODetector(QThread):
    detected = pyqtSignal(list)
    error = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._running = False
        self._frame = None
        self._lock = False
        self._model = None

    def start_detection(self):
        self._running = True
        try:
            from ultralytics import YOLO
            self._model = YOLO("yolov8m.pt")
            self.status.emit("YOLOv8n loaded OK")
        except Exception as e:
            self.error.emit(f"Failed to load YOLOv8: {e}")
            return
        if not self.isRunning():
            self.start()

    def stop_detection(self):
        self._running = False

    def set_frame(self, frame):
        if not self._lock:
            self._frame = frame

    def run(self):
        while self._running:
            if self._frame is not None and self._model is not None:
                self._lock = True
                try:
                    frame = self._frame.copy()
                    self._lock = False
                    results = self._model(frame, conf=0.5, verbose=False)
                    
                    detections = []
                    for r in results:
                        for box in r.boxes:
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            conf = float(box.conf[0])
                            cls = int(box.cls[0])
                            label = self._model.names[cls]
                            detections.append({
                                "x": x1,
                                "y": y1,
                                "w": x2 - x1,
                                "h": y2 - y1,
                                "confidence": conf,
                                "label": label
                            })
                    self.detected.emit(detections)
                except Exception as e:
                    self._lock = False
                    self.error.emit(str(e)[:100])
            self.msleep(300)
