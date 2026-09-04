import requests
from config import load_config


class CloudAPI:
    def __init__(self):
        self._config = load_config()
        self._base_url = self._config.get("cloud_api_url", "")
        self._device_uid = self._config.get("device_uid", "rover-001")
        self._timeout = 10

    def _url(self, path):
        return f"{self._base_url}{path}"

    def post_telemetry(self, data):
        """POST /api/v1/telemetry - Ingest one telemetry record"""
        payload = {
            "device_uid": self._device_uid,
            "temperature_c": data.get("temperature", 0),
            "humidity_pct": data.get("humidity", 0),
            "gas_ppm": data.get("gas", 0),
            "distance_cm": data.get("distance", 0),
            "auto_brake": data.get("auto_brake", False),
        }
        try:
            resp = requests.post(
                self._url("/telemetry"),
                json=payload,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def get_rovers(self):
        """GET /api/v1/rovers - List known rovers"""
        try:
            resp = requests.get(
                self._url("/rovers"),
                timeout=self._timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def get_latest(self, device_uid=None):
        """GET /api/v1/rovers/{device_uid}/latest - Single latest reading"""
        uid = device_uid or self._device_uid
        try:
            resp = requests.get(
                self._url(f"/rovers/{uid}/latest"),
                timeout=self._timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def get_readings(self, device_uid=None, limit=100, start=None, end=None):
        """GET /api/v1/rovers/{device_uid}/readings - Last N records or time range"""
        uid = device_uid or self._device_uid
        params = {"limit": limit}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        try:
            resp = requests.get(
                self._url(f"/rovers/{uid}/readings"),
                params=params,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def get_summary(self, device_uid=None, granularity="hour", start=None, end=None):
        """GET /api/v1/rovers/{device_uid}/summary - Aggregated statistics"""
        uid = device_uid or self._device_uid
        params = {"granularity": granularity}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        try:
            resp = requests.get(
                self._url(f"/rovers/{uid}/summary"),
                params=params,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            return {"error": str(e)}
