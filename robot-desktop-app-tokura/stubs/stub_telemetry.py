import random
import time
from PyQt6.QtCore import QThread, pyqtSignal


class StubTelemetryThread(QThread):
    data_received = pyqtSignal(dict)

    def __init__(self, interval=1.0):
        super().__init__()
        self.interval = interval
        self._running = False
        self._temperature = 25.0
        self._humidity = 60.0
        self._distance = 50.0
        self._gas = 400.0

    def run(self):
        self._running = True
        while self._running:
            self._temperature += random.uniform(-0.5, 0.5)
            self._temperature = max(15.0, min(40.0, self._temperature))

            self._humidity += random.uniform(-1.0, 1.0)
            self._humidity = max(30.0, min(90.0, self._humidity))

            self._distance += random.uniform(-5.0, 5.0)
            self._distance = max(5.0, min(200.0, self._distance))

            self._gas += random.uniform(-20.0, 20.0)
            self._gas = max(200.0, min(800.0, self._gas))

            data = {
                "temperature": round(self._temperature, 1),
                "humidity": round(self._humidity, 1),
                "distance": round(self._distance, 1),
                "gas": round(self._gas, 0),
                "link_quality": random.randint(85, 99),
                "battery_voltage": round(random.uniform(11.8, 12.6), 1),
                "timestamp": time.time(),
            }
            self.data_received.emit(data)
            time.sleep(self.interval)

    def stop(self):
        self._running = False
        self.wait()
