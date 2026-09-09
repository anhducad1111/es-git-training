import requests
from PyQt6.QtCore import QThread, pyqtSignal


class TelemetryPoller(QThread):
    data_received = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, car_ip, interval_ms=1000):
        super().__init__()
        self.car_ip = car_ip
        self.interval_ms = interval_ms
        self._running = False

    def run(self):
        self._running = True
        while self._running:
            try:
                resp = requests.get(f"http://{self.car_ip}/api/telemetry", timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    self.data_received.emit(data)
                else:
                    self.error.emit(f"HTTP {resp.status_code}")
            except requests.exceptions.Timeout:
                self.error.emit("Timeout")
            except requests.exceptions.ConnectionError:
                self.error.emit("Connection failed")
            except Exception as e:
                self.error.emit(str(e))

            self.msleep(self.interval_ms)

    def stop(self):
        self._running = False
        self.wait()
