from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QSlider, QVBoxLayout, QWidget
)


def create_bottom_controls(app):
    widget = QWidget()
    widget.setFixedHeight(80)
    widget.setStyleSheet("""
        background-color: #0f172a;
        border-top: 1px solid #1e293b;
    """)
    layout = QHBoxLayout()
    layout.setContentsMargins(16, 8, 16, 8)
    layout.setSpacing(10)

    speed_group = QGroupBox("SPEED")
    speed_group.setStyleSheet("""
        background-color: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 6px;
        padding: 8px;
    """)
    speed_layout = QHBoxLayout()
    speed_layout.setContentsMargins(8, 4, 8, 4)
    speed_layout.setSpacing(8)

    app._speed_slider = QSlider(Qt.Orientation.Horizontal)
    app._speed_slider.setRange(150, 255)
    app._speed_slider.setValue(app._current_speed)
    app._speed_slider.setFixedWidth(100)
    app._speed_slider.valueChanged.connect(lambda v: _on_speed_change(app, v))
    speed_layout.addWidget(app._speed_slider)

    app._speed_label = QLabel(f"{app._current_speed}")
    app._speed_label.setStyleSheet("""
        color: #06b6d4;
        font-size: 12px;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
    """)
    app._speed_label.setFixedWidth(60)
    speed_layout.addWidget(app._speed_label)

    speed_group.setLayout(speed_layout)
    layout.addWidget(speed_group)

    brake_group = QGroupBox("BRAKE")
    brake_group.setStyleSheet("""
        background-color: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 6px;
        padding: 8px;
    """)
    brake_layout = QHBoxLayout()
    brake_layout.setContentsMargins(8, 4, 8, 4)
    brake_layout.setSpacing(8)

    app._brake_toggle = QPushButton("ON")
    app._brake_toggle.setCheckable(True)
    app._brake_toggle.setChecked(True)
    app._brake_toggle.setFixedWidth(50)
    app._brake_toggle.setFixedHeight(24)
    app._brake_toggle.setStyleSheet("""
        QPushButton {
            background-color: #10b981;
            color: white;
            font-weight: 600;
            font-size: 10px;
            border: none;
            border-radius: 12px;
            padding: 2px 8px;
        }
        QPushButton:!checked {
            background-color: #475569;
        }
    """)
    app._brake_toggle.clicked.connect(lambda: _toggle_brake(app))
    brake_layout.addWidget(app._brake_toggle)

    brake_group.setLayout(brake_layout)
    layout.addWidget(brake_group)

    layout.addSpacing(10)

    gimbal_group = QGroupBox("GIMBAL")
    gimbal_group.setStyleSheet("""
        background-color: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 6px;
        padding: 8px;
    """)
    gimbal_layout = QHBoxLayout()
    gimbal_layout.setContentsMargins(8, 4, 8, 4)
    gimbal_layout.setSpacing(8)

    pan_label = QLabel("PAN")
    pan_label.setStyleSheet("color: #475569; font-size: 9px; letter-spacing: 1px;")
    gimbal_layout.addWidget(pan_label)

    app._gimbal_pan_label = QLabel(f"{app._gimbal_pan}°")
    app._gimbal_pan_label.setStyleSheet("""
        color: #e2e8f0;
        font-size: 11px;
        font-family: 'JetBrains Mono', monospace;
    """)
    gimbal_layout.addWidget(app._gimbal_pan_label)

    tilt_label = QLabel("TILT")
    tilt_label.setStyleSheet("color: #475569; font-size: 9px; letter-spacing: 1px;")
    gimbal_layout.addWidget(tilt_label)

    app._gimbal_tilt_label = QLabel(f"{app._gimbal_tilt}°")
    app._gimbal_tilt_label.setStyleSheet("""
        color: #e2e8f0;
        font-size: 11px;
        font-family: 'JetBrains Mono', monospace;
    """)
    gimbal_layout.addWidget(app._gimbal_tilt_label)

    center_btn = QPushButton("C")
    center_btn.setFixedSize(28, 28)
    center_btn.setStyleSheet("""
        QPushButton {
            background-color: #1e293b;
            border: 1px solid #334155;
            color: #06b6d4;
            font-weight: 700;
            font-size: 10px;
            border-radius: 14px;
        }
        QPushButton:hover {
            background-color: #334155;
        }
    """)
    center_btn.clicked.connect(app._center_gimbal)
    gimbal_layout.addWidget(center_btn)

    app._mouse_gimbal_btn = QPushButton("MOUSE")
    app._mouse_gimbal_btn.setFixedHeight(28)
    app._mouse_gimbal_btn.setCheckable(True)
    app._mouse_gimbal_btn.setChecked(True)
    app._mouse_gimbal_btn.setStyleSheet("""
        QPushButton {
            background-color: #1e293b;
            border: 1px solid #334155;
            color: #06b6d4;
            font-weight: 600;
            font-size: 10px;
            padding: 4px 12px;
            letter-spacing: 1px;
        }
        QPushButton:checked {
            background-color: #06b6d4;
            color: #0a0e1a;
        }
    """)
    app._mouse_gimbal_btn.clicked.connect(lambda: _toggle_mouse_gimbal(app))
    gimbal_layout.addWidget(app._mouse_gimbal_btn)

    gimbal_group.setLayout(gimbal_layout)
    layout.addWidget(gimbal_group)

    cloud_group = QGroupBox("CLOUD")
    cloud_group.setStyleSheet("""
        background-color: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 6px;
        padding: 8px;
    """)
    cloud_layout = QHBoxLayout()
    cloud_layout.setContentsMargins(8, 4, 8, 4)

    app._cloud_send_btn = QPushButton("SEND")
    app._cloud_send_btn.setFixedHeight(28)
    app._cloud_send_btn.setStyleSheet("""
        QPushButton {
            background-color: #7c3aed;
            color: white;
            font-weight: 600;
            font-size: 10px;
            border: none;
            padding: 4px 16px;
            letter-spacing: 1px;
        }
        QPushButton:hover {
            background-color: #6d28d9;
        }
    """)
    app._cloud_send_btn.clicked.connect(app._manual_send_to_cloud)
    cloud_layout.addWidget(app._cloud_send_btn)

    app._toggle_view_btn = QPushButton("DATA")
    app._toggle_view_btn.setFixedHeight(28)
    app._toggle_view_btn.setCheckable(True)
    app._toggle_view_btn.setStyleSheet("""
        QPushButton {
            background-color: #1e293b;
            border: 1px solid #334155;
            color: #06b6d4;
            font-weight: 600;
            font-size: 10px;
            padding: 4px 12px;
            letter-spacing: 1px;
        }
        QPushButton:checked {
            background-color: #06b6d4;
            color: #0a0e1a;
        }
    """)
    app._toggle_view_btn.clicked.connect(app._toggle_view)
    cloud_layout.addWidget(app._toggle_view_btn)

    cloud_group.setLayout(cloud_layout)
    layout.addWidget(cloud_group)

    widget.setLayout(layout)
    return widget


def _on_speed_change(app, value):
    app._global_speed = value
    app._speed_label.setText(f"{value}")
    app._send_command(f"speed:{value}")


def _toggle_brake(app):
    checked = app._brake_toggle.isChecked()
    app._brake_toggle.setText("ON" if checked else "OFF")
    if hasattr(app, '_esp32_api'):
        app._esp32_api.set_brake(checked)
    app._add_log("SAFETY", f"Auto-brake {'enabled' if checked else 'disabled'}")


def _toggle_mouse_gimbal(app):
    checked = app._mouse_gimbal_btn.isChecked()
    if hasattr(app, '_video_canvas'):
        app._video_canvas._mouse_gimbal_enabled = checked
    app._add_log("GIMBAL", f"Mouse gimbal {'enabled' if checked else 'disabled'}")
