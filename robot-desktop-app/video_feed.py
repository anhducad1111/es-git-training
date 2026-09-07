import json
import time
import websocket
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


class VideoReceiverThread(QThread):
    frame_received = pyqtSignal(object)
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error = pyqtSignal(str)
    stats_updated = pyqtSignal(dict)

    def __init__(self, ws_url):
        super().__init__()
        self.ws_url = ws_url
        self._running = False
        self._connected = False
        self._frame_slot = LatestSlot()
        self._drop_count = 0
        self._recv_count = 0
        self._last_stats_time = time.time()
        self._frame_times = []
        self.ws = None

    def run(self):
        self._running = True
        while self._running:
            try:
                self.ws = websocket.WebSocketApp(
                    self.ws_url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )
                self.ws.run_forever()
            except Exception as e:
                if self._running:
                    self.error.emit(str(e)[:80])
            
            finally:
                self._connected = False
                self.disconnected.emit()

            if self._running:
                self.msleep(2000)

    def _on_open(self, ws):
        self._connected = True
        self.connected.emit()

    def _on_message(self, ws, message):
        if isinstance(message, bytes) and len(message) > 500:
            self._recv_count += 1
            now = time.time()
            self._frame_times.append(now)
            if len(self._frame_times) > 60:
                self._frame_times.pop(0)
            
            pixmap = QPixmap()
            pixmap.loadFromData(message, "JPEG")
            if not pixmap.isNull():
                self._frame_slot.publish(pixmap)
            
            if now - self._last_stats_time >= 1.0:
                self._emit_stats()
                self._last_stats_time = now

    def _on_error(self, ws, error):
        if self._running:
            self.error.emit(str(error)[:80])

    def _on_close(self, ws, close_status_code, close_msg):
        pass

    def _emit_stats(self):
        now = time.time()
        fps = 0
        if len(self._frame_times) > 1:
            elapsed = now - self._frame_times[0]
            if elapsed > 0:
                fps = (len(self._frame_times) - 1) / elapsed
        
        self.stats_updated.emit({
            "fps": round(fps, 1),
            "recv_count": self._recv_count,
            "drop_count": self._drop_count,
        })

    def take_frame(self):
        return self._frame_slot.take()

    def stop(self):
        self._running = False
        if self.ws:
            self.ws.close()
        self.wait()
