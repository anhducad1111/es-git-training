import os
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
from styles import DARK_STYLE
from views.header import create_header
from views.main_view import create_main_view
from views.diagnostics_view import create_diagnostics_view
from views.snapshots_view import create_snapshots_view
from views.sidebar import create_sidebar
from views.bottom_controls import create_bottom_controls
from views.log_panel import create_log_panel
from connection_manager import ConnectionManager
from video_manager import VideoManager
from detection_manager import DetectionManager
from input_handler import InputHandler
from cloud_manager import CloudManager
from remote_control_server import RemoteControlServer


class RoverTeleopApp(QWidget):
    log_message = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self._config = load_config()
        self._view_mode = "main"
        self._current_speed = self._config.get("motor_speed", 220)
        self._global_speed = self._current_speed
        self._gimbal_pan = 90
        self._gimbal_tilt = 90
        
        # Initialize managers
        self._conn_mgr = ConnectionManager(self._config, self._add_log)
        self._video_mgr = VideoManager(None, self._add_log)
        self._detection_mgr = DetectionManager(self._add_log, app=self)
        self._input_handler = InputHandler(self._send_command, self._add_log, on_emergency_stop=self._emergency_stop, on_chassis_follow_toggle=self._toggle_chassis_follow, on_gimbal_update=self._on_gimbal_update)
        self._cloud_mgr = CloudManager(self._config, self._add_log)
        self._allow_remote_control = False
        self._remote_server = None
        
        self._speed_timer = QTimer()
        self._speed_timer.timeout.connect(self._input_handler._tick_speed)
        self._speed_timer.setInterval(50)
        
        self.init_ui()
        self.connect_signals()
        self.start_connections()

    def init_ui(self):
        self.setWindowTitle("Rover Teleop Cockpit v2.5.0")
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
        self._center_stack.addWidget(create_snapshots_view(self))
        content.addWidget(self._center_stack, 1)

        self._sidebar = create_sidebar(self)
        content.addWidget(self._sidebar)

        main_layout.addLayout(content, 1)

        main_layout.addWidget(create_bottom_controls(self))
        main_layout.addWidget(create_log_panel(self))

        self.setFocus()

    def connect_signals(self):
        self.log_message.connect(self._add_log)
        self._detection_mgr.detections_updated.connect(self._on_detections_updated)
        self._detection_mgr.follow_detected.connect(self._on_follow_detected)
        if hasattr(self, '_video_canvas'):
            self._video_canvas.gimbal_changed.connect(self._on_mouse_gimbal)

    def start_connections(self):
        self._conn_mgr.start_all()
        self._cloud_mgr.initialize()
        self._video_mgr._cloud_api = self._cloud_mgr.cloud_api
        
        port = self._config.get("remote_control_port", 8765)
        self._remote_server = RemoteControlServer("0.0.0.0", port)
        self._remote_server.command_received.connect(self._relay_command)
        self._remote_server.set_rover_connected(
            self._conn_mgr.rover_ws is not None
            and self._conn_mgr.rover_ws.is_connected
        )
        self._conn_mgr.rover_connected.connect(
            lambda: self._remote_server.set_rover_connected(True)
        )
        self._conn_mgr.rover_disconnected.connect(
            lambda: self._remote_server.set_rover_connected(False)
        )
        self._remote_server.start()
        self._add_log("REMOTE", f"Remote control server listening on port {port}")
        
        self._video_timer = QTimer()
        self._video_timer.timeout.connect(self._update_video_frame)
        self._video_timer.start(33)
        
        self._cloud_timer = QTimer()
        self._cloud_timer.timeout.connect(self._send_cloud_update)
        self._cloud_timer.start(10000)
        
        self._add_log("MODE", "Connecting to REAL ESP32 hardware...")

    def _update_video_frame(self):
        frame = self._conn_mgr.take_frame()
        if frame:
            if self._video_mgr.is_recording and isinstance(frame, QImage):
                self._video_mgr.save_frame(frame)
            if isinstance(frame, QImage):
                self._video_canvas.update_frame_jpeg(frame)
                if self._detection_mgr._follow_mode_active:
                    import cv2
                    import numpy as np
                    ptr = frame.bits()
                    ptr.setsize(frame.sizeInBytes())
                    arr = np.array(ptr).reshape(frame.height(), frame.width(), 4)
                    bgr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
                    self._detection_mgr.set_frame(bgr)
            elif isinstance(frame, bytes):
                from video_worker import VideoWorker
                if not hasattr(self, '_video_worker'):
                    self._video_worker = VideoWorker()
                    self._video_worker.frame_ready.connect(self._on_video_frame_ready)
                    self._video_worker.start()
                self._video_worker.push_frame(frame)

    def _on_video_frame_ready(self, pixmap, bgr):
        self._video_canvas.update_frame_jpeg(pixmap)
        if bgr is not None:
            self._detection_mgr.set_frame(bgr)

    def _on_detections_updated(self, detections):
        pass

    def _on_follow_detected(self, detection):
        self._video_canvas.set_follow_detections(
            [detection] if detection.get("bbox") else []
        )

    def _send_cloud_update(self):
        pass

    def _toggle_view(self):
        if self._view_mode == "diagnostics":
            self._center_stack.setCurrentIndex(0)
            self._view_mode = "main"
            if hasattr(self, '_diag_btn'):
                self._diag_btn.setChecked(False)
        else:
            self._center_stack.setCurrentIndex(1)
            self._view_mode = "diagnostics"
            if hasattr(self, '_diag_btn'):
                self._diag_btn.setChecked(True)
            if hasattr(self, '_snapshot_btn'):
                self._snapshot_btn.setChecked(False)

    def _toggle_snapshots_view(self):
        if self._view_mode == "snapshots":
            self._center_stack.setCurrentIndex(0)
            self._view_mode = "main"
            if hasattr(self, '_snapshot_btn'):
                self._snapshot_btn.setChecked(False)
        else:
            self._center_stack.setCurrentIndex(2)
            self._view_mode = "snapshots"
            if hasattr(self, '_snapshot_btn'):
                self._snapshot_btn.setChecked(True)
            if hasattr(self, '_diag_btn'):
                self._diag_btn.setChecked(False)
            from views.snapshots_view import _load_snapshots
            _load_snapshots(self)

    def _toggle_follow_mode(self):
        self._detection_mgr.toggle_follow_mode()

    def _toggle_hog_detection(self):
        self._detection_mgr.toggle_detection()

    def _center_gimbal(self):
        self._input_handler.center_gimbal()
        self._add_log("GIMBAL", "Centered")

    def _manual_send_to_cloud(self):
        self._add_log("CLOUD", "Manual send triggered")

    @property
    def _cloud_api(self):
        return self._cloud_mgr.cloud_api

    @property
    def _cloud_workers(self):
        return self._cloud_mgr._cloud_workers

    def _start_recording(self):
        self._video_mgr.start_recording()

    def _stop_recording(self):
        self._video_mgr.stop_recording()

    def _on_camera_connected(self):
        """Handle camera stream connected."""
        self._add_log("CAMERA", "Stream connected")
        if hasattr(self, '_cam_status'):
            self._cam_status.setText("ONLINE")
            self._cam_status.setStyleSheet("""
                color: #10b981;
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 1px;
                margin-left: 12px;
            """)
        if self._detection_mgr and self._detection_mgr._follow_controller:
            gimbal_thread = self._detection_mgr._follow_controller._gimbal_thread
            if gimbal_thread:
                gimbal_thread.on_camera_connected()

    def _on_camera_disconnected(self):
        """Handle camera stream disconnected."""
        self._add_log("CAMERA", "Stream disconnected")
        if hasattr(self, '_cam_status'):
            self._cam_status.setText("OFFLINE")
            self._cam_status.setStyleSheet("""
                color: #ef4444;
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 1px;
                margin-left: 12px;
            """)
        if self._detection_mgr and self._detection_mgr._follow_controller:
            gimbal_thread = self._detection_mgr._follow_controller._gimbal_thread
            if gimbal_thread:
                gimbal_thread.on_camera_disconnected()

    def _on_camera_error(self, error):
        """Handle camera stream error."""
        self._add_log("CAMERA", f"Error: {error}")

    def _on_gimbal_update(self, pan, tilt):
        """Update gimbal UI when manually controlled."""
        self._gimbal_pan = int(pan)
        self._gimbal_tilt = int(tilt)
        if hasattr(self, '_gimbal_pan_label'):
            self._gimbal_pan_label.setText(f"{int(pan)}°")
        if hasattr(self, '_gimbal_tilt_label'):
            self._gimbal_tilt_label.setText(f"{int(tilt)}°")
        if hasattr(self, '_gimbal_hud'):
            self._gimbal_hud.set_gimbal(int(pan), int(tilt))

    def _take_snapshot(self):
        pixmap = self._video_canvas.pixmap() if hasattr(self, '_video_canvas') else None
        self._video_mgr.take_snapshot(pixmap)

    def _emergency_stop(self):
        self._send_command("stop")
        self._add_log("STOP", "Emergency stop activated")
        if self._detection_mgr and self._detection_mgr.follow_mode_active:
            self._detection_mgr.toggle_follow_mode()
    
    def _toggle_chassis_follow(self):
        """Toggle chassis follow mode (v key)."""
        if self._detection_mgr and self._detection_mgr._follow_controller:
            self._detection_mgr._follow_controller.toggle_chassis_follow()

    def _toggle_web_control(self):
        self._allow_remote_control = self._web_control_btn.isChecked()
        self._web_control_btn.setText(
            "WEB CONTROL: ON" if self._allow_remote_control else "WEB CONTROL: OFF"
        )
        self._remote_server.set_allowed(self._allow_remote_control)
        state = "enabled" if self._allow_remote_control else "disabled"
        self._add_log("REMOTE", f"Web control {state}")
        
        if self._allow_remote_control:
            self._conn_mgr.stop_camera()
            self._add_log("CAMERA", "Camera stopped for remote control")
        else:
            self._conn_mgr.start_camera()
            self._add_log("CAMERA", "Camera reconnected")

    def _relay_command(self, command):
        self._add_log("REMOTE", f"Relay: {command}")
        self._conn_mgr.send_command(command)

    def _send_command(self, command):
        if self._allow_remote_control:
            self._allow_remote_control = False
            self._web_control_btn.setChecked(False)
            self._web_control_btn.setText("WEB CONTROL: OFF")
            self._remote_server.set_allowed(False)
            self._add_log("REMOTE", "Local input reclaimed control")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._add_log("CMD", command)
        self._conn_mgr.send_command(command)

    def _add_log(self, category, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {
            "CONNECTED": "#10b981",
            "CMD": "#f1f5f9",
            "SAFETY": "#f59e0b",
            "STOP": "#ef4444",
            "SNAPSHOT": "#06b6d4",
            "REC": "#ef4444",
            "FOLLOW": "#8b5cf6",
            "ERROR": "#ef4444",
        }
        color = colors.get(category, "#94a3b8")
        html = f'<span style="color: #64748b;">[{timestamp}]</span> <span style="color: {color};">[{category}]</span> <span style="color: #94a3b8;">{message}</span>'
        if hasattr(self, '_log_display'):
            self._log_display.append(html)

    def keyPressEvent(self, event):
        self._input_handler.handle_key_press(event)

    def keyReleaseEvent(self, event):
        self._input_handler.handle_key_release(event)

    def _on_mouse_gimbal(self, pan, tilt):
        self._input_handler._gimbal_pan = int(pan)
        self._input_handler._gimbal_tilt = int(tilt)
        self._gimbal_pan = int(pan)
        self._gimbal_tilt = int(tilt)
        if hasattr(self, '_gimbal_pan_label'):
            self._gimbal_pan_label.setText(f"{int(pan)}°")
        if hasattr(self, '_gimbal_tilt_label'):
            self._gimbal_tilt_label.setText(f"{int(tilt)}°")
        if hasattr(self, '_gimbal_hud'):
            self._gimbal_hud.set_gimbal(int(pan), int(tilt))
        self._send_command(f"servo:{int(pan)},{int(tilt)}")

    def closeEvent(self, event):
        if hasattr(self, '_video_timer'):
            self._video_timer.stop()
        if self._remote_server:
            self._remote_server.stop()
        self._conn_mgr.stop_all()
        self._detection_mgr.stop_all()
        self._cloud_mgr.stop_all()
        save_config(self._config)
        event.accept()
