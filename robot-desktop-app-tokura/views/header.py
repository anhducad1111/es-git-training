from PyQt6.QtWidgets import (
    QLabel, QLineEdit, QHBoxLayout, QPushButton, QWidget
)
from config import save_config, get_local_ip


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
    app._rover_ip_input.returnPressed.connect(lambda: _on_connect_clicked(app))
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
    app._cam_ip_input.returnPressed.connect(lambda: _on_connect_clicked(app))
    layout.addWidget(app._cam_ip_input)

    connect_btn = QPushButton("CONNECT")
    connect_btn.setFixedHeight(26)
    connect_btn.setStyleSheet("""
        QPushButton {
            background-color: rgba(6, 182, 212, 0.15);
            border: 1px solid rgba(6, 182, 212, 0.4);
            color: #06b6d4;
            font-weight: 600;
            font-size: 10px;
            padding: 4px 10px;
            letter-spacing: 1px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: rgba(6, 182, 212, 0.3);
        }
    """)
    connect_btn.clicked.connect(lambda: _on_connect_clicked(app))
    layout.addWidget(connect_btn)

    separator2 = QLabel()
    separator2.setFixedWidth(1)
    separator2.setFixedHeight(20)
    separator2.setStyleSheet("background-color: #1e293b;")
    layout.addWidget(separator2)

    web_label = QLabel("WEB")
    web_label.setStyleSheet("color: #475569; font-size: 10px; letter-spacing: 1px;")
    layout.addWidget(web_label)

    web_port = app._config.get("remote_control_port", 8765)
    app._web_ip_input = QLineEdit(f"{get_local_ip()}:{web_port}")
    app._web_ip_input.setReadOnly(True)
    app._web_ip_input.setFixedWidth(140)
    app._web_ip_input.setStyleSheet("""
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 4px;
        padding: 4px 8px;
        color: #06b6d4;
        font-size: 11px;
        font-family: 'JetBrains Mono', monospace;
    """)
    layout.addWidget(app._web_ip_input)

    separator3 = QLabel()
    separator3.setFixedWidth(1)
    separator3.setFixedHeight(20)
    separator3.setStyleSheet("background-color: #1e293b;")
    layout.addWidget(separator3)

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

    separator_dist = QLabel()
    separator_dist.setFixedWidth(1)
    separator_dist.setFixedHeight(20)
    separator_dist.setStyleSheet("background-color: #1e293b;")
    layout.addWidget(separator_dist)

    dist_label = QLabel("DIST")
    dist_label.setStyleSheet("color: #475569; font-size: 10px; letter-spacing: 1px;")
    layout.addWidget(dist_label)

    app._distance_display = QLabel("-- cm")
    app._distance_display.setFixedWidth(70)
    app._distance_display.setStyleSheet("""
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 4px;
        padding: 4px 8px;
        color: #10b981;
        font-size: 11px;
        font-family: 'JetBrains Mono', monospace;
    """)
    layout.addWidget(app._distance_display)

    separator_angle = QLabel()
    separator_angle.setFixedWidth(1)
    separator_angle.setFixedHeight(20)
    separator_angle.setStyleSheet("background-color: #1e293b;")
    layout.addWidget(separator_angle)

    angle_label = QLabel("TARGET")
    angle_label.setStyleSheet("color: #475569; font-size: 10px; letter-spacing: 1px;")
    layout.addWidget(angle_label)

    app._target_angle_display = QLabel("0°")
    app._target_angle_display.setFixedWidth(60)
    app._target_angle_display.setStyleSheet("""
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 4px;
        padding: 4px 8px;
        color: #a78bfa;
        font-size: 11px;
        font-family: 'JetBrains Mono', monospace;
    """)
    layout.addWidget(app._target_angle_display)

    header.setLayout(layout)
    return header


def _on_connect_clicked(app):
    app._config['car_ip'] = app._rover_ip_input.text().strip()
    app._config['cam_ip'] = app._cam_ip_input.text().strip()
    save_config(app._config)
    app._add_log("CONFIG", f"IPs updated: Rover={app._config['car_ip']}, Cam={app._config['cam_ip']}")

    app._conn_mgr.update_esp32_ips()
    app._conn_mgr.reconnect_rover()

    resolution = "640x480"
    if hasattr(app, '_resolution_combo'):
        resolution = app._resolution_combo.currentText().split(" ")[0]
    app._conn_mgr.reconnect_camera(resolution)

    app.setFocus()
