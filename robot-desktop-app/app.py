from datetime import datetime
import requests
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QPixmap, QImage, QFont, QColor, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSlider,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QStackedWidget,
)
from config import load_config, save_config
from cloud_api import CloudAPI
from stubs.stub_video import StubVideoThread
from stubs.stub_telemetry import StubTelemetryThread


DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #0b1326;
    color: #f1f5f9;
}
QGroupBox {
    font-weight: bold;
    border: 1px solid #334155;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
QPushButton {
    background-color: #1d4ed8;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #2563eb;
}
QPushButton:pressed {
    background-color: #1e40af;
}
QSlider::groove:horizontal {
    border: 1px solid #334155;
    height: 8px;
    background: #1e293b;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #3b82f6;
    border: none;
    width: 16px;
    height: 16px;
    margin: -4px 0;
    border-radius: 8px;
}
QSlider::sub-page:horizontal {
    background: #3b82f6;
    border-radius: 4px;
}
QLineEdit {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 4px 8px;
    color: #f1f5f9;
}
QTextEdit {
    background-color: #131b2e;
    border: 1px solid #334155;
    border-radius: 4px;
    color: #f1f5f9;
}
QLabel {
    color: #94a3b8;
}
"""


class VideoCanvas(QLabel):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(640, 480)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: #0f172a; border: 1px solid #334155;")
        self.setText("No Video Feed")
        self.setFont(QFont("JetBrains Mono", 14))

    def update_frame(self, jpeg_data):
        pixmap = QPixmap()
        pixmap.loadFromData(jpeg_data)
        scaled = pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)


class SensorCard(QWidget):
    def __init__(self, name, unit, icon="", min_val=0, max_val=100):
        super().__init__()
        self.min_val = min_val
        self.max_val = max_val
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        top_row = QHBoxLayout()
        top_row.setSpacing(4)

        self.icon_label = QLabel(icon)
        self.icon_label.setFont(QFont("Segoe UI Emoji", 14))
        self.icon_label.setFixedWidth(24)
        top_row.addWidget(self.icon_label)

        self.name_label = QLabel(name)
        self.name_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        top_row.addWidget(self.name_label)

        top_row.addStretch()

        self.value_label = QLabel("--")
        self.value_label.setStyleSheet("color: #f1f5f9; font-size: 14px; font-weight: bold;")
        top_row.addWidget(self.value_label)

        self.unit_label = QLabel(unit)
        self.unit_label.setStyleSheet("color: #64748b; font-size: 11px;")
        top_row.addWidget(self.unit_label)

        layout.addLayout(top_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: #1e293b;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress)

        self.setLayout(layout)
        self.setStyleSheet(
            "background-color: #1e293b; border-radius: 6px; padding: 4px;"
        )

    def update_value(self, value, progress=None):
        self.value_label.setText(str(value))
        if progress is not None:
            self.progress.setValue(int(min(100, max(0, progress))))


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

        self.init_ui()
        self.connect_signals()
        self.start_stubs()

    def init_ui(self):
        self.setWindowTitle("Rover Teleop Cockpit v2.4.0")
        self.setMinimumSize(1400, 800)
        self.setStyleSheet(DARK_STYLE)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_layout.addWidget(self._create_header())

        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)

        self._center_stack = QStackedWidget()
        self._center_stack.addWidget(self._create_main_view())
        self._center_stack.addWidget(self._create_diagnostics_view())
        content.addWidget(self._center_stack, 1)

        self._sidebar = self._create_sidebar()
        content.addWidget(self._sidebar)

        main_layout.addLayout(content, 1)

        main_layout.addWidget(self._create_bottom_controls())
        main_layout.addWidget(self._create_log_panel())

    def _create_header(self):
        header = QWidget()
        header.setFixedHeight(48)
        header.setStyleSheet("background-color: #131b2e; border-bottom: 1px solid #334155;")
        layout = QHBoxLayout()
        layout.setContentsMargins(16, 0, 16, 0)

        title = QLabel("Rover Teleop Cockpit v2.4.0")
        title.setStyleSheet("color: #f1f5f9; font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        layout.addStretch()

        rover_label = QLabel("Rover IP:")
        rover_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(rover_label)

        self._rover_ip_input = QLineEdit(self._config['car_ip'])
        self._rover_ip_input.setFixedWidth(130)
        self._rover_ip_input.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 4px; padding: 2px 6px; color: #f1f5f9; font-size: 11px;")
        self._rover_ip_input.returnPressed.connect(self._on_ip_changed)
        layout.addWidget(self._rover_ip_input)

        cam_label = QLabel("Cam IP:")
        cam_label.setStyleSheet("color: #94a3b8; font-size: 11px; margin-left: 12px;")
        layout.addWidget(cam_label)

        self._cam_ip_input = QLineEdit(self._config['cam_ip'])
        self._cam_ip_input.setFixedWidth(130)
        self._cam_ip_input.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 4px; padding: 2px 6px; color: #f1f5f9; font-size: 11px;")
        self._cam_ip_input.returnPressed.connect(self._on_ip_changed)
        layout.addWidget(self._cam_ip_input)

        self._rover_status = QLabel("● Rover")
        self._rover_status.setStyleSheet("color: #10b981; font-size: 11px; margin-left: 16px;")
        layout.addWidget(self._rover_status)

        self._cam_status = QLabel("● Cam")
        self._cam_status.setStyleSheet("color: #10b981; font-size: 11px; margin-left: 8px;")
        layout.addWidget(self._cam_status)

        header.setLayout(layout)
        return header

    def _on_ip_changed(self):
        self._config['car_ip'] = self._rover_ip_input.text()
        self._config['cam_ip'] = self._cam_ip_input.text()
        save_config(self._config)
        self._add_log("CONFIG", f"IPs updated: Rover={self._config['car_ip']}, Cam={self._config['cam_ip']}")

    def _create_main_view(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        video_container = QWidget()
        video_layout = QVBoxLayout()
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.setSpacing(0)

        self._video_canvas = VideoCanvas()
        video_layout.addWidget(self._video_canvas, 1)

        resolution_widget = QWidget()
        resolution_widget.setFixedHeight(32)
        resolution_widget.setStyleSheet("background-color: #131b2e; border-top: 1px solid #334155;")
        res_layout = QHBoxLayout()
        res_layout.setContentsMargins(8, 4, 8, 4)

        from PyQt6.QtWidgets import QComboBox
        self._resolution_combo = QComboBox()
        self._resolution_combo.addItems(["640x480 (30 FPS)", "1280x720 (15 FPS)", "320x240 (60 FPS)"])
        self._resolution_combo.setFixedWidth(180)
        self._resolution_combo.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 4px; padding: 2px 6px; color: #f1f5f9; font-size: 11px;")
        self._resolution_combo.currentTextChanged.connect(self._on_resolution_change)
        res_layout.addWidget(self._resolution_combo)

        res_layout.addStretch()
        resolution_widget.setLayout(res_layout)
        video_layout.addWidget(resolution_widget)

        video_container.setLayout(video_layout)
        layout.addWidget(video_container, 1)

        widget.setLayout(layout)
        return widget

    def _on_resolution_change(self, text):
        if "640x480" in text:
            self._send_command("resolution:640,480")
        elif "1280x720" in text:
            self._send_command("resolution:1280,720")
        elif "320x240" in text:
            self._send_command("resolution:320,240")
        self._add_log("VIDEO", f"Resolution changed to {text}")

    def _create_diagnostics_view(self):
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)

        charts_title = QLabel("Historical Sensor Analytics")
        charts_title.setStyleSheet("color: #f1f5f9; font-size: 16px; font-weight: bold;")
        left_layout.addWidget(charts_title)

        charts_placeholder = QLabel("Charts will be displayed here")
        charts_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        charts_placeholder.setStyleSheet(
            "background-color: #1e293b; border-radius: 6px; padding: 40px; color: #64748b;"
        )
        left_layout.addWidget(charts_placeholder)

        left_panel.setLayout(left_layout)
        layout.addWidget(left_panel, 1)

        right_panel = QWidget()
        right_panel.setFixedWidth(384)
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)

        chat_title = QLabel("Local AI Sensor Analyst (Ollama)")
        chat_title.setStyleSheet("color: #f1f5f9; font-size: 14px; font-weight: bold;")
        right_layout.addWidget(chat_title)

        self._chat_display = QTextEdit()
        self._chat_display.setReadOnly(True)
        self._chat_display.setStyleSheet("background-color: #131b2e; border-radius: 6px; padding: 8px;")
        right_layout.addWidget(self._chat_display, 1)

        chat_input_layout = QHBoxLayout()
        self._chat_input = QLineEdit()
        self._chat_input.setPlaceholderText("Ask about sensor data...")
        chat_input_layout.addWidget(self._chat_input)

        send_btn = QPushButton("Send")
        send_btn.setFixedWidth(60)
        send_btn.clicked.connect(self._send_chat)
        chat_input_layout.addWidget(send_btn)

        right_layout.addLayout(chat_input_layout)

        right_panel.setLayout(right_layout)
        layout.addWidget(right_panel)

        widget.setLayout(layout)
        return widget

    def _create_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(320)
        sidebar.setStyleSheet("background-color: #131b2e; border-left: 1px solid #334155;")
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()
        header_label = QLabel("Telemetry Sensors")
        header_label.setStyleSheet("color: #f1f5f9; font-weight: bold; font-size: 13px;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()

        self._link_label = QLabel("Link: 98% (Optimal)")
        self._link_label.setStyleSheet("color: #10b981; font-size: 11px;")
        header_layout.addWidget(self._link_label)

        estop_btn = QPushButton("E-STOP")
        estop_btn.setFixedWidth(60)
        estop_btn.setStyleSheet("background-color: #ef4444; font-weight: bold; padding: 4px 8px;")
        estop_btn.clicked.connect(self._emergency_stop)
        header_layout.addWidget(estop_btn)

        layout.addLayout(header_layout)

        self._temp_card = SensorCard("Chassis Core Temp", "°C", "🌡", 0, 60)
        layout.addWidget(self._temp_card)

        self._humidity_card = SensorCard("Ambient Humidity", "%", "💧", 0, 100)
        layout.addWidget(self._humidity_card)

        self._gas_card = SensorCard("Air Purity Metric", "PPM", "🌫", 0, 1000)
        layout.addWidget(self._gas_card)

        self._distance_card = SensorCard("Obstacle Distance", "cm", "📏", 0, 200)
        layout.addWidget(self._distance_card)

        health_group = QGroupBox("Subsystem Health")
        health_layout = QVBoxLayout()

        for name in ["ESP32 Main MCU", "Motor Drivers", "Pan/Tilt Servos"]:
            row = QHBoxLayout()
            label = QLabel(name)
            label.setStyleSheet("color: #94a3b8; font-size: 11px;")
            row.addWidget(label)
            row.addStretch()
            status = QLabel("OK")
            status.setStyleSheet("color: #10b981; font-size: 11px; font-weight: bold;")
            row.addWidget(status)
            health_layout.addLayout(row)

        battery_row = QHBoxLayout()
        battery_label = QLabel("Battery Level")
        battery_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        battery_row.addWidget(battery_label)
        battery_row.addStretch()
        self._battery_label = QLabel("12.4V")
        self._battery_label.setStyleSheet("color: #f1f5f9; font-size: 11px; font-weight: bold;")
        battery_row.addWidget(self._battery_label)
        health_layout.addLayout(battery_row)

        health_group.setLayout(health_layout)
        layout.addWidget(health_group)

        snapshot_btn = QPushButton("Take Snapshot")
        snapshot_btn.setStyleSheet("background-color: #1d4ed8;")
        snapshot_btn.clicked.connect(self._take_snapshot)
        layout.addWidget(snapshot_btn)

        diag_btn = QPushButton("System Diagnostics")
        diag_btn.setStyleSheet("background-color: #475569;")
        diag_btn.clicked.connect(self._toggle_view)
        layout.addWidget(diag_btn)

        config_btn = QPushButton("Device Configuration")
        config_btn.setStyleSheet("background-color: #475569;")
        layout.addWidget(config_btn)

        follow_btn = QPushButton("Follow Mode")
        follow_btn.setStyleSheet("background-color: #7c3aed;")
        follow_btn.clicked.connect(self._toggle_follow_mode)
        layout.addWidget(follow_btn)

        layout.addStretch()

        sidebar.setLayout(layout)
        return sidebar

    def _create_bottom_controls(self):
        widget = QWidget()
        widget.setFixedHeight(100)
        widget.setStyleSheet("background-color: #131b2e; border-top: 1px solid #334155;")
        layout = QHBoxLayout()
        layout.setContentsMargins(16, 8, 16, 8)

        speed_group = QGroupBox("Motor Speed")
        speed_layout = QVBoxLayout()

        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(150, 255)
        self._speed_slider.setValue(self._current_speed)
        self._speed_slider.valueChanged.connect(self._on_speed_change)
        speed_layout.addWidget(self._speed_slider)

        self._speed_label = QLabel(f"{self._current_speed} ({int(self._current_speed / 255 * 100)}%)")
        self._speed_label.setStyleSheet("color: #f1f5f9; font-size: 11px;")
        self._speed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        speed_layout.addWidget(self._speed_label)

        speed_group.setLayout(speed_layout)
        layout.addWidget(speed_group, 1)

        brake_group = QGroupBox("Auto-Brake")
        brake_layout = QVBoxLayout()

        self._brake_toggle = QPushButton("ON")
        self._brake_toggle.setCheckable(True)
        self._brake_toggle.setChecked(True)
        self._brake_toggle.setMinimumHeight(36)
        self._brake_toggle.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                font-weight: bold;
                font-size: 13px;
                border-radius: 4px;
                padding: 4px 16px;
            }
            QPushButton:checked {
                background-color: #10b981;
            }
            QPushButton:!checked {
                background-color: #6b7280;
            }
        """)
        self._brake_toggle.clicked.connect(self._toggle_brake)
        brake_layout.addWidget(self._brake_toggle)

        brake_label = QLabel("Threshold: 30cm")
        brake_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        brake_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brake_layout.addWidget(brake_label)

        brake_group.setLayout(brake_layout)
        layout.addWidget(brake_group, 1)

        gimbal_group = QGroupBox("Gimbal")
        gimbal_layout = QVBoxLayout()

        self._gimbal_label = QLabel(f"Pan: {self._gimbal_pan}°  Tilt: {self._gimbal_tilt}°")
        self._gimbal_label.setStyleSheet("color: #f1f5f9; font-size: 12px;")
        self._gimbal_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gimbal_layout.addWidget(self._gimbal_label)

        center_btn = QPushButton("Center")
        center_btn.setMinimumHeight(36)
        center_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                font-weight: bold;
                font-size: 13px;
                border-radius: 4px;
                padding: 4px 16px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        center_btn.clicked.connect(self._center_gimbal)
        gimbal_layout.addWidget(center_btn)

        gimbal_group.setLayout(gimbal_layout)
        layout.addWidget(gimbal_group, 1)

        keys_group = QGroupBox("Controls")
        keys_layout = QVBoxLayout()

        keys_label = QLabel("W/S: Drive  A/D: Turn")
        keys_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        keys_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        keys_layout.addWidget(keys_label)

        keys_label2 = QLabel("I/J/K/L: Gimbal  C: Center")
        keys_label2.setStyleSheet("color: #94a3b8; font-size: 11px;")
        keys_label2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        keys_layout.addWidget(keys_label2)

        keys_group.setLayout(keys_layout)
        layout.addWidget(keys_group, 1)

        stop_group = QGroupBox("")
        stop_layout = QVBoxLayout()

        stop_btn = QPushButton("STOP")
        stop_btn.setFixedHeight(40)
        stop_btn.setStyleSheet("background-color: #ef4444; font-size: 14px;")
        stop_btn.clicked.connect(self._emergency_stop)
        stop_layout.addWidget(stop_btn)

        stop_group.setLayout(stop_layout)
        layout.addWidget(stop_group, 1)

        widget.setLayout(layout)
        return widget

    def _create_log_panel(self):
        widget = QWidget()
        widget.setFixedHeight(100)
        widget.setStyleSheet("background-color: #0f172a; border-top: 1px solid #334155;")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 4, 16, 4)

        header_layout = QHBoxLayout()
        log_toggle = QLabel("[LOG] Click to expand/collapse")
        log_toggle.setStyleSheet("color: #94a3b8; font-size: 11px;")
        header_layout.addWidget(log_toggle)

        header_layout.addStretch()

        baud_label = QLabel("115200 Baud")
        baud_label.setStyleSheet("color: #64748b; font-size: 11px;")
        header_layout.addWidget(baud_label)
        layout.addLayout(header_layout)

        self._log_display = QTextEdit()
        self._log_display.setReadOnly(True)
        self._log_display.setStyleSheet("background-color: #0f172a; border: none; color: #94a3b8; font-size: 11px;")
        layout.addWidget(self._log_display)

        widget.setLayout(layout)
        return widget

    def connect_signals(self):
        self.log_message.connect(self._add_log)

    def start_stubs(self):
        self._video_thread = StubVideoThread()
        self._video_thread.frame_received.connect(self._video_canvas.update_frame)
        self._video_thread.start()

        self._telemetry_thread = StubTelemetryThread()
        self._telemetry_thread.data_received.connect(self._update_telemetry)
        self._telemetry_thread.start()

        self._add_log("CONNECTED", "Stub connections active (simulated)")

        self._cloud_api = CloudAPI()
        self._test_cloud_connection()
        self._test_rover_connection()
        self._test_camera_connection()

    def _update_telemetry(self, data):
        self._temp_card.update_value(f"{data['temperature']}°C", data['temperature'] / 60 * 100)
        self._humidity_card.update_value(f"{data['humidity']}%", data['humidity'])
        self._gas_card.update_value(f"{int(data['gas'])} PPM", data['gas'] / 1000 * 100)
        self._distance_card.update_value(f"{data['distance']} cm", data['distance'] / 200 * 100)
        self._link_label.setText(f"Link: {data['link_quality']}%")
        self._battery_label.setText(f"{data['battery_voltage']}V")

    def _test_cloud_connection(self):
        try:
            result = self._cloud_api.get_rovers()
            if "error" in result:
                if "timed out" in result["error"] or "ConnectTimeout" in result["error"]:
                    self._add_log("CLOUD", "Server not reachable (timeout) - server may be offline")
                elif "NameResolutionError" in result["error"] or "resolve" in result["error"]:
                    self._add_log("CLOUD", "Cannot resolve hostname - check server address")
                else:
                    self._add_log("CLOUD", f"Connection failed: {result['error'][:80]}")
            else:
                self._add_log("CLOUD", "Connected to cloud API OK")
        except Exception as e:
            self._add_log("CLOUD", f"Connection failed: {e}")

    def _test_rover_connection(self):
        try:
            resp = requests.get(f"http://{self._config['car_ip']}/api/telemetry", timeout=5)
            if resp.status_code == 200:
                self._add_log("ROVER", f"Connected to ESP32-Car OK ({self._config['car_ip']})")
            else:
                self._add_log("ROVER", f"ESP32-Car responded with status {resp.status_code}")
        except requests.exceptions.Timeout:
            self._add_log("ROVER", f"ESP32-Car timeout ({self._config['car_ip']}) - rover may be offline")
        except requests.exceptions.ConnectionError:
            self._add_log("ROVER", f"Cannot connect to ESP32-Car ({self._config['car_ip']})")
        except Exception as e:
            self._add_log("ROVER", f"Connection failed: {e}")

    def _test_camera_connection(self):
        try:
            resp = requests.get(f"http://{self._config['cam_ip']}/resolutions.csv", timeout=5)
            if resp.status_code == 200:
                self._add_log("CAMERA", f"Connected to ESP32-Cam OK ({self._config['cam_ip']})")
            else:
                self._add_log("CAMERA", f"ESP32-Cam responded with status {resp.status_code}")
        except requests.exceptions.Timeout:
            self._add_log("CAMERA", f"ESP32-Cam timeout ({self._config['cam_ip']}) - camera may be offline")
        except requests.exceptions.ConnectionError:
            self._add_log("CAMERA", f"Cannot connect to ESP32-Cam ({self._config['cam_ip']})")
        except Exception as e:
            self._add_log("CAMERA", f"Connection failed: {e}")

    def _on_speed_change(self, value):
        self._current_speed = value
        percent = int(value / 255 * 100)
        self._speed_label.setText(f"{value} ({percent}%)")

    def _toggle_brake(self):
        checked = self._brake_toggle.isChecked()
        self._brake_toggle.setText("ON" if checked else "OFF")
        self._add_log("SAFETY", f"Auto-brake {'enabled' if checked else 'disabled'}")

    def _center_gimbal(self):
        self._gimbal_pan = 90
        self._gimbal_tilt = 90
        self._gimbal_label.setText(f"Pan: 90°  Tilt: 90°")
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
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return
        key = event.key()
        if key in (Qt.Key.Key_W, Qt.Key.Key_S, Qt.Key.Key_A, Qt.Key.Key_D):
            self._send_command("stop")
        else:
            super().keyReleaseEvent(event)

    def _update_gimbal(self):
        self._gimbal_label.setText(f"Pan: {self._gimbal_pan}°  Tilt: {self._gimbal_tilt}°")
        self._send_command(f"servo:{self._gimbal_pan},{self._gimbal_tilt}")

    def closeEvent(self, event):
        if self._video_thread:
            self._video_thread.stop()
        if self._telemetry_thread:
            self._telemetry_thread.stop()
        save_config(self._config)
        event.accept()
