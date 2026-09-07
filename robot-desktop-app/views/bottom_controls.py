from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QSlider, QVBoxLayout, QWidget
)


def create_bottom_controls(app):
    widget = QWidget()
    widget.setFixedHeight(80)
    widget.setStyleSheet("background-color: #131b2e; border-top: 1px solid #243147;")
    layout = QHBoxLayout()
    layout.setContentsMargins(12, 6, 12, 6)
    layout.setSpacing(8)

    speed_group = QGroupBox("Motor Speed")
    speed_group.setStyleSheet("background-color: #171f33; border: 1px solid #243147; border-radius: 6px; padding: 6px;")
    speed_layout = QHBoxLayout()
    speed_layout.setContentsMargins(8, 4, 8, 4)
    speed_layout.setSpacing(8)

    app._speed_slider = QSlider(Qt.Orientation.Horizontal)
    app._speed_slider.setRange(150, 255)
    app._speed_slider.setValue(app._current_speed)
    app._speed_slider.setFixedWidth(120)
    app._speed_slider.valueChanged.connect(lambda v: _on_speed_change(app, v))
    speed_layout.addWidget(app._speed_slider)

    app._speed_label = QLabel(f"{app._current_speed} ({int(app._current_speed / 255 * 100)}%)")
    app._speed_label.setStyleSheet("color: #f1f5f9; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
    app._speed_label.setFixedWidth(70)
    speed_layout.addWidget(app._speed_label)

    speed_group.setLayout(speed_layout)
    layout.addWidget(speed_group)

    brake_group = QGroupBox("Auto-Brake")
    brake_group.setStyleSheet("background-color: #171f33; border: 1px solid #243147; border-radius: 6px; padding: 6px;")
    brake_layout = QHBoxLayout()
    brake_layout.setContentsMargins(8, 4, 8, 4)
    brake_layout.setSpacing(8)

    app._brake_toggle = QPushButton("ON")
    app._brake_toggle.setCheckable(True)
    app._brake_toggle.setChecked(True)
    app._brake_toggle.setFixedWidth(50)
    app._brake_toggle.setFixedHeight(28)
    app._brake_toggle.setStyleSheet("""
        QPushButton {
            background-color: #10b981;
            color: white;
            font-weight: 600;
            font-size: 11px;
            border-radius: 4px;
            border: none;
        }
        QPushButton:!checked {
            background-color: #64748b;
        }
    """)
    app._brake_toggle.clicked.connect(lambda: _toggle_brake(app))
    brake_layout.addWidget(app._brake_toggle)

    brake_label = QLabel("30cm")
    brake_label.setStyleSheet("color: #94a3b8; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
    brake_layout.addWidget(brake_label)

    brake_group.setLayout(brake_layout)
    layout.addWidget(brake_group)

    gimbal_group = QGroupBox("Gimbal")
    gimbal_group.setStyleSheet("background-color: #171f33; border: 1px solid #243147; border-radius: 6px; padding: 6px;")
    gimbal_layout = QHBoxLayout()
    gimbal_layout.setContentsMargins(8, 4, 8, 4)
    gimbal_layout.setSpacing(6)

    pan_label = QLabel("Pan")
    pan_label.setStyleSheet("color: #94a3b8; font-size: 10px;")
    gimbal_layout.addWidget(pan_label)

    app._gimbal_pan_label = QLabel(f"{app._gimbal_pan}°")
    app._gimbal_pan_label.setStyleSheet("color: #f1f5f9; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
    gimbal_layout.addWidget(app._gimbal_pan_label)

    tilt_label = QLabel("Tilt")
    tilt_label.setStyleSheet("color: #94a3b8; font-size: 10px;")
    gimbal_layout.addWidget(tilt_label)

    app._gimbal_tilt_label = QLabel(f"{app._gimbal_tilt}°")
    app._gimbal_tilt_label.setStyleSheet("color: #f1f5f9; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
    gimbal_layout.addWidget(app._gimbal_tilt_label)

    center_btn = QPushButton("Center")
    center_btn.setFixedHeight(28)
    center_btn.setStyleSheet("""
        QPushButton {
            background-color: #3b82f6;
            color: white;
            font-weight: 600;
            font-size: 11px;
            border-radius: 4px;
            border: none;
            padding: 4px 12px;
        }
        QPushButton:hover {
            background-color: #2563eb;
        }
    """)
    center_btn.clicked.connect(app._center_gimbal)
    gimbal_layout.addWidget(center_btn)

    gimbal_group.setLayout(gimbal_layout)
    layout.addWidget(gimbal_group)

    cloud_group = QGroupBox("Cloud")
    cloud_layout = QVBoxLayout()

    app._cloud_send_btn = QPushButton("POST")
    app._cloud_send_btn.setFixedHeight(40)
    app._cloud_send_btn.setStyleSheet("""
        QPushButton {
            background-color: #8b5cf6;
            color: white;
            font-weight: bold;
            font-size: 13px;
            border-radius: 4px;
            padding: 4px 16px;
        }
        QPushButton:hover {
            background-color: #7c3aed;
        }
    """)
    app._cloud_send_btn.clicked.connect(app._manual_send_to_cloud)
    cloud_layout.addWidget(app._cloud_send_btn)

    cloud_label = QLabel("Send telemetry")
    cloud_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
    cloud_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    cloud_layout.addWidget(cloud_label)

    cloud_group.setLayout(cloud_layout)
    layout.addWidget(cloud_group, 1)

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
    stop_btn.clicked.connect(app._emergency_stop)
    stop_layout.addWidget(stop_btn)

    stop_group.setLayout(stop_layout)
    layout.addWidget(stop_group, 1)

    widget.setLayout(layout)
    return widget


def _on_speed_change(app, value):
    app._current_speed = value
    percent = int(value / 255 * 100)
    app._speed_label.setText(f"{value} ({percent}%)")


def _toggle_brake(app):
    checked = app._brake_toggle.isChecked()
    app._brake_toggle.setText("ON" if checked else "OFF")
    app._add_log("SAFETY", f"Auto-brake {'enabled' if checked else 'disabled'}")
