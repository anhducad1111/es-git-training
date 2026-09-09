from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget
)
from mjpeg_receiver import MJPEGReceiver


def create_main_view(app):
    widget = QWidget()
    layout = QVBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    video_container = QWidget()
    video_layout = QVBoxLayout()
    video_layout.setContentsMargins(0, 0, 0, 0)
    video_layout.setSpacing(0)

    from widgets.video_canvas import VideoCanvas
    app._video_canvas = VideoCanvas(app)
    video_layout.addWidget(app._video_canvas, 1)

    from widgets.gimbal_hud import GimbalHUD
    app._gimbal_hud = GimbalHUD()
    app._gimbal_hud.setParent(app._video_canvas)
    app._gimbal_hud.move(10, app._video_canvas.height() - 190)

    resolution_widget = QWidget()
    resolution_widget.setFixedHeight(32)
    resolution_widget.setStyleSheet("background-color: #131b2e; border-top: 1px solid #334155;")
    res_layout = QHBoxLayout()
    res_layout.setContentsMargins(8, 4, 8, 4)

    app._resolution_combo = QComboBox()
    app._resolution_combo.addItems(["640x480 (30 FPS)", "1280x720 (15 FPS)", "320x240 (60 FPS)", "160x120 (90 FPS)"])
    app._resolution_combo.setFixedWidth(180)
    app._resolution_combo.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 4px; padding: 2px 6px; color: #f1f5f9; font-size: 11px;")
    app._resolution_combo.currentTextChanged.connect(lambda text: _on_resolution_change(app, text))
    res_layout.addWidget(app._resolution_combo)

    app._resolution_label = QLabel("640x480")
    app._resolution_label.setStyleSheet("color: #94a3b8; font-size: 11px; font-family: 'JetBrains Mono', monospace; margin-left: 8px;")
    res_layout.addWidget(app._resolution_label)

    res_layout.addStretch()
    resolution_widget.setLayout(res_layout)
    video_layout.addWidget(resolution_widget)

    video_container.setLayout(video_layout)
    layout.addWidget(video_container, 1)

    widget.setLayout(layout)
    return widget


def _on_resolution_change(app, text):
    if "640x480" in text:
        app._send_command("resolution:640,480")
        app._resolution_label.setText("640x480")
        _restart_camera_stream(app, "640x480")
    elif "1280x720" in text:
        app._send_command("resolution:1280,720")
        app._resolution_label.setText("1280x720")
        _restart_camera_stream(app, "1280x720")
    elif "320x240" in text:
        app._send_command("resolution:320,240")
        app._resolution_label.setText("320x240")
        _restart_camera_stream(app, "320x240")
    elif "160x120" in text:
        app._send_command("resolution:160,120")
        app._resolution_label.setText("160x120")
        _restart_camera_stream(app, "160x120")
    app._add_log("VIDEO", f"Resolution changed to {text}")
    app.setFocus()


def _restart_camera_stream(app, resolution):
    if app._video_receiver:
        app._video_receiver.stop()
    stream_url = f"http://{app._config['cam_ip']}/{resolution}.mjpeg"
    app._video_receiver = MJPEGReceiver(stream_url)
    app._video_receiver.connected.connect(lambda: app._on_camera_connected())
    app._video_receiver.disconnected.connect(lambda: app._on_camera_disconnected())
    app._video_receiver.error.connect(lambda e: app._on_camera_error(e))
    app._video_receiver.stats_updated.connect(lambda s: app._on_video_stats(s))
    app._video_receiver.start()
