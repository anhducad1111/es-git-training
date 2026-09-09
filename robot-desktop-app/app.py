import os
import tempfile
from datetime import datetime
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QImage
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
from video_worker import VideoWorker
from telemetry_poller import TelemetryPoller
from esp32_api import ESP32API
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
        self._driving_forward = True
        self._global_speed = self._config.get("motor_speed", 220)
        self._forward_speed = self._global_speed
        self._current_speed = self._config.get("motor_speed", 220)
        self._gimbal_pan = 90
        self._gimbal_tilt = 90
        self._view_mode = "main"
        self._commands_log = []
        self._speed_delta = 0

        self._video_thread = None
        self._telemetry_thread = None
        self._rover_ws = None
        self._mjpeg_receiver = None
        self._telemetry_poller = None
        self._cloud_workers = []

        self._speed_timer = QTimer()
        self._speed_timer.timeout.connect(self._tick_speed)
        self._speed_timer.setInterval(50)

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
        if hasattr(self, '_video_canvas'):
            self._video_canvas.gimbal_changed.connect(self._on_mouse_gimbal)

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

        self._esp32_api = ESP32API(self._config['car_ip'], self._config['cam_ip'])

        self._video_timer = QTimer()
        self._video_timer.timeout.connect(self._update_video_frame)
        self._video_timer.start(33)

        self._video_worker = VideoWorker()
        self._video_worker.frame_ready.connect(self._on_video_frame_ready)
        self._video_worker.start()

        self._latest_telemetry = {}
        self._cloud_timer = QTimer()
        self._cloud_timer.timeout.connect(self._send_cloud_update)
        self._cloud_timer.start(10000)

        self._hog_detector = None
        self._yolo_detector = None
        self._hog_detections = []
        self._detection_method = "HOG"

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
        if hasattr(self, '_video_worker') and self._video_worker:
            self._video_worker.stop()
            self._video_worker = None
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
                if isinstance(frame, QImage):
                    self._video_canvas.update_frame_jpeg(frame)
                elif isinstance(frame, bytes):
                    self._video_worker.push_frame(frame)

    def _on_video_frame_ready(self, pixmap, bgr):
        self._video_canvas.update_frame_jpeg(pixmap)
        if (self._hog_detector and self._hog_detector.isRunning()) or \
           (self._yolo_detector and self._yolo_detector.isRunning()):
            if bgr is not None:
                if self._hog_detector and self._hog_detector.isRunning():
                    self._hog_detector.set_frame(bgr)
                if self._yolo_detector and self._yolo_detector.isRunning():
                    self._yolo_detector.set_frame(bgr)

    def _toggle_hog_detection(self):
        if self._detection_method == "HOG":
            if self._hog_detector and self._hog_detector.isRunning():
                self._hog_detector.stop_detection()
                self._hog_detections = []
                self._add_log("HOG", "Human detection stopped")
            else:
                from hog_detector import HOGDetector
                self._hog_detector = HOGDetector()
                self._hog_detector.detected.connect(self._on_hog_detected)
                self._hog_detector.error.connect(lambda e: self._add_log("HOG", f"Error: {e}"))
                self._hog_detector.start_detection()
                self._add_log("HOG", "Human detection started")
        elif self._detection_method == "YOLO":
            if self._yolo_detector and self._yolo_detector.isRunning():
                self._yolo_detector.stop_detection()
                self._hog_detections = []
                self._add_log("YOLO", "Object detection stopped")
            else:
                from yolo_detector import YOLODetector
                self._yolo_detector = YOLODetector()
                self._yolo_detector.detected.connect(self._on_hog_detected)
                self._yolo_detector.error.connect(lambda e: self._add_log("YOLO", f"Error: {e}"))
                self._yolo_detector.status.connect(lambda e: self._add_log("YOLO", e))
                self._yolo_detector.start_detection()
                self._add_log("YOLO", "Object detection started")

    def _on_hog_detected(self, detections):
        self._hog_detections = detections
        if detections:
            self._add_log("HOG", f"Detected {len(detections)} person(s)")

    def _on_video_stats(self, stats):
        pass

    def _on_telemetry_data(self, data):
        self._update_telemetry(data)
        self._latest_telemetry = data

    def _on_telemetry_error(self, error):
        self._add_log("TELEMETRY", f"Error: {error[:60]}")

    def _update_telemetry(self, data):
        temp = data.get("temperature", 0)
        humidity = data.get("humidity", 0)
        gas = data.get("gas", 0)
        distance = data.get("distance", 0)

        self._temp_label.setText(f"{temp}°C")
        self._humidity_label.setText(f"{humidity}%")
        self._gas_label.setText(f"{int(gas)} PPM")
        self._distance_card.update_value(f"{distance} cm", distance / 200 * 100)

        if hasattr(self, '_brake_toggle') and self._brake_toggle.isChecked():
            if self._driving_forward and distance < 89:
                if distance <= 15:
                    self._forward_speed = 0
                else:
                    ratio = (distance - 15) / 74.0
                    self._forward_speed = int(self._global_speed * ratio)
                self._forward_speed = max(0, min(255, self._forward_speed))
                self._send_command(f"speed:{self._forward_speed}")
                if hasattr(self, '_speed_meter'):
                    self._speed_meter.set_speed(self._forward_speed)
                if self._forward_speed == 0:
                    self._send_command("stop")
            else:
                self._send_command(f"speed:{self._global_speed}")
                if hasattr(self, '_speed_meter'):
                    self._speed_meter.set_speed(self._global_speed)

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
        self._add_log("CLOUD", f"Sent: T={data.get('temperature',0)}°C H={data.get('humidity',0)}%")

    def _send_cloud_update(self):
        if self._latest_telemetry:
            self._send_to_cloud(self._latest_telemetry)

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
        if hasattr(self, '_gimbal_hud'):
            self._gimbal_hud.set_gimbal(90, 90)

    def _take_snapshot(self):
        if not hasattr(self, '_video_canvas'):
            self._add_log("SNAPSHOT", "No video canvas available")
            return
        
        pixmap = self._video_canvas.pixmap()
        if pixmap is None or pixmap.isNull():
            self._add_log("SNAPSHOT", "No frame to capture")
            return
        
        from PyQt6.QtGui import QPainter, QFont, QColor, QPen
        
        temp = self._latest_telemetry.get("temperature", 0)
        humidity = self._latest_telemetry.get("humidity", 0)
        gas = self._latest_telemetry.get("gas", 0)
        distance = self._latest_telemetry.get("distance", 0)
        
        overlay = pixmap.copy()
        painter = QPainter(overlay)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        from datetime import timezone, timedelta
        vn_tz = timezone(timedelta(hours=7))
        vn_time = datetime.now(vn_tz).strftime("%H:%M:%S")
        
        panel_x = overlay.width() - 120
        panel_y = 15
        line_h = 18
        
        painter.setPen(QPen(QColor(16, 185, 129), 1))
        painter.setFont(QFont("JetBrains Mono", 9, QFont.Weight.Bold))
        painter.drawText(panel_x, panel_y, f"T: {temp}°C")
        painter.drawText(panel_x, panel_y + line_h, f"H: {humidity}%")
        painter.drawText(panel_x, panel_y + line_h * 2, f"G: {int(gas)} PPM")
        painter.drawText(panel_x, panel_y + line_h * 3, vn_time)
        
        painter.end()
        
        snapshot_dir = os.path.join(os.path.dirname(__file__), "snapshot")
        os.makedirs(snapshot_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"snapshot_{timestamp}.png"
        filepath = os.path.join(snapshot_dir, filename)
        
        overlay.save(filepath, "PNG")
        self._add_log("SNAPSHOT", f"Saved: {filename}")
        
        self._upload_snapshot_to_server(filepath)
        
        if hasattr(self, '_super_res_check') and self._super_res_check.isChecked():
            self._apply_super_resolution(filepath)

    def _upload_snapshot_to_server(self, filepath):
        if not self._cloud_api:
            self._add_log("SNAPSHOT", "Cloud API not available")
            return
        
        try:
            import requests
            url = self._cloud_api._url(f"/rovers/{self._cloud_api._device_uid}/media")
            self._add_log("SNAPSHOT", f"Upload URL: {url}")
            
            with open(filepath, 'rb') as f:
                files = {'file': (os.path.basename(filepath), f, 'image/png')}
                response = requests.post(url, files=files, timeout=10)
            
            self._add_log("SNAPSHOT", f"Response: {response.status_code} {response.text[:100]}")
            if response.status_code == 201:
                self._add_log("SNAPSHOT", f"Uploaded to server: {os.path.basename(filepath)}")
            else:
                self._add_log("SNAPSHOT", f"Upload failed: {response.status_code}")
        except Exception as e:
            self._add_log("SNAPSHOT", f"Upload error: {str(e)[:80]}")

    def _apply_super_resolution(self, image_path):
        self._add_log("SUPER RES", "Processing snapshot...")
        
        try:
            from super_resolution import SuperResolutionWorker
            
            directory = os.path.dirname(image_path)
            filename = os.path.basename(image_path)
            
            use_hf = bool(self._config.get("hf_token", ""))
            prefix = "hg_" if use_hf else "high_"
            output_path = os.path.join(directory, f"{prefix}{filename}")
            
            self._sr_worker = SuperResolutionWorker(image_path, output_path, use_hf=use_hf)
            self._sr_worker.finished.connect(
                lambda path: self._add_log("SUPER RES", f"Saved: {os.path.basename(path)}")
            )
            self._sr_worker.error.connect(
                lambda err: self._add_log("SUPER RES", f"Error: {err[:50]}")
            )
            self._sr_worker.status.connect(
                lambda msg: self._add_log("SUPER RES", msg)
            )
            self._sr_worker.start()
        except Exception as e:
            self._add_log("SUPER RES", f"Error: {str(e)[:50]}")

    def _toggle_view(self):
        if self._view_mode == "main":
            self._center_stack.setCurrentIndex(1)
            self._view_mode = "diagnostics"
            if hasattr(self, '_cloud_api') and self._cloud_api:
                self._load_history()
        else:
            self._center_stack.setCurrentIndex(0)
            self._view_mode = "main"

    def _load_history(self):
        from views.diagnostics_view import _load_history as _do_load
        _do_load(self)

    def _toggle_follow_mode(self):
        self._add_log("FOLLOW", "Follow mode toggled (stub)")

    def _emergency_stop(self):
        self._send_command("stop")
        self._add_log("STOP", "Emergency stop activated")

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
            self._driving_forward = True
            self._send_command("forward")
        elif key == Qt.Key.Key_S:
            self._driving_forward = False
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
        elif key == Qt.Key.Key_X:
            self._take_snapshot()
        elif key == Qt.Key.Key_1:
            self._resolution_combo.setCurrentIndex(0)
        elif key == Qt.Key.Key_2:
            self._resolution_combo.setCurrentIndex(1)
        elif key == Qt.Key.Key_3:
            self._resolution_combo.setCurrentIndex(2)
        elif key == Qt.Key.Key_4:
            self._resolution_combo.setCurrentIndex(3)
        elif key == Qt.Key.Key_Shift:
            self._speed_delta = 1
            if not self._speed_timer.isActive():
                self._speed_timer.start()
        elif key == Qt.Key.Key_Control:
            self._speed_delta = -1
            if not self._speed_timer.isActive():
                self._speed_timer.start()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return
        key = event.key()
        if key in (Qt.Key.Key_W, Qt.Key.Key_S, Qt.Key.Key_A, Qt.Key.Key_D):
            self._send_command("stop")
            if hasattr(self, '_speed_meter'):
                self._speed_meter.set_speed(0)
            if self._telemetry_poller:
                self._telemetry_poller.set_driving(False)
        elif key in (Qt.Key.Key_Shift, Qt.Key.Key_Control):
            self._speed_delta = 0
            self._speed_timer.stop()
        else:
            super().keyReleaseEvent(event)

    def _change_speed(self, delta):
        new_speed = max(180, min(255, self._global_speed + delta))
        if new_speed != self._global_speed:
            self._global_speed = new_speed
            self._speed_slider.setValue(self._global_speed)
            self._speed_label.setText(f"{self._global_speed}")
            self._send_command(f"speed:{self._global_speed}")

    def _tick_speed(self):
        if self._speed_delta != 0:
            self._change_speed(self._speed_delta)

    def _update_gimbal(self):
        self._gimbal_pan_label.setText(f"{self._gimbal_pan}°")
        self._gimbal_tilt_label.setText(f"{self._gimbal_tilt}°")
        self._send_command(f"servo:{self._gimbal_pan},{self._gimbal_tilt}")
        if hasattr(self, '_gimbal_hud'):
            self._gimbal_hud.set_gimbal(self._gimbal_pan, self._gimbal_tilt)

    def _on_mouse_gimbal(self, pan, tilt):
        self._gimbal_pan = int(pan)
        self._gimbal_tilt = int(tilt)
        self._gimbal_pan_label.setText(f"{self._gimbal_pan}°")
        self._gimbal_tilt_label.setText(f"{self._gimbal_tilt}°")
        self._send_command(f"servo:{self._gimbal_pan},{self._gimbal_tilt}")
        if hasattr(self, '_gimbal_hud'):
            self._gimbal_hud.set_gimbal(self._gimbal_pan, self._gimbal_tilt)

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