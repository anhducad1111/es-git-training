import requests
from PyQt6.QtCore import QThread, pyqtSignal


class MJPEGReceiver(QThread):
    frame_received = pyqtSignal(bytes)
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, stream_url):
        super().__init__()
        self.stream_url = stream_url
        self._running = False
        self._connected = False

    def run(self):
        self._running = True
        try:
            response = requests.get(self.stream_url, stream=True, timeout=10)
            if response.status_code == 200:
                self._connected = True
                self.connected.emit()
                self._process_stream(response)
            else:
                self.error.emit(f"HTTP {response.status_code}")
        except requests.exceptions.Timeout:
            self.error.emit("Connection timeout")
        except requests.exceptions.ConnectionError:
            self.error.emit("Connection failed")
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self._connected = False
            self.disconnected.emit()

    def _process_stream(self, response):
        buffer = b""
        
        for chunk in response.iter_content(chunk_size=4096):
            if not self._running:
                break
            
            buffer += chunk
            
            while True:
                start = buffer.find(b"\xff\xd8")
                if start == -1:
                    buffer = buffer[-1:]
                    break
                
                end = buffer.find(b"\xff\xd9", start + 2)
                if end == -1:
                    break
                
                end += 2
                jpeg_data = buffer[start:end]
                buffer = buffer[end:]
                
                if jpeg_data:
                    self.frame_received.emit(jpeg_data)

    def stop(self):
        self._running = False
        self.wait()
