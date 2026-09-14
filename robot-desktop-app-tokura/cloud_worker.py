import os
import requests
from PyQt6.QtCore import QThread, pyqtSignal


class _UploadFileWrapper:
    def __init__(self, file_path, on_progress):
        self._fp = open(file_path, "rb")
        self._total = os.path.getsize(file_path)
        self._sent = 0
        self._on_progress = on_progress

    def read(self, size=-1):
        chunk = self._fp.read(size)
        if chunk:
            self._sent += len(chunk)
            pct = int(self._sent * 100 / self._total) if self._total else 100
            self._on_progress(pct)
        return chunk

    def close(self):
        self._fp.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __iter__(self):
        return iter(self._fp)

    def fileno(self):
        return self._fp.fileno()


class CloudWorker(QThread):
    result = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, method, url, payload=None, file_path=None, headers=None, timeout=60, data=None):
        super().__init__()
        self.method = method
        self.url = url
        self.payload = payload
        self.file_path = file_path
        self.headers = headers or {}
        self.timeout = timeout
        self.data = data or {}

    def run(self):
        try:
            if self.method == "GET":
                resp = requests.get(self.url, headers=self.headers, timeout=self.timeout)
            elif self.method == "POST":
                resp = requests.post(self.url, json=self.payload, headers=self.headers, timeout=self.timeout)
            elif self.method == "DELETE":
                resp = requests.delete(self.url, headers=self.headers, timeout=self.timeout)
            elif self.method == "UPLOAD":
                fname = self.file_path.split("/")[-1].split("\\")[-1]
                with _UploadFileWrapper(self.file_path, self.progress.emit) as wf:
                    files = {"file": (fname, wf)}
                    resp = requests.post(
                        self.url, files=files, data=self.data,
                        headers=self.headers, timeout=self.timeout
                    )
                self.progress.emit(100)
            else:
                self.error.emit("Invalid method")
                return

            resp.raise_for_status()
            if resp.status_code == 204:
                self.result.emit({"success": True})
            else:
                self.result.emit(resp.json())
        except requests.RequestException as e:
            self.error.emit(str(e))
