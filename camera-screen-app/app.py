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
    QSizePolicy,
    QTextEdit,
)
from config import load_config, save_config
from camera_thread import CameraThread


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
                Qt.TransformationMode.SmoothTransformation,
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

        # Crosshair
        painter.setPen(QPen(color, 2))
        painter.drawLine(int(cx), int(cy - 20), int(cx), int(cy - 5))
        painter.drawLine(int(cx), int(cy + 5), int(cx), int(cy + 20))
        painter.drawLine(int(cx - 20), int(cy), int(cx - 5), int(cy))
        painter.drawLine(int(cx + 5), int(cy), int(cx + 20), int(cy))

        # Center dot
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(int(cx), int(cy), 2, 2)

        # Timestamp overlay
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
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Camera Screen Demo")
        self.setMinimumSize(800, 600)
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
                padding: 6px 16px;
                font-family: Consolas;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #3b82f6; }
            QPushButton:pressed { background-color: #1d4ed8; }
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
        self._url_input.setText(f"http://{self._config['cam_ip']}:{self._config['cam_port']}{self._config['stream_path']}")
        url_bar.addWidget(self._url_input, 1)

        self._connect_btn = QPushButton("Connect")
        self._connect_btn.clicked.connect(self._toggle_connection)
        url_bar.addWidget(self._connect_btn)

        layout.addLayout(url_bar)

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

        # Timestamp
        self._time_label = QLabel("")
        self._time_label.setStyleSheet("color: #64748b; font-size: 11px;")
        status_bar.addWidget(self._time_label)

        layout.addLayout(status_bar)

        # Log
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(80)
        layout.addWidget(self._log)

        # Update timer for FPS
        self._fps_timer = QTimer()
        self._fps_timer.timeout.connect(self._update_fps)
        self._fps_timer.start(1000)
        self._frame_count = 0

        # Time update
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

        # Save IP to config
        if "://" in url:
            host = url.split("://")[1].split("/")[0]
            if ":" in host:
                ip, port = host.split(":")
                self._config["cam_ip"] = ip
                self._config["cam_port"] = int(port)
            else:
                self._config["cam_ip"] = host
            path = "/" + "/".join(url.split("://")[1].split("/")[1:])
            self._config["stream_path"] = path

        self._camera_thread = CameraThread(url)
        self._camera_thread.connected.connect(self._on_connected)
        self._camera_thread.disconnected.connect(self._on_disconnected)
        self._camera_thread.error.connect(self._on_error)
        self._camera_thread.frame_received.connect(self._on_frame)
        self._camera_thread.start()

        self._connect_btn.setText("Disconnect")
        self._add_log("CAMERA", f"Connecting to {url}")

    def _disconnect(self):
        if self._camera_thread:
            self._camera_thread.stop()
            self._camera_thread = None
        self._connect_btn.setText("Connect")
        self._add_log("CAMERA", "Disconnected")

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
