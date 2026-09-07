from PyQt6.QtWidgets import (
    QLabel, QLineEdit, QHBoxLayout, QWidget
)
from config import save_config


def create_header(app):
    header = QWidget()
    header.setFixedHeight(48)
    header.setStyleSheet("background-color: #131b2e; border-bottom: 1px solid #243147;")
    layout = QHBoxLayout()
    layout.setContentsMargins(16, 0, 16, 0)

    title_label = QLabel("Rover Teleop Cockpit")
    title_label.setStyleSheet("color: #f1f5f9; font-weight: 600; font-size: 13px;")
    layout.addWidget(title_label)

    version_label = QLabel("v2.4.0")
    version_label.setStyleSheet("color: #94a3b8; font-size: 10px; background-color: #1e293b; padding: 2px 6px; border-radius: 3px; border: 1px solid #334155; font-family: 'JetBrains Mono', monospace;")
    layout.addWidget(version_label)

    layout.addStretch()

    rover_label = QLabel("Rover IP:")
    rover_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
    layout.addWidget(rover_label)

    app._rover_ip_input = QLineEdit(app._config['car_ip'])
    app._rover_ip_input.setFixedWidth(120)
    app._rover_ip_input.setStyleSheet("background-color: #0f172a; border: 1px solid #334155; border-radius: 4px; padding: 3px 6px; color: #f1f5f9; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
    app._rover_ip_input.returnPressed.connect(lambda: _on_ip_changed(app))
    layout.addWidget(app._rover_ip_input)

    separator1 = QLabel()
    separator1.setFixedWidth(1)
    separator1.setFixedHeight(16)
    separator1.setStyleSheet("background-color: #243147;")
    layout.addWidget(separator1)

    cam_label = QLabel("Camera IP:")
    cam_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
    layout.addWidget(cam_label)

    app._cam_ip_input = QLineEdit(app._config['cam_ip'])
    app._cam_ip_input.setFixedWidth(120)
    app._cam_ip_input.setStyleSheet("background-color: #0f172a; border: 1px solid #334155; border-radius: 4px; padding: 3px 6px; color: #f1f5f9; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
    app._cam_ip_input.returnPressed.connect(lambda: _on_ip_changed(app))
    layout.addWidget(app._cam_ip_input)

    separator2 = QLabel()
    separator2.setFixedWidth(1)
    separator2.setFixedHeight(16)
    separator2.setStyleSheet("background-color: #243147;")
    layout.addWidget(separator2)

    app._rover_status = QLabel("Rover: Offline")
    app._rover_status.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: 500;")
    layout.addWidget(app._rover_status)

    app._cam_status = QLabel("Cam: Offline")
    app._cam_status.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: 500; margin-left: 8px;")
    layout.addWidget(app._cam_status)

    header.setLayout(layout)
    return header


def _on_ip_changed(app):
    app._config['car_ip'] = app._rover_ip_input.text()
    app._config['cam_ip'] = app._cam_ip_input.text()
    save_config(app._config)
    app._add_log("CONFIG", f"IPs updated: Rover={app._config['car_ip']}, Cam={app._config['cam_ip']}")
