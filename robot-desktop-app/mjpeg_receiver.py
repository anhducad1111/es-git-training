import time
import requests
from collections import deque
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QPixmap


class LatestSlot:
    def __init__(self):
        self._item = None
        self._has_item = False
        self._lock = __import__('threading').Lock()
    
    def publish(self, item):
        with self._lock:
            self._item = item
            self._has_item = True
    
    def take(self):
        with self._lock:
            if self._has_item:
                item = self._item
                self._item = None
                self._has_item = False
                return item
            return None


class ReceiveThread(QThread):
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, stream_url, raw_slot):
        super().__init__()
        self.stream_url = stream_url
        self.raw_slot = raw_slot
        self._running = False

    def run(self):
        self._running = True
        while self._running:
            try:
                response = requests.get(
                    self.stream_url,
                    stream=True,
                    timeout=(5, 30)
                )
                if response.status_code == 200:
                    self.connected.emit()
                    self._receive(response)
                else:
                    self.error.emit(f"HTTP {response.status_code}")
            except requests.exceptions.Timeout:
                self.error.emit("Connection timeout")
            except requests.exceptions.ConnectionError:
                self.error.emit("Connection failed")
            except Exception as e:
                self.error.emit(str(e)[:80])
            finally:
                self.disconnected.emit()

            if self._running:
                self.msleep(2000)

    def _receive(self, response):
        buf = b""
        for chunk in response.iter_content(chunk_size=4096):
            if not self._running:
                break
            buf += chunk
            while len(buf) > 2:
                soi = buf.find(b"\xff\xd8")
                if soi == -1:
                    buf = b""
                    break
                if soi > 0:
                    buf = buf[soi:]
                eoi = buf.find(b"\xff\xd9", 2)
                if eoi == -1:
                    if len(buf) > 100000:
                        buf = buf[-100:]
                    break
                jpeg = buf[:eoi + 2]
                buf = buf[eoi + 2:]
                if len(jpeg) > 500:
                    self.raw_slot.publish(jpeg)

    def stop(self):
        self._running = False
        self.wait()


class DecodeThread(QThread):
    def __init__(self, raw_slot, display_slot):
        super().__init__()
        self.raw_slot = raw_slot
        self.display_slot = display_slot
        self._running = False

    def run(self):
        self._running = True
        while self._running:
            raw = self.raw_slot.take()
            if raw:
                pixmap = QPixmap()
                pixmap.loadFromData(raw, "JPEG")
                if not pixmap.isNull():
                    self.display_slot.publish(pixmap)
            else:
                self.msleep(5)

    def stop(self):
        self._running = False
        self.wait()


class MJPEGReceiver:
    def __init__(self, stream_url):
        self.raw_slot = LatestSlot()
        self.display_slot = LatestSlot()
        self.receive_thread = ReceiveThread(stream_url, self.raw_slot)
        self.decode_thread = DecodeThread(self.raw_slot, self.display_slot)
        self.connected = self.receive_thread.connected
        self.disconnected = self.receive_thread.disconnected
        self.error = self.receive_thread.error

    def start(self):
        self.decode_thread.start()
        self.receive_thread.start()

    def take_frame(self):
        return self.display_slot.take()

    def stop(self):
        self.receive_thread.stop()
        self.decode_thread.stop()