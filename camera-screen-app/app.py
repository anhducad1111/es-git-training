from datetime import datetime
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap, QFont, QPainter, QPen, QColor
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QSlider,
    QSizePolicy,
    QTextEdit,
)
from config import load_config, save_config
from camera_thread import CameraThread

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


RESOLUTIONS = [
    ("320x240 (QVGA)", "320x240"),
    ("640x480 (VGA)", "640x480"),
    ("800x600 (SVGA)", "800x600"),
    ("1024x768 (XGA)", "1024x768"),
    ("1600x1200 (UXGA)", "1600x1200"),
]


class CameraCanvas(QLabel):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(320, 240)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: #0a0e1a; border: 1px solid #1e293b;")
        self.setText("NO SIGNAL")
        self.setFont(QFont("Consolas", 14))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def update_frame(self, image):
        if isinstance(image, QImage):
            pixmap = QPixmap.fromImage(image)
        else:
            pixmap = image

        if not pixmap.isNull():
            scaled = pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )
            self.setPixmap(scaled)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.pixmap() is None or self.pixmap().isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2
        cy = self.height() / 2
        color = QColor(255, 255, 255, 200)

        painter.setPen(QPen(color, 2))
        painter.drawLine(int(cx), int(cy - 20), int(cx), int(cy - 5))
        painter.drawLine(int(cx), int(cy + 5), int(cx), int(cy + 20))
        painter.drawLine(int(cx - 20), int(cy), int(cx - 5), int(cy))
        painter.drawLine(int(cx + 5), int(cy), int(cx + 20), int(cy))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(int(cx), int(cy), 2, 2)

        painter.setPen(QPen(QColor(16, 185, 129), 1))
        painter.setFont(QFont("Consolas", 10))
        now = datetime.now().strftime("%H:%M:%S")
        painter.drawText(10, 20, now)

        painter.end()


