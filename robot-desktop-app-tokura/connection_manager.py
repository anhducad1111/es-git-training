from PyQt6.QtCore import QTimer, pyqtSignal, QObject
from rover_ws import RoverWebSocket
from mjpeg_receiver import MJPEGReceiver
from telemetry_poller import TelemetryPoller
from esp32_api import ESP32API


class ConnectionManager(QObject):
    """Manages WebSocket, MJPEG, and telemetry connections."""
    
    rover_connected = pyqtSignal()
    rover_disconnected = pyqtSignal()
    camera_connected = pyqtSignal()
    camera_disconnected = pyqtSignal()
    video_stats = pyqtSignal(dict)
    
    def __init__(self, config, log_callback):
        super().__init__()
        self._config = config
        self._log = log_callback
        
        self._rover_ws = None
        self._video_receiver = None
        self._telemetry_poller = None
        self._esp32_api = None
        self._cam_resolution = "640x480"
        
    def start_all(self):
        """Start all connections."""
        self._start_rover_ws()
        self._start_camera()
        self._start_telemetry()
        self._esp32_api = ESP32API(self._config['car_ip'], self._config['cam_ip'])
        
    def stop_all(self):
        """Stop all connections."""
        if self._rover_ws:
            self._rover_ws.stop()
            self._rover_ws = None
        if self._video_receiver:
            self._video_receiver.stop()
            self._video_receiver = None
        if self._telemetry_poller:
            self._telemetry_poller.stop()
            self._telemetry_poller = None
            
    def _start_rover_ws(self):
        """Start WebSocket connection to rover."""
        ws_url = f"ws://{self._config['car_ip']}:81/"
        self._rover_ws = RoverWebSocket(ws_url)
        self._rover_ws.connected.connect(lambda: self._log("ROVER", f"WebSocket connected - {ws_url}"))
        self._rover_ws.connected.connect(self.rover_connected.emit)
        self._rover_ws.disconnected.connect(lambda: self._log("ROVER", "WebSocket disconnected"))
        self._rover_ws.disconnected.connect(self.rover_disconnected.emit)
        self._rover_ws.error.connect(lambda e: self._log("ROVER", f"Error: {e}"))
        self._rover_ws.start()

    def reconnect_rover(self):
        """Tear down and re-establish the rover WebSocket + telemetry poller
        using the current IP in self._config (e.g. after the user edits it)."""
        if self._rover_ws:
            self._rover_ws.stop()
            self._rover_ws = None
        if self._telemetry_poller:
            self._telemetry_poller.stop()
            self._telemetry_poller = None
        self._start_rover_ws()
        self._start_telemetry()
        self._log("ROVER", f"Reconnecting to {self._config['car_ip']}...")

    def _start_camera(self, resolution=None):
        """Start MJPEG camera connection."""
        if resolution:
            self._cam_resolution = resolution
        cam_url = f"http://{self._config['cam_ip']}/{self._cam_resolution}.mjpeg"
        quality = self._config.get('cam_quality', 14)
        self._video_receiver = MJPEGReceiver(cam_url, quality=quality)
        self._video_receiver.connected.connect(lambda: self._log("CAMERA", f"Stream connected - {cam_url}"))
        self._video_receiver.connected.connect(self.camera_connected.emit)
        self._video_receiver.disconnected.connect(lambda: self._log("CAMERA", "Stream disconnected"))
        self._video_receiver.disconnected.connect(self.camera_disconnected.emit)
        self._video_receiver.error.connect(lambda e: self._log("CAMERA", f"Error: {e}"))
        self._video_receiver.stats_updated.connect(lambda s: self.video_stats.emit(s))
        # Temporary diagnostic: shows whether a low FPS is a network/device
        # bandwidth problem (few bytes/s) or a parser problem (many bytes/s
        # but few frames/s extracted from them).
        self._video_receiver.parser_stats.connect(
            lambda b, f: self._log("CAMERA", f"recv {b/1024:.1f} KB/s, {f} frames/s parsed")
        )
        self._video_receiver.start()

    def reconnect_camera(self, resolution=None):
        """Tear down and re-establish the camera stream using the current
        cam_ip in self._config (e.g. after the user edits it or changes
        resolution)."""
        if self._video_receiver:
            self._video_receiver.stop()
            self._video_receiver = None
        self._start_camera(resolution)
        self._log("CAMERA", f"Reconnecting to {self._config['cam_ip']}...")

    def update_esp32_ips(self):
        """Refresh the shared ESP32API instance's IPs after they change."""
        if self._esp32_api:
            self._esp32_api.car_ip = self._config['car_ip']
            self._esp32_api.cam_ip = self._config['cam_ip']

    def _start_telemetry(self):
        """Start telemetry polling."""
        self._telemetry_poller = TelemetryPoller(self._config['car_ip'])
        self._telemetry_poller.error.connect(lambda e: self._log("TELEMETRY", f"Error: {e[:60]}"))
        self._telemetry_poller.start()
        
    def send_command(self, command):
        """Send command to rover via WebSocket."""
        if self._rover_ws and self._rover_ws.is_connected:
            self._rover_ws.send(command)
            
    def take_frame(self):
        """Take latest frame from camera."""
        if self._video_receiver:
            return self._video_receiver.take_frame()
        return None
        
    def stop_camera(self):
        """Stop camera connection."""
        if self._video_receiver:
            self._video_receiver.stop()
            self._video_receiver = None
            self._log("CAMERA", "Camera disconnected for remote control")
            
    def start_camera(self):
        """Start camera connection."""
        if self._video_receiver is None:
            self._start_camera()
        
    @property
    def rover_ws(self):
        return self._rover_ws
        
    @property
    def esp32_api(self):
        return self._esp32_api
        
    @property
    def telemetry_poller(self):
        return self._telemetry_poller
