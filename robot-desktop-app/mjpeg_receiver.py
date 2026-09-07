import threading
import time
import requests
from collections import deque
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage


class LatestSlot:
    def __init__(self):
        self._item = None
        self._has_item = False
        self._lock = threading.Lock()
        self._event = threading.Event()

    def publish(self, item):
        with self._lock:
            self._item = item
            self._has_item = True
        self._event.set()

    def take(self):
        with self._lock:
            if self._has_item:
                item = self._item
                self._item = None
                self._has_item = False
                self._event.clear()
                return item
            return None

    def wait_and_take(self, timeout=None):
        if self._event.wait(timeout):
            return self.take()
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
    stats_updated = pyqtSignal(dict)

    def __init__(self, raw_slot, display_slot):
        super().__init__()
        self.raw_slot = raw_slot
        self.display_slot = display_slot
        self._running = False
        self._recv_count = 0
        self._drop_count = 0
        self._last_stats_time = time.time()
        self._frame_times = deque(maxlen=60)

    def run(self):
        self._running = True
        while self._running:
            raw = self.raw_slot.wait_and_take(timeout=0.5)
            if raw:
                image = QImage()
                image.loadFromData(raw, "JPEG")
                if not image.isNull():
                    self.display_slot.publish(image)
                    self._recv_count += 1
                    self._frame_times.append(time.time())
                else:
                    self._drop_count += 1

                now = time.time()
                if now - self._last_stats_time >= 1.0:
                    self._emit_stats(now)
                    self._last_stats_time = now

    def _emit_stats(self, now):
        fps = 0
        if len(self._frame_times) > 1:
            elapsed = self._frame_times[-1] - self._frame_times[0]
            if elapsed > 0:
                fps = (len(self._frame_times) - 1) / elapsed

        self.stats_updated.emit({
            "fps": round(fps, 1),
            "recv_count": self._recv_count,
            "drop_count": self._drop_count,
        })

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
        self.stats_updated = self.decode_thread.stats_updated

    def start(self):
        self.decode_thread.start()
        self.receive_thread.start()

    def take_frame(self):
        return self.display_slot.take()

    def stop(self):
        self.receive_thread.stop()
        self.decode_thread.stop()