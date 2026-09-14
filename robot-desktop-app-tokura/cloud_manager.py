from datetime import datetime, timezone
from cloud_api import CloudAPI
from cloud_worker import CloudWorker


class CloudManager:
    """Manages cloud API interactions."""
    
    def __init__(self, config, log_callback):
        self._config = config
        self._log = log_callback
        self._cloud_api = None
        self._cloud_workers = []
        self._latest_telemetry = {}
        
    def initialize(self):
        """Initialize cloud API."""
        self._cloud_api = CloudAPI()
        self.test_connection()
        
    def test_connection(self):
        """Test cloud API connection."""
        if not self._cloud_api:
            return
            
        url = f"{self._cloud_api._base_url}/rovers"
        worker = CloudWorker("GET", url)
        worker.result.connect(self._on_test_success)
        worker.error.connect(self._on_test_error)
        self._cloud_workers.append(worker)
        worker.finished.connect(lambda: self._remove_worker(worker))
        worker.start()
        
    def _on_test_success(self, data):
        self._log("CLOUD", f"Connected to cloud API OK - {self._cloud_api._base_url}")
        
    def _on_test_error(self, error):
        if "timed out" in error or "ConnectTimeout" in error:
            self._log("CLOUD", f"Server offline (timeout) - {self._cloud_api._base_url}")
        elif "NameResolutionError" in error or "resolve" in error:
            self._log("CLOUD", f"Cannot resolve hostname - {self._cloud_api._base_url}")
        else:
            self._log("CLOUD", f"Connection failed: {error}")
            
    def send_telemetry(self, data):
        """Send telemetry data to cloud."""
        if not self._cloud_api:
            return
            
        url = f"{self._cloud_api._base_url}/telemetry"
        payload = {
            "device_uid": self._cloud_api._device_uid,
            "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "temperature_c": data.get("temperature", 0),
            "humidity_pct": data.get("humidity", 0),
            "gas_ppm": data.get("gas", 0),
            "distance_cm": data.get("distance", 0),
            "auto_brake": data.get("obstacle", False),
        }
        worker = CloudWorker("POST", url, payload=payload)
        self._cloud_workers.append(worker)
        worker.finished.connect(lambda: self._remove_worker(worker))
        worker.start()
        self._latest_telemetry = data
        
    def _remove_worker(self, worker):
        if worker in self._cloud_workers:
            self._cloud_workers.remove(worker)
            
    def stop_all(self):
        """Stop all cloud workers."""
        for worker in self._cloud_workers:
            if worker.isRunning():
                worker.quit()
                worker.wait(1000)
        self._cloud_workers.clear()
        
    @property
    def cloud_api(self):
        return self._cloud_api
