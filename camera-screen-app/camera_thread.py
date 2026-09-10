import queue
import cv2
import numpy as np
from PyQt6.QtCore import QThread
from PyQt6.QtGui import QImage
import urllib.request

MAX_QUEUE_SIZE = 1


class CameraThread(QThread):
    def __init__(self, url, target_size=None):
        super().__init__()
        self.url = url
        self._running = False
        self._stream = None
        self.frame_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        self.connected = False
        self.error_msg = None
        self.target_size = target_size

    def run(self):
        self._running = True
        while self._running:
            try:
                req = urllib.request.Request(self.url)
                self._stream = urllib.request.urlopen(req, timeout=10)
                self.connected = True
                self.error_msg = None

                buf = bytearray()
                while self._running:
                    chunk = self._stream.read(4096)
                    if not chunk:
                        break
                    buf.extend(chunk)

                    while True:
                        start = buf.find(b"\xff\xd8")
                        if start == -1:
                            buf.clear()
                            break
                        end = buf.find(b"\xff\xd9", start + 2)
                        if end == -1:
                            if start > 0:
                                buf = buf[start:]
                            break

                        jpeg_data = bytes(buf[start : end + 2])
                        buf = buf[end + 2 :]

                        nparr = np.frombuffer(jpeg_data, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        if frame is None:
                            continue

                        if self.target_size:
                            frame = cv2.resize(frame, self.target_size, interpolation=cv2.INTER_LINEAR)

                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        h, w, ch = frame.shape
                        bytes_per_line = ch * w
                        image = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()

                        if self.frame_queue.full():
                            try:
                                self.frame_queue.get_nowait()
                            except queue.Empty:
                                pass
                        self.frame_queue.put_nowait(image)

            except Exception as e:
                if self._running:
                    self.error_msg = str(e)[:100]

            finally:
                if self._stream:
                    try:
                        self._stream.close()
                    except:
                        pass
                    self._stream = None
                self.connected = False

            if self._running:
                self.msleep(1000)

    def stop(self):
        self._running = False
        if self._stream:
            try:
                self._stream.close()
            except:
                pass
        self.wait()
