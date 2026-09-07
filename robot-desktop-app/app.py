from datetime import datetime
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from config import load_config, save_config
from cloud_api import CloudAPI
from cloud_worker import CloudWorker
from rover_ws import RoverWebSocket
from mjpeg_receiver import MJPEGReceiver
from telemetry_poller import TelemetryPoller
from styles import DARK_STYLE
from views.header import create_header, _on_ip_changed
from views.main_view import create_main_view
from views.diagnostics_view import create_diagnostics_view
from views.sidebar import create_sidebar
from views.bottom_controls import create_bottom_controls
from views.log_panel import create_log_panel


class RoverTeleopApp(QWidget):
    log_message = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self._config = load_config()
        self._is_driving = False
        self._current_speed = self._config.get("motor_speed", 220)
        self._gimbal_pan = 90
        self._gimbal_tilt = 90
        self._view_mode = "main"
        self._commands_log = []

        self._video_thread = None
        self._telemetry_thread = None
        self._rover_ws = None
        self._mjpeg_receiver = None
        self._telemetry_poller = None
        self._cloud_workers = []

        self.init_ui()
        self.connect_signals()
        self.start_connections()

    def init_ui(self):
        self.setWindowTitle("Rover Teleop Cockpit v2.4.0")
        self.setMinimumSize(1400, 900)
        self.setStyleSheet(DARK_STYLE)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_layout.addWidget(create_header(self))

        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)

        self._center_stack = QStackedWidget()
        self._center_stack.addWidget(create_main_view(self))
        self._center_stack.addWidget(create_diagnostics_view(self))
        content.addWidget(self._center_stack, 1)

        self._sidebar = create_sidebar(self)
        content.addWidget(self._sidebar)

        main_layout.addLayout(content, 1)

        main_layout.addWidget(create_bottom_controls(self))
        main_layout.addWidget(create_log_panel(self))

        self.setFocus()

    def connect_signals(self):
        self.log_message.connect(self._add_log)

    def start_connections(self):
        self._stop_real_connections()

        ws_url = f"ws://{self._config['car_ip']}:81/"
        self._rover_ws = RoverWebSocket(ws_url)
        self._rover_ws.connected.connect(self._on_rover_connected)
        self._rover_ws.disconnected.connect(self._on_rover_disconnected)
        self._rover_ws.message_received.connect(self._on_rover_message)
        self._rover_ws.error.connect(self._on_rover_error)
        self._rover_ws.start()

        ws_url = f"ws://{self._config['cam_ip']}:81/"
        self._video_receiver = MJPEGReceiver(f"http://{self._config['cam_ip']}/640x480.mjpeg")
        self._video_receiver.connected.connect(self._on_camera_connected)
        self._video_receiver.disconnected.connect(self._on_camera_disconnected)
        self._video_receiver.error.connect(self._on_camera_error)
        self._video_receiver.start()

        self._telemetry_poller = TelemetryPoller(self._config['car_ip'])
        self._telemetry_poller.data_received.connect(self._on_telemetry_data)
        self._telemetry_poller.error.connect(self._on_telemetry_error)
        self._telemetry_poller.start()

        self._video_timer = QTimer()
        self._video_timer.timeout.connect(self._update_video_frame)
        self._video_timer.start(33)

        self._add_log("MODE", "Connecting to REAL ESP32 hardware...")

        self._cloud_api = CloudAPI()
        self._test_cloud_connection()

    def _stop_real_connections(self):
        if self._rover_ws:
            self._rover_ws.stop()
            self._rover_ws = None
        if hasattr(self, '_video_receiver') and self._video_receiver:
            self._video_receiver.stop()
            self._video_receiver = None
        if self._telemetry_poller:
            self._telemetry_poller.stop()
            self._telemetry_poller = None

    def _on_rover_connected(self):
        self._add_log("ROVER", f"WebSocket connected - ws://{self._config['car_ip']}:81/")
        self._rover_status.setText("Rover: Online")
        self._rover_status.setStyleSheet("color: #10b981; font-size: 11px; font-weight: 500;")

    def _on_rover_disconnected(self):
        self._add_log("ROVER", "WebSocket disconnected")
        self._rover_status.setText("Rover: Offline")
        self._rover_status.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: 500;")

    def _on_rover_message(self, data):
        msg_type = data.get("type", "")
        if msg_type == "status":
            self._add_log("ROVER", f"Status: {data.get('msg', '')}")
        elif msg_type == "imu":
            pass

    def _on_rover_error(self, error):
        self._add_log("ROVER", f"Error: {error}")

    def _on_camera_connected(self):
        self._add_log("CAMERA", f"MJPEG stream connected - http://{self._config['cam_ip']}/640x480.mjpeg")
        self._cam_status.setText("Cam: Online")
        self._cam_status.setStyleSheet("color: #10b981; font-size: 11px; font-weight: 500; margin-left: 8px;")

    def _on_camera_disconnected(self):
        self._add_log("CAMERA", "MJPEG stream disconnected")
        self._cam_status.setText("Cam: Offline")
        self._cam_status.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: 500; margin-left: 8px;")

    def _on_camera_error(self, error):
        self._add_log("CAMERA", f"Error: {error}")

    def _update_video_frame(self):
        if hasattr(self, '_video_receiver') and self._video_receiver:
            frame = self._video_receiver.take_frame()
            if frame:
                self._video_canvas.update_frame_jpeg(frame)

    def _on_video_stats(self, stats):
        pass

    def _on_telemetry_data(self, data):
        self._update_telemetry(data)
        self._send_to_cloud(data)

    def _on_telemetry_error(self, error):
        self._add_log("TELEMETRY", f"Error: {error[:60]}")

    def _update_telemetry(self, data):
        temp = data.get("temperature", 0)
        humidity = data.get("humidity", 0)
        gas = data.get("gas", 0)
        distance = data.get("distance", 0)

        self._temp_card.update_value(f"{temp}°C", temp / 60 * 100)
        self._humidity_card.update_value(f"{humidity}%", humidity)
        self._gas_card.update_value(f"{int(gas)} PPM", gas / 1000 * 100)
        self._distance_card.update_value(f"{distance} cm", distance / 200 * 100)

    def _send_to_cloud(self, data):
        if not self._cloud_api:
            return
        
        url = f"{self._cloud_api._base_url}/telemetry"
        payload = {
            "device_uid": self._cloud_api._device_uid,
            "recorded_at": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "temperature_c": data.get("temperature", 0),
            "humidity_pct": data.get("humidity", 0),
            "gas_ppm": data.get("gas", 0),
            "distance_cm": data.get("distance", 0),
            "auto_brake": data.get("obstacle", False),
        }
        worker = CloudWorker("POST", url, payload=payload)
        self._cloud_workers.append(worker)
        worker.finished.connect(lambda: self._cloud_workers.remove(worker) if worker in self._cloud_workers else None)
        worker.start()

    def _manual_send_to_cloud(self):
        if not self._cloud_api:
            self._add_log("CLOUD", "Cloud API not initialized")
            return

        url = f"{self._cloud_api._base_url}/telemetry"
        payload = {
            "device_uid": self._cloud_api._device_uid,
            "recorded_at": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "temperature_c": 25.0,
            "humidity_pct": 60.0,
            "gas_ppm": 100.0,
            "distance_cm": 50.0,
            "auto_brake": False,
        }
        worker = CloudWorker("POST", url, payload=payload)
        worker.result.connect(self._on_cloud_post_success)
        worker.error.connect(self._on_cloud_post_error)
        self._cloud_workers.append(worker)
        worker.finished.connect(lambda: self._cloud_workers.remove(worker) if worker in self._cloud_workers else None)
        worker.start()

    def _on_cloud_post_success(self, data):
        if data.get("success"):
            self._add_log("CLOUD", "POST sent to cloud OK")
        else:
            self._add_log("CLOUD", f"POST response: {data}")

    def _on_cloud_post_error(self, error):
        self._add_log("CLOUD", f"POST failed: {error}")

    def _test_cloud_connection(self):
        url = f"{self._cloud_api._base_url}/rovers"
        self._cloud_worker = CloudWorker("GET", url)
        self._cloud_worker.result.connect(self._on_cloud_test_success)
        self._cloud_worker.error.connect(self._on_cloud_test_error)
        self._cloud_workers.append(self._cloud_worker)
        self._cloud_worker.finished.connect(lambda: self._cloud_workers.remove(self._cloud_worker) if self._cloud_worker in self._cloud_workers else None)
        self._cloud_worker.start()

    def _on_cloud_test_success(self, data):
        self._add_log("CLOUD", f"Connected to cloud API OK - {self._cloud_api._base_url}")

    def _on_cloud_test_error(self, error):
        if "timed out" in error or "ConnectTimeout" in error:
            self._add_log("CLOUD", f"Server offline (timeout) - {self._cloud_api._base_url}")
        elif "NameResolutionError" in error or "resolve" in error:
            self._add_log("CLOUD", f"Cannot resolve hostname - {self._cloud_api._base_url}")
        else:
            self._add_log("CLOUD", f"Connection failed: {error}")

    def _center_gimbal(self):
        self._gimbal_pan = 90
        self._gimbal_tilt = 90
        self._gimbal_pan_label.setText(f"90°")
        self._gimbal_tilt_label.setText(f"90°")
        self._send_command("servo:90,90")

    def _take_snapshot(self):
        self._add_log("SNAPSHOT", "Frame captured (stub)")

    def _toggle_view(self):
        if self._view_mode == "main":
            self._center_stack.setCurrentIndex(1)
            self._view_mode = "diagnostics"
        else:
            self._center_stack.setCurrentIndex(0)
            self._view_mode = "main"

    def _toggle_follow_mode(self):
        self._add_log("FOLLOW", "Follow mode toggled (stub)")

    def _emergency_stop(self):
        self._send_command("stop")
        self._add_log("STOP", "Emergency stop activated")

    def _send_chat(self):
        text = self._chat_input.text().strip()
        if not text:
            return
        self._chat_display.append(f"You: {text}")
        self._chat_input.clear()

        self._chat_display.append(f"AI: [Stub] Received: {text}")

    def _send_command(self, command):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._commands_log.append((timestamp, command))
        self._add_log("CMD", command)

        if self._rover_ws and self._rover_ws.is_connected:
            self._rover_ws.send(command)

    def _add_log(self, category, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {
            "CONNECTED": "#10b981",
            "CMD": "#f1f5f9",
            "SAFETY": "#f59e0b",
            "STOP": "#ef4444",
            "SNAPSHOT": "#06b6d4",
            "FOLLOW": "#8b5cf6",
            "ERROR": "#ef4444",
        }
        color = colors.get(category, "#94a3b8")
        html = f'<span style="color: #64748b;">[{timestamp}]</span> <span style="color: {color};">[{category}]</span> <span style="color: #94a3b8;">{message}</span>'
        self._log_display.append(html)

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return

        key = event.key()
        if key in (Qt.Key.Key_W, Qt.Key.Key_S, Qt.Key.Key_A, Qt.Key.Key_D):
            if self._telemetry_poller:
                self._telemetry_poller.set_driving(True)

        if key == Qt.Key.Key_W:
            self._send_command("forward")
        elif key == Qt.Key.Key_S:
            self._send_command("backward")
        elif key == Qt.Key.Key_A:
            self._send_command("left")
        elif key == Qt.Key.Key_D:
            self._send_command("right")
        elif key == Qt.Key.Key_Space:
            self._emergency_stop()
        elif key == Qt.Key.Key_I:
            self._gimbal_tilt = min(180, self._gimbal_tilt + 5)
            self._update_gimbal()
        elif key == Qt.Key.Key_K:
            self._gimbal_tilt = max(0, self._gimbal_tilt - 5)
            self._update_gimbal()
        elif key == Qt.Key.Key_J:
            self._gimbal_pan = max(0, self._gimbal_pan - 5)
            self._update_gimbal()
        elif key == Qt.Key.Key_L:
            self._gimbal_pan = min(180, self._gimbal_pan + 5)
            self._update_gimbal()
        elif key == Qt.Key.Key_C:
            self._center_gimbal()
        elif key == Qt.Key.Key_1:
            self._resolution_combo.setCurrentIndex(0)
        elif key == Qt.Key.Key_2:
            self._resolution_combo.setCurrentIndex(1)
        elif key == Qt.Key.Key_3:
            self._resolution_combo.setCurrentIndex(2)
        elif key == Qt.Key.Key_4:
            self._resolution_combo.setCurrentIndex(3)
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return
        key = event.key()
        if key in (Qt.Key.Key_W, Qt.Key.Key_S, Qt.Key.Key_A, Qt.Key.Key_D):
            self._send_command("stop")
            if self._telemetry_poller:
                self._telemetry_poller.set_driving(False)
        else:
            super().keyReleaseEvent(event)

    def _update_gimbal(self):
        self._gimbal_pan_label.setText(f"{self._gimbal_pan}°")
        self._gimbal_tilt_label.setText(f"{self._gimbal_tilt}°")
        self._send_command(f"servo:{self._gimbal_pan},{self._gimbal_tilt}")

    def closeEvent(self, event):
        if hasattr(self, '_video_timer'):
            self._video_timer.stop()
        
        self._stop_real_connections()
        
        for worker in self._cloud_workers:
            if worker.isRunning():
                worker.quit()
                worker.wait(1000)
        self._cloud_workers.clear()
        
        save_config(self._config)
        event.accept()