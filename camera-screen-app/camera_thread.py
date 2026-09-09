import time
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage
import urllib.request


class CameraThread(QThread):
    frame_received = pyqtSignal(QImage)
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url
        self._running = False
        self._stream = None

    def run(self):
        self._running = True
        while self._running:
            try:
                req = urllib.request.Request(self.url)
                self._stream = urllib.request.urlopen(req, timeout=10)
                self.connected.emit()

                buffer = b""
                while self._running:
                    chunk = self._stream.read(1024)
                    if not chunk:
                        break
                    buffer += chunk

                    # Find JPEG boundaries
                    start = buffer.find(b"\xff\xd8")
                    end = buffer.find(b"\xff\xd9")

                    if start != -1 and end != -1:
                        jpeg_data = buffer[start : end + 2]
                        buffer = buffer[end + 2 :]

                        image = QImage()
                        image.loadFromData(jpeg_data, "JPEG")
                        if not image.isNull():
                            self.frame_received.emit(image)

            except Exception as e:
                if self._running:
                    self.error.emit(str(e)[:100])

            finally:
                if self._stream:
                    try:
                        self._stream.close()
                    except:
                        pass
                    self._stream = None
                self.disconnected.emit()

            if self._running:
                self.msleep(2000)

    def stop(self):
        self._running = False
        if self._stream:
            try:
                self._stream.close()
            except:
                pass
        self.wait()
