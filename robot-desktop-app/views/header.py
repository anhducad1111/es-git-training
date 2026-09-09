from PyQt6.QtWidgets import (
    QLabel, QLineEdit, QHBoxLayout, QWidget
)
from config import save_config


def create_header(app):
    header = QWidget()
    header.setFixedHeight(52)
    header.setStyleSheet("""
        background-color: #0f172a;
        border-bottom: 1px solid #1e293b;
    """)
    layout = QHBoxLayout()
    layout.setContentsMargins(20, 0, 20, 0)

    title_label = QLabel("ROVER COCKPIT")
    title_label.setStyleSheet("""
        color: #06b6d4;
        font-weight: 700;
        font-size: 14px;
        letter-spacing: 2px;
    """)
    layout.addWidget(title_label)

    version_label = QLabel("v2.4")
    version_label.setStyleSheet("""
        color: #475569;
        font-size: 9px;
        background-color: #1e293b;
        padding: 2px 6px;
        border-radius: 3px;
        border: 1px solid #334155;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: 1px;
    """)
    layout.addWidget(version_label)

    layout.addStretch()

    rover_label = QLabel("ROVER")
    rover_label.setStyleSheet("color: #475569; font-size: 10px; letter-spacing: 1px;")
    layout.addWidget(rover_label)

    app._rover_ip_input = QLineEdit(app._config['car_ip'])
    app._rover_ip_input.setFixedWidth(110)
    app._rover_ip_input.setStyleSheet("""
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 4px;
        padding: 4px 8px;
        color: #06b6d4;
        font-size: 11px;
        font-family: 'JetBrains Mono', monospace;
    """)
    app._rover_ip_input.returnPressed.connect(lambda: _on_ip_changed(app))
    layout.addWidget(app._rover_ip_input)

    separator1 = QLabel()
    separator1.setFixedWidth(1)
    separator1.setFixedHeight(20)
    separator1.setStyleSheet("background-color: #1e293b;")
    layout.addWidget(separator1)

    cam_label = QLabel("CAM")
    cam_label.setStyleSheet("color: #475569; font-size: 10px; letter-spacing: 1px;")
    layout.addWidget(cam_label)

    app._cam_ip_input = QLineEdit(app._config['cam_ip'])
    app._cam_ip_input.setFixedWidth(110)
    app._cam_ip_input.setStyleSheet("""
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 4px;
        padding: 4px 8px;
        color: #06b6d4;
        font-size: 11px;
        font-family: 'JetBrains Mono', monospace;
    """)
    app._cam_ip_input.returnPressed.connect(lambda: _on_ip_changed(app))
    layout.addWidget(app._cam_ip_input)

    separator2 = QLabel()
    separator2.setFixedWidth(1)
    separator2.setFixedHeight(20)
    separator2.setStyleSheet("background-color: #1e293b;")
    layout.addWidget(separator2)

    app._rover_status = QLabel("OFFLINE")
    app._rover_status.setStyleSheet("""
        color: #ef4444;
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 1px;
    """)
    layout.addWidget(app._rover_status)

    app._cam_status = QLabel("OFFLINE")
    app._cam_status.setStyleSheet("""
        color: #ef4444;
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 1px;
        margin-left: 12px;
    """)
    layout.addWidget(app._cam_status)

    header.setLayout(layout)
    return header


def _on_ip_changed(app):
    app._config['car_ip'] = app._rover_ip_input.text()
    app._config['cam_ip'] = app._cam_ip_input.text()
    save_config(app._config)
    app._add_log("CONFIG", f"IPs updated: Rover={app._config['car_ip']}, Cam={app._config['cam_ip']}")