class CameraApp(QWidget):
    def __init__(self):
        super().__init__()
        self._config = load_config()
        self._camera_thread = None
        self._base_url = f"http://{self._config['cam_ip']}"
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("ESP32-Cam FPV Client")
        self.setMinimumSize(900, 650)
        self.setStyleSheet("""
            QWidget { background-color: #0f172a; color: #e2e8f0; }
            QLabel { font-family: Consolas; }
            QLineEdit {
                background-color: #1e293b;
                border: 1px solid #334155;
                color: #e2e8f0;
                padding: 6px;
                font-family: Consolas;
                font-size: 13px;
            }
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                padding: 6px 12px;
                font-family: Consolas;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #3b82f6; }
            QPushButton:pressed { background-color: #1d4ed8; }
            QComboBox {
                background-color: #1e293b;
                border: 1px solid #334155;
                color: #e2e8f0;
                padding: 4px 8px;
                font-family: Consolas;
                font-size: 11px;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #1e293b;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #3b82f6;
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QTextEdit {
                background-color: #0a0e1a;
                border: 1px solid #1e293b;
                color: #94a3b8;
                font-family: Consolas;
                font-size: 11px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # URL bar
        url_bar = QHBoxLayout()
        url_bar.setSpacing(6)

        url_label = QLabel("URL:")
        url_bar.addWidget(url_label)

        self._url_input = QLineEdit()
        stream_url = f"{self._base_url}/{self._config['stream_path'].lstrip('/')}"
        self._url_input.setText(stream_url)
        url_bar.addWidget(self._url_input, 1)

        self._connect_btn = QPushButton("Connect")
        self._connect_btn.clicked.connect(self._toggle_connection)
        url_bar.addWidget(self._connect_btn)

        layout.addLayout(url_bar)

        # Controls row
        controls = QHBoxLayout()
        controls.setSpacing(12)

        # Resolution selector
        res_label = QLabel("Resolution:")
        controls.addWidget(res_label)

        self._res_combo = QComboBox()
        for label, _ in RESOLUTIONS:
            self._res_combo.addItem(label)
        self._res_combo.setCurrentIndex(1)
        self._res_combo.currentIndexChanged.connect(self._on_resolution_changed)
        controls.addWidget(self._res_combo)

        controls.addSpacing(20)

        # LED brightness
        led_label = QLabel("LED:")
        controls.addWidget(led_label)

        self._led_slider = QSlider(Qt.Orientation.Horizontal)
        self._led_slider.setRange(0, 255)
        self._led_slider.setValue(0)
        self._led_slider.setFixedWidth(100)
        self._led_slider.valueChanged.connect(self._on_led_changed)
        self._led_timer = QTimer()
        self._led_timer.setSingleShot(True)
        self._led_timer.setInterval(100)
        self._led_timer.timeout.connect(self._send_led)
        self._led_pending = 0
        controls.addWidget(self._led_slider)

        self._led_value = QLabel("0")
        self._led_value.setFixedWidth(30)
        controls.addWidget(self._led_value)

        controls.addSpacing(20)

        # JPEG quality
        qual_label = QLabel("Quality:")
        controls.addWidget(qual_label)

        self._quality_slider = QSlider(Qt.Orientation.Horizontal)
        self._quality_slider.setRange(0, 63)
        self._quality_slider.setValue(14)
        self._quality_slider.setFixedWidth(100)
        self._quality_slider.valueChanged.connect(self._on_quality_changed)
        controls.addWidget(self._quality_slider)

        self._quality_value = QLabel("14")
        self._quality_value.setFixedWidth(30)
        controls.addWidget(self._quality_value)

        controls.addStretch()

        layout.addLayout(controls)

        # Camera canvas
        self._canvas = CameraCanvas()
        layout.addWidget(self._canvas, 1)

        # Status bar
        status_bar = QHBoxLayout()
        status_bar.setSpacing(12)

        self._status_label = QLabel("Disconnected")
        self._status_label.setStyleSheet("color: #ef4444; font-size: 11px;")
        status_bar.addWidget(self._status_label)

        self._fps_label = QLabel("FPS: --")
        self._fps_label.setStyleSheet("color: #64748b; font-size: 11px;")
        status_bar.addWidget(self._fps_label)

        status_bar.addStretch()

        self._time_label = QLabel("")
        self._time_label.setStyleSheet("color: #64748b; font-size: 11px;")
        status_bar.addWidget(self._time_label)

        layout.addLayout(status_bar)

        # Log
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(80)
        layout.addWidget(self._log)

        # Timers
        self._fps_timer = QTimer()
        self._fps_timer.timeout.connect(self._update_fps)
        self._fps_timer.start(1000)
        self._frame_count = 0

        self._time_timer = QTimer()
        self._time_timer.timeout.connect(self._update_time)
        self._time_timer.start(1000)
        self._update_time()

    def _toggle_connection(self):
        if self._camera_thread and self._camera_thread.isRunning():
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        url = self._url_input.text().strip()
        if not url:
            self._add_log("ERROR", "No URL provided")
            return

        self._camera_thread = CameraThread(url)
        self._camera_thread.start()

        self._frame_timer = QTimer()
        self._frame_timer.timeout.connect(self._poll_frame)
        self._frame_timer.start(33)

        self._status_timer = QTimer()
        self._status_timer.timeout.connect(self._poll_status)
        self._status_timer.start(500)

        self._prev_connected = False
        self._connect_btn.setText("Disconnect")
        self._add_log("CAMERA", f"Connecting to {url}")

    def _disconnect(self):
        if self._camera_thread:
            self._camera_thread.stop()
            self._camera_thread = None
        if hasattr(self, '_frame_timer'):
            self._frame_timer.stop()
        if hasattr(self, '_status_timer'):
            self._status_timer.stop()
        self._connect_btn.setText("Connect")
        self._add_log("CAMERA", "Disconnected")

    def _poll_frame(self):
        if not self._camera_thread:
            return
        dropped = 0
        while not self._camera_thread.frame_queue.empty():
            try:
                image = self._camera_thread.frame_queue.get_nowait()
                dropped += 1
            except Exception:
                break
        if dropped > 0:
            self._on_frame(image)

    def _poll_status(self):
        if not self._camera_thread:
            return
        connected = self._camera_thread.connected
        if connected and not self._prev_connected:
            self._on_connected()
        elif not connected and self._prev_connected:
            self._on_disconnected()
        self._prev_connected = connected

        if self._camera_thread.error_msg:
            self._add_log("ERROR", self._camera_thread.error_msg)
            self._camera_thread.error_msg = None

    def _on_resolution_changed(self, index):
        _, res = RESOLUTIONS[index]
        url = f"{self._base_url}/{res}.mjpeg"
        self._url_input.setText(url)
        self._config["stream_path"] = f"/{res}.mjpeg"
        if self._camera_thread and self._camera_thread.isRunning():
            self._disconnect()
            self._connect()

    def _on_led_changed(self, value):
        self._led_value.setText(str(value))
        self._led_pending = value
        self._led_timer.start()

    def _send_led(self):
        self._send_api(f"/api/led?val={self._led_pending}")

    def _on_quality_changed(self, value):
        self._quality_value.setText(str(value))
        self._quality_pending = value
        if not hasattr(self, '_quality_timer'):
            self._quality_timer = QTimer()
            self._quality_timer.setSingleShot(True)
            self._quality_timer.setInterval(100)
            self._quality_timer.timeout.connect(self._send_quality)
        self._quality_timer.start()

    def _send_quality(self):
        self._send_api(f"/api/quality?val={self._quality_pending}")

    def _send_api(self, path):
        if not HAS_REQUESTS:
            return
        try:
            url = f"{self._base_url}{path}"
            requests.get(url, timeout=2)
        except Exception:
            pass

    def _on_connected(self):
        self._status_label.setText("Connected")
        self._status_label.setStyleSheet("color: #10b981; font-size: 11px;")
        self._add_log("CAMERA", "Stream connected")

    def _on_disconnected(self):
        self._status_label.setText("Disconnected")
        self._status_label.setStyleSheet("color: #ef4444; font-size: 11px;")

    def _on_error(self, error):
        self._add_log("ERROR", error)

    def _on_frame(self, image):
        self._canvas.update_frame(image)
        self._frame_count += 1

    def _update_fps(self):
        self._fps_label.setText(f"FPS: {self._frame_count}")
        self._frame_count = 0

    def _update_time(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._time_label.setText(now)

    def _add_log(self, category, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {
            "CAMERA": "#10b981",
            "ERROR": "#ef4444",
        }
        color = colors.get(category, "#94a3b8")
        html = f'<span style="color: #64748b;">[{timestamp}]</span> <span style="color: {color};">[{category}]</span> <span style="color: #94a3b8;">{message}</span>'
        self._log.append(html)

    def closeEvent(self, event):
        if self._camera_thread:
            self._camera_thread.stop()
        save_config(self._config)
        event.accept()
