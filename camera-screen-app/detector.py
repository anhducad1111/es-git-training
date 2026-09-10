import queue
import numpy as np
from PyQt6.QtCore import QThread
from PyQt6.QtGui import QImage
from ultralytics import YOLO

_model = None


def get_model():
    global _model
    if _model is None:
        _model = YOLO("yolov8n.pt")
    return _model


def qimage_to_numpy(image):
    image = image.convertToFormat(QImage.Format.Format_RGB888)
    ptr = image.bits()
    ptr.setsize(image.sizeInBytes())
    return np.array(ptr).reshape(image.height(), image.width(), 3)


class DetectionThread(QThread):
    def __init__(self):
        super().__init__()
        self._running = False
        self.input_queue = queue.Queue(maxsize=1)
        self.result_queue = queue.Queue(maxsize=1)
        self.enabled = False
        self.confidence = 0.5

    def run(self):
        self._running = True
        model = get_model()
        while self._running:
            if not self.enabled:
                self.msleep(10)
                continue
            try:
                image = self.input_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                arr = qimage_to_numpy(image)
                results = model(arr, conf=self.confidence, verbose=False)
                detections = []
                for r in results:
                    for box in r.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        detections.append({
                            "box": (x1, y1, x2, y2),
                            "label": r.names[int(box.cls[0])],
                            "confidence": float(box.conf[0]),
                        })
                if self.result_queue.full():
                    try:
                        self.result_queue.get_nowait()
                    except queue.Empty:
                        pass
                self.result_queue.put_nowait(detections)
            except Exception:
                pass

    def stop(self):
        self._running = False
        self.wait()
