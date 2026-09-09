import threading
import time
import requests
from collections import deque
from PyQt6.QtCore import QThread, pyqtSignal, Qt
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
        self._response = None
        self._response_lock = threading.Lock()
        self._skip_backoff = threading.Event()

    def run(self):
        self._running = True
        while self._running:
            try:
                response = requests.get(
                    self.stream_url,
                    stream=True,
                    timeout=(5, 30)
                )
                with self._response_lock:
                    self._response = response
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
                with self._response_lock:
                    self._response = None
                self.disconnected.emit()

            if self._running:
                if self._skip_backoff.is_set():
                    self._skip_backoff.clear()
                else:
                    self.msleep(2000)

    def set_stream_url(self, url):
        """Switch to a new stream URL (e.g. resolution change) without
        tearing down and re-wiring the thread's signals. Aborts any
        in-flight request so the switch takes effect immediately instead
        of waiting for the next timeout/retry."""
        self.stream_url = url
        self._skip_backoff.set()
        with self._response_lock:
            response = self._response
        if response is not None:
            try:
                response.close()
            except Exception:
                pass

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
    frame_ready = pyqtSignal()

    def __init__(self, raw_slot, display_slot):
        super().__init__()
        self.raw_slot = raw_slot
        self.display_slot = display_slot
        self._running = False
        self._recv_count = 0
        self._drop_count = 0
        self._last_stats_time = time.time()
        self._frame_times = deque(maxlen=60)
        self._target_size_lock = threading.Lock()
        self._target_size = None

    def set_target_size(self, width, height):
        """Display size to pre-scale decoded frames to. Doing this here
        (QImage is thread-safe) keeps the expensive smooth-resize off the
        GUI thread - it only has to do a cheap QPixmap::fromImage after."""
        with self._target_size_lock:
            self._target_size = (max(1, width), max(1, height))

    def run(self):
        self._running = True
        while self._running:
            raw = self.raw_slot.wait_and_take(timeout=0.5)
            if raw:
                image = QImage()
                image.loadFromData(raw, "JPEG")
                if not image.isNull():
                    with self._target_size_lock:
                        target = self._target_size
                    if target is not None:
                        image = image.scaled(
                            target[0],
                            target[1],
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    self.display_slot.publish(image)
                    self.frame_ready.emit()
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
    # Hardware resolutions the ESP32-Cam firmware serves (API doc §3.1).
    SUPPORTED_RESOLUTIONS = [
        (320, 240),
        (640, 480),
        (800, 600),
        (1024, 768),
        (1600, 1200),
    ]

    # Fixed streaming endpoint used by test-bench ESP32-Cam boards running
    # the stock AI-Thinker firmware (no per-resolution URLs, no quality API).
    TEST_MODE_PORT = 81
    TEST_MODE_PATH = "/stream"

    def __init__(self, cam_ip, width=640, height=480, test_mode=False):
        self.cam_ip = cam_ip
        self.width = width
        self.height = height
        self.test_mode = test_mode
        self.raw_slot = LatestSlot()
        self.display_slot = LatestSlot()
        self.receive_thread = ReceiveThread(self._build_url(width, height), self.raw_slot)
        self.decode_thread = DecodeThread(self.raw_slot, self.display_slot)
        self.connected = self.receive_thread.connected
        self.disconnected = self.receive_thread.disconnected
        self.error = self.receive_thread.error
        self.stats_updated = self.decode_thread.stats_updated
        self.frame_ready = self.decode_thread.frame_ready

    def _build_url(self, width, height):
        if self.test_mode:
            return f"http://{self.cam_ip}:{self.TEST_MODE_PORT}{self.TEST_MODE_PATH}"
        return f"http://{self.cam_ip}/{width}x{height}.mjpeg"

    def set_test_mode(self, enabled):
        self.test_mode = enabled
        self.receive_thread.set_stream_url(self._build_url(self.width, self.height))

    def set_resolution(self, width, height):
        self.width = width
        self.height = height
        self.receive_thread.set_stream_url(self._build_url(width, height))

    def set_target_size(self, width, height):
        self.decode_thread.set_target_size(width, height)

    def start(self):
        self.decode_thread.start()
        self.receive_thread.start()

    def take_frame(self):
        return self.display_slot.take()

    def stop(self):
        self.receive_thread.stop()
        self.decode_thread.stop()
