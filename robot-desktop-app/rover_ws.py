import json
import threading
from PyQt6.QtCore import QThread, pyqtSignal
import websocket


class RoverWebSocket(QThread):
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    message_received = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, ws_url):
        super().__init__()
        self.ws_url = ws_url
        self.ws = None
        self._running = False
        self._connected = False

    def run(self):
        self._running = True
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        self.ws.run_forever()

    def _on_open(self, ws):
        self._connected = True
        self.connected.emit()

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            self.message_received.emit(data)
        except json.JSONDecodeError:
            pass

    def _on_error(self, ws, error):
        self._connected = False
        self.error.emit(str(error))

    def _on_close(self, ws, close_status_code, close_msg):
        self._connected = False
        self.disconnected.emit()

    def send(self, command):
        if self.ws and self._connected:
            try:
                self.ws.send(command)
            except Exception as e:
                self.error.emit(str(e))

    def stop(self):
        self._running = False
        if self.ws:
            self.ws.close()
        self.wait()

    @property
    def is_connected(self):
        return self._connected
