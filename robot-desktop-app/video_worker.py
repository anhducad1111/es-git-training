import queue
import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QImage, QPixmap


class VideoWorker(QThread):
    frame_ready = pyqtSignal(object, object)

    def __init__(self):
        super().__init__()
        self._running = True
        self._frame_queue = queue.Queue(maxsize=2)

    def push_frame(self, jpeg_bytes):
        if self._frame_queue.full():
            try:
                self._frame_queue.get_nowait()
            except queue.Empty:
                pass
        self._frame_queue.put_nowait(jpeg_bytes)

    def stop(self):
        self._running = False
        self.wait()

    def run(self):
        while self._running:
            try:
                jpeg_bytes = self._frame_queue.get(timeout=0.05)
            except queue.Empty:
                continue

            nparr = np.frombuffer(jpeg_bytes, np.uint8)
            bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if bgr is None:
                continue

            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)

            self.frame_ready.emit(pixmap, bgr)
