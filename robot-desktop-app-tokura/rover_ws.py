import json
import queue
import threading
import time
from PyQt6.QtCore import QThread, pyqtSignal
import websocket


class RoverWebSocket(QThread):
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    message_received = pyqtSignal(dict)
    error = pyqtSignal(str)

    # Commands older than this were queued during a stall/disconnect and no
    # longer reflect the operator's intent - drop them instead of firing a
    # burst of stale motion once the link recovers.
    STALE_COMMAND_S = 0.3

    # How often the current motion state is re-sent even if nothing changed.
    # This is a safety net: if a single command was lost to RF interference
    # while driving, the rover self-corrects within this window instead of
    # continuing on whatever it last received.
    MOTION_HEARTBEAT_S = 0.5

    def __init__(self, ws_url):
        super().__init__()
        self.ws_url = ws_url
        self.ws = None
        self._running = False
        self._connected = False
        self._send_queue = queue.Queue(maxsize=100)
        self._send_thread = None
        self._motion_lock = threading.Lock()
        self._desired_motion = "stop"

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
                    self.error.emit(str(e))
            finally:
                self._connected = False

            if self._running:
                self.msleep(2000)

    def _on_open(self, ws):
        self._connected = True
        self.connected.emit()
        self._send_thread = threading.Thread(target=self._sender_loop, daemon=True)
        self._send_thread.start()
        # Reassert our current intent immediately. If the operator released
        # a key (or hit E-STOP) while we were disconnected, self._desired_motion
        # already reflects that - send it now instead of leaving the rover on
        # whatever command it last received before the drop.
        with self._motion_lock:
            motion = self._desired_motion
        self._send_now(motion)

    def _send_now(self, command):
        try:
            if self.ws and self._connected:
                self.ws.send(command)
        except Exception as e:
            if self._connected:
                self.error.emit(str(e))

    def _sender_loop(self):
        last_heartbeat = time.time()
        while self._connected:
            try:
                queued_at, cmd = self._send_queue.get(timeout=0.1)
                if time.time() - queued_at <= self.STALE_COMMAND_S:
                    self._send_now(cmd)
            except queue.Empty:
                pass

            now = time.time()
            if now - last_heartbeat >= self.MOTION_HEARTBEAT_S:
                with self._motion_lock:
                    motion = self._desired_motion
                self._send_now(motion)
                last_heartbeat = now

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            self.message_received.emit(data)
        except json.JSONDecodeError:
            pass

    def _on_error(self, ws, error):
        self._connected = False
        if self._running:
            self.error.emit(str(error))

    def _on_close(self, ws, close_status_code, close_msg):
        self._connected = False
        self.disconnected.emit()

    def send(self, command):
        if self._connected:
            try:
                self._send_queue.put_nowait((time.time(), command))
            except queue.Full:
                pass

    def set_motion(self, command):
        """Use for directional/E-STOP commands ("forward", "stop", ...).
        Tracks the operator's current intent so it survives a disconnect and
        gets re-sent on reconnect and on a fixed heartbeat, instead of only
        firing once and hoping the single packet arrives."""
        with self._motion_lock:
            self._desired_motion = command
        self.send(command)

    def stop(self):
        self._running = False
        if self.ws:
            self.ws.close()
        self.wait()

    @property
    def is_connected(self):
        return self._connected
