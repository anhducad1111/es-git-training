import requests
from datetime import datetime, timezone
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
        """POST /telemetry - Ingest one telemetry record"""
        payload = {
            "device_uid": self._device_uid,
            "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
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
        """GET /rovers - List known rovers"""
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
        """GET /rovers/{uid}/latest - Single latest reading"""
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

    def get_readings(self, device_uid=None, limit=100, start=None, end=None, order=None):
        """GET /rovers/{uid}/readings - Last N records or time range"""
        uid = device_uid or self._device_uid
        params = {"limit": limit}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        if order:
            params["order"] = order
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

    def get_summary(self, device_uid=None, granularity="day", start=None, end=None):
        """GET /rovers/{uid}/summary - Aggregated statistics"""
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

    def get_health(self):
        """GET /health - Service and database health"""
        try:
            resp = requests.get(
                self._url("/health"),
                timeout=self._timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def get_system(self):
        """GET /system - Gateway host metrics"""
        try:
            resp = requests.get(
                self._url("/system"),
                timeout=self._timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def get_media(self, device_uid=None):
        """GET /rovers/{uid}/media - List snapshots"""
        uid = device_uid or self._device_uid
        try:
            resp = requests.get(
                self._url(f"/rovers/{uid}/media"),
                timeout=self._timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def get_media_item(self, media_id, device_uid=None):
        """GET /rovers/{uid}/media/{id} - Get snapshot binary"""
        uid = device_uid or self._device_uid
        try:
            resp = requests.get(
                self._url(f"/rovers/{uid}/media/{media_id}"),
                timeout=self._timeout,
            )
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as e:
            return None

    def delete_media(self, media_id, device_uid=None):
        """DELETE /rovers/{uid}/media/{id} - Delete snapshot"""
        uid = device_uid or self._device_uid
        try:
            resp = requests.delete(
                self._url(f"/rovers/{uid}/media/{media_id}"),
                timeout=self._timeout,
            )
            resp.raise_for_status()
            return True
        except requests.RequestException as e:
            return False

    def upload_media(self, filepath, media_type="photo"):
        """POST /rovers/{uid}/media - Upload photo or video"""
        import os
        try:
            url = self._url(f"/rovers/{self._device_uid}/media")
            filename = os.path.basename(filepath)
            
            if media_type == "video":
                ext = os.path.splitext(filename)[1].lower()
                content_type = "video/mp4" if ext == ".mp4" else "video/avi"
            else:
                ext = os.path.splitext(filename)[1].lower()
                content_type = "image/png" if ext == ".png" else "image/jpeg"
            
            with open(filepath, 'rb') as f:
                files = {'file': (filename, f, content_type)}
                resp = requests.post(url, files=files, timeout=60)
            
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            return {"error": str(e)}
