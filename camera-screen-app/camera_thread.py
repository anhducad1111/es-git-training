import queue
from PyQt6.QtCore import QThread
from PyQt6.QtGui import QImage
import urllib.request

MAX_QUEUE_SIZE = 1


class CameraThread(QThread):
    def __init__(self, url):
        super().__init__()
        self.url = url
        self._running = False
        self._stream = None
        self.frame_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        self.connected = False
        self.error_msg = None

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

                        image = QImage()
                        image.loadFromData(jpeg_data, "JPEG")
                        if not image.isNull():
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
