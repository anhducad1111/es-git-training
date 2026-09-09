from PyQt6.QtWidgets import (
    QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QWidget
)
from widgets.sensor_card import SensorCard


def create_sidebar(app):
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

    app._link_label = QLabel("Link: 98% (Optimal)")
    app._link_label.setStyleSheet("color: #10b981; font-size: 11px;")
    header_layout.addWidget(app._link_label)

    estop_btn = QPushButton("E-STOP")
    estop_btn.setFixedWidth(60)
    estop_btn.setStyleSheet("background-color: #ef4444; font-weight: bold; padding: 4px 8px;")
    estop_btn.clicked.connect(app._emergency_stop)
    header_layout.addWidget(estop_btn)

    layout.addLayout(header_layout)

    app._temp_card = SensorCard("Chassis Core Temp", "°C", "🌡", 0, 60)
    layout.addWidget(app._temp_card)

    app._humidity_card = SensorCard("Ambient Humidity", "%", "💧", 0, 100)
    layout.addWidget(app._humidity_card)

    app._gas_card = SensorCard("Air Purity Metric", "PPM", "🌫", 0, 1000)
    layout.addWidget(app._gas_card)

    app._distance_card = SensorCard("Obstacle Distance", "cm", "📏", 0, 200)
    layout.addWidget(app._distance_card)

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
    app._battery_label = QLabel("12.4V")
    app._battery_label.setStyleSheet("color: #f1f5f9; font-size: 11px; font-weight: bold;")
    battery_row.addWidget(app._battery_label)
    health_layout.addLayout(battery_row)

    health_group.setLayout(health_layout)
    layout.addWidget(health_group)

    snapshot_btn = QPushButton("Take Snapshot")
    snapshot_btn.setStyleSheet("background-color: #1d4ed8;")
    snapshot_btn.clicked.connect(app._take_snapshot)
    layout.addWidget(snapshot_btn)

    diag_btn = QPushButton("System Diagnostics")
    diag_btn.setStyleSheet("background-color: #475569;")
    diag_btn.clicked.connect(app._toggle_view)
    layout.addWidget(diag_btn)

    config_btn = QPushButton("Device Configuration")
    config_btn.setStyleSheet("background-color: #475569;")
    layout.addWidget(config_btn)

    follow_btn = QPushButton("Follow Mode")
    follow_btn.setStyleSheet("background-color: #7c3aed;")
    follow_btn.clicked.connect(app._toggle_follow_mode)
    layout.addWidget(follow_btn)

    layout.addStretch()

    sidebar.setLayout(layout)
    return sidebar
