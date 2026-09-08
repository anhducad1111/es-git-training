from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QCheckBox, QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QSlider, QStackedWidget, QVBoxLayout, QWidget
)
from widgets.sensor_card import SensorCard


def create_sidebar(app):
    sidebar = QWidget()
    sidebar.setFixedWidth(320)
    sidebar.setStyleSheet("""
        background-color: #0f172a;
        border-left: 1px solid #1e293b;
    """)
    main_layout = QVBoxLayout()
    main_layout.setContentsMargins(16, 16, 16, 16)
    main_layout.setSpacing(10)

    header_layout = QHBoxLayout()
    header_label = QLabel("SENSORS")
    header_label.setStyleSheet("""
        color: #06b6d4;
        font-weight: 700;
        font-size: 11px;
        letter-spacing: 2px;
    """)
    header_layout.addWidget(header_label)
    header_layout.addStretch()

    app._link_label = QLabel("98%")
    app._link_label.setStyleSheet("""
        color: #10b981;
        font-size: 11px;
        font-family: 'JetBrains Mono', monospace;
    """)
    header_layout.addWidget(app._link_label)

    estop_btn = QPushButton("STOP")
    estop_btn.setFixedWidth(50)
    estop_btn.setStyleSheet("""
        background-color: #ef4444;
        color: white;
        font-weight: 700;
        font-size: 10px;
        padding: 4px 8px;
        border: none;
    """)
    estop_btn.clicked.connect(app._emergency_stop)
    header_layout.addWidget(estop_btn)

    main_layout.addLayout(header_layout)

    app._sidebar_stack = QStackedWidget()

    sensors_page = QWidget()
    sensors_layout = QVBoxLayout()
    sensors_layout.setContentsMargins(0, 0, 0, 0)
    sensors_layout.setSpacing(10)

    app._temp_card = SensorCard("Temp", "°C", "T", 0, 60)
    sensors_layout.addWidget(app._temp_card)

    app._humidity_card = SensorCard("Humidity", "%", "H", 0, 100)
    sensors_layout.addWidget(app._humidity_card)

    app._gas_card = SensorCard("Gas", "PPM", "G", 0, 1000)
    sensors_layout.addWidget(app._gas_card)

    app._distance_card = SensorCard("Distance", "cm", "D", 0, 200)
    sensors_layout.addWidget(app._distance_card)

    health_group = QGroupBox("HEALTH")
    health_layout = QVBoxLayout()
    health_layout.setSpacing(6)

    for name in ["MCU", "Motors", "Servos"]:
        row = QHBoxLayout()
        label = QLabel(name)
        label.setStyleSheet("color: #64748b; font-size: 10px;")
        row.addWidget(label)
        row.addStretch()
        status = QLabel("OK")
        status.setStyleSheet("color: #10b981; font-size: 10px; font-weight: bold;")
        row.addWidget(status)
        health_layout.addLayout(row)

    battery_row = QHBoxLayout()
    battery_label = QLabel("Battery")
    battery_label.setStyleSheet("color: #64748b; font-size: 10px;")
    battery_row.addWidget(battery_label)
    battery_row.addStretch()
    app._battery_label = QLabel("12.4V")
    app._battery_label.setStyleSheet("color: #e2e8f0; font-size: 10px; font-weight: bold; font-family: 'JetBrains Mono', monospace;")
    battery_row.addWidget(app._battery_label)
    health_layout.addLayout(battery_row)

    health_group.setLayout(health_layout)
    sensors_layout.addWidget(health_group)

    snapshot_btn = QPushButton("📷  Take Snapshot")
    snapshot_btn.setStyleSheet("""
        QPushButton {
            background-color: rgba(6, 182, 212, 0.1);
            border: 1px solid rgba(6, 182, 212, 0.3);
            color: #06b6d4;
            font-weight: 600;
            font-size: 11px;
            padding: 8px 12px;
            border-radius: 6px;
        }
        QPushButton:hover {
            background-color: rgba(6, 182, 212, 0.2);
        }
        QPushButton:pressed {
            background-color: rgba(6, 182, 212, 0.3);
        }
    """)
    snapshot_btn.clicked.connect(app._take_snapshot)
    sensors_layout.addWidget(snapshot_btn)

    app._super_res_check = QCheckBox("Auto Super-Res on Snapshot")
    app._super_res_check.setStyleSheet("color: #94a3b8; font-size: 10px;")
    sensors_layout.addWidget(app._super_res_check)

    sensors_layout.addStretch()
    sensors_page.setLayout(sensors_layout)
    app._sidebar_stack.addWidget(sensors_page)

    settings_page = QWidget()
    settings_layout = QVBoxLayout()
    settings_layout.setContentsMargins(0, 0, 0, 0)
    settings_layout.setSpacing(10)

    pid_group = QGroupBox("PID STRAIGHT")
    pid_group.setStyleSheet("""
        background-color: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 6px;
        padding: 8px;
    """)
    pid_layout = QVBoxLayout()
    pid_layout.setContentsMargins(8, 4, 8, 4)
    pid_layout.setSpacing(4)

    app._pid_toggle = QPushButton("OFF")
    app._pid_toggle.setCheckable(True)
    app._pid_toggle.setFixedHeight(22)
    app._pid_toggle.setStyleSheet("""
        QPushButton {
            background-color: #475569;
            color: white;
            font-weight: 600;
            font-size: 9px;
            border: none;
            border-radius: 10px;
        }
        QPushButton:checked {
            background-color: #10b981;
        }
    """)
    app._pid_toggle.clicked.connect(lambda: _toggle_pid(app))
    pid_layout.addWidget(app._pid_toggle)

    kp_row = QHBoxLayout()
    kp_label = QLabel("Kp")
    kp_label.setStyleSheet("color: #94a3b8; font-size: 9px;")
    kp_row.addWidget(kp_label)
    app._kp_slider = QSlider(Qt.Orientation.Horizontal)
    app._kp_slider.setRange(0, 100)
    app._kp_slider.setValue(20)
    app._kp_slider.valueChanged.connect(lambda v: _on_pid_change(app))
    kp_row.addWidget(app._kp_slider)
    app._kp_label = QLabel("20")
    app._kp_label.setStyleSheet("color: #06b6d4; font-size: 9px; font-family: 'JetBrains Mono', monospace;")
    app._kp_label.setFixedWidth(25)
    kp_row.addWidget(app._kp_label)
    pid_layout.addLayout(kp_row)

    ki_row = QHBoxLayout()
    ki_label = QLabel("Ki")
    ki_label.setStyleSheet("color: #94a3b8; font-size: 9px;")
    ki_row.addWidget(ki_label)
    app._ki_slider = QSlider(Qt.Orientation.Horizontal)
    app._ki_slider.setRange(0, 100)
    app._ki_slider.setValue(5)
    app._ki_slider.valueChanged.connect(lambda v: _on_pid_change(app))
    ki_row.addWidget(app._ki_slider)
    app._ki_label = QLabel("5")
    app._ki_label.setStyleSheet("color: #06b6d4; font-size: 9px; font-family: 'JetBrains Mono', monospace;")
    app._ki_label.setFixedWidth(25)
    ki_row.addWidget(app._ki_label)
    pid_layout.addLayout(ki_row)

    kd_row = QHBoxLayout()
    kd_label = QLabel("Kd")
    kd_label.setStyleSheet("color: #94a3b8; font-size: 9px;")
    kd_row.addWidget(kd_label)
    app._kd_slider = QSlider(Qt.Orientation.Horizontal)
    app._kd_slider.setRange(0, 100)
    app._kd_slider.setValue(10)
    app._kd_slider.valueChanged.connect(lambda v: _on_pid_change(app))
    kd_row.addWidget(app._kd_slider)
    app._kd_label = QLabel("10")
    app._kd_label.setStyleSheet("color: #06b6d4; font-size: 9px; font-family: 'JetBrains Mono', monospace;")
    app._kd_label.setFixedWidth(25)
    kd_row.addWidget(app._kd_label)
    pid_layout.addLayout(kd_row)

    pid_group.setLayout(pid_layout)
    settings_layout.addWidget(pid_group)

    cam_group = QGroupBox("CAMERA")
    cam_group.setStyleSheet("""
        background-color: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 6px;
        padding: 8px;
    """)
    cam_layout = QVBoxLayout()
    cam_layout.setContentsMargins(8, 4, 8, 4)
    cam_layout.setSpacing(6)

    led_row = QHBoxLayout()
    led_label = QLabel("LED")
    led_label.setStyleSheet("color: #64748b; font-size: 9px; letter-spacing: 1px;")
    led_row.addWidget(led_label)

    app._led_slider = QSlider(Qt.Orientation.Horizontal)
    app._led_slider.setRange(0, 255)
    app._led_slider.setValue(0)
    app._led_slider.setFixedWidth(100)
    app._led_slider.valueChanged.connect(lambda v: _on_led_change(app, v))
    led_row.addWidget(app._led_slider)

    app._led_label = QLabel("0")
    app._led_label.setStyleSheet("color: #e2e8f0; font-size: 9px; font-family: 'JetBrains Mono', monospace;")
    app._led_label.setFixedWidth(25)
    led_row.addWidget(app._led_label)

    app._led_flash_btn = QPushButton("FLASH")
    app._led_flash_btn.setCheckable(True)
    app._led_flash_btn.setFixedWidth(45)
    app._led_flash_btn.setFixedHeight(18)
    app._led_flash_btn.setStyleSheet("""
        QPushButton {
            background-color: #475569;
            color: white;
            font-weight: 600;
            font-size: 8px;
            border: none;
            border-radius: 9px;
        }
        QPushButton:checked {
            background-color: #f59e0b;
        }
    """)
    app._led_flash_btn.clicked.connect(lambda: _toggle_led_flash(app))
    led_row.addWidget(app._led_flash_btn)

    cam_layout.addLayout(led_row)

    quality_row = QHBoxLayout()
    quality_label = QLabel("Q")
    quality_label.setStyleSheet("color: #64748b; font-size: 9px; letter-spacing: 1px;")
    quality_row.addWidget(quality_label)

    app._quality_slider = QSlider(Qt.Orientation.Horizontal)
    app._quality_slider.setRange(0, 63)
    app._quality_slider.setValue(14)
    app._quality_slider.setFixedWidth(100)
    app._quality_slider.valueChanged.connect(lambda v: _on_quality_change(app, v))
    quality_row.addWidget(app._quality_slider)

    app._quality_label = QLabel("14")
    app._quality_label.setStyleSheet("color: #e2e8f0; font-size: 9px; font-family: 'JetBrains Mono', monospace;")
    app._quality_label.setFixedWidth(25)
    quality_row.addWidget(app._quality_label)

    cam_layout.addLayout(quality_row)

    cam_group.setLayout(cam_layout)
    settings_layout.addWidget(cam_group)

    settings_layout.addStretch()
    settings_page.setLayout(settings_layout)
    app._sidebar_stack.addWidget(settings_page)

    main_layout.addWidget(app._sidebar_stack, 1)

    settings_btn = QPushButton("SETTINGS")
    settings_btn.setCheckable(True)
    settings_btn.setStyleSheet("""
        QPushButton {
            background-color: #1e293b;
            border: 1px solid #334155;
            color: #64748b;
            font-weight: 600;
            font-size: 10px;
            letter-spacing: 1px;
        }
        QPushButton:checked {
            background-color: #06b6d4;
            color: #0a0e1a;
        }
    """)
    settings_btn.clicked.connect(lambda: _toggle_settings(app, settings_btn))
    main_layout.addWidget(settings_btn)

    diag_btn = QPushButton("DIAGNOSTICS")
    diag_btn.setStyleSheet("""
        background-color: #1e293b;
        border: 1px solid #334155;
        color: #64748b;
        font-weight: 600;
        font-size: 10px;
        letter-spacing: 1px;
    """)
    diag_btn.clicked.connect(app._toggle_view)
    main_layout.addWidget(diag_btn)

    follow_btn = QPushButton("FOLLOW MODE")
    follow_btn.setStyleSheet("""
        background-color: #1e293b;
        border: 1px solid #7c3aed;
        color: #7c3aed;
        font-weight: 600;
        font-size: 10px;
        letter-spacing: 1px;
    """)
    follow_btn.clicked.connect(app._toggle_follow_mode)
    main_layout.addWidget(follow_btn)

    sidebar.setLayout(main_layout)
    return sidebar


def _toggle_settings(app, btn):
    checked = btn.isChecked()
    if checked:
        app._sidebar_stack.setCurrentIndex(1)
    else:
        app._sidebar_stack.setCurrentIndex(0)


def _toggle_brake(app):
    checked = app._brake_toggle.isChecked()
    app._brake_toggle.setText("ON" if checked else "OFF")
    if hasattr(app, '_esp32_api'):
        app._esp32_api.set_brake(checked)
    app._add_log("SAFETY", f"Auto-brake {'enabled' if checked else 'disabled'}")


def _on_led_change(app, value):
    app._led_label.setText(str(value))
    if hasattr(app, '_esp32_api'):
        app._esp32_api.set_led(value)


def _on_quality_change(app, value):
    app._quality_label.setText(str(value))
    if hasattr(app, '_esp32_api'):
        app._esp32_api.set_quality(value)


def _toggle_pid(app):
    checked = app._pid_toggle.isChecked()
    app._pid_toggle.setText("ON" if checked else "OFF")
    if hasattr(app, '_esp32_api'):
        app._esp32_api.set_pid(enabled=checked)
    app._add_log("PID", f"PID straight {'enabled' if checked else 'disabled'}")


def _on_pid_change(app):
    kp = app._kp_slider.value()
    ki = app._ki_slider.value()
    kd = app._kd_slider.value()
    app._kp_label.setText(str(kp))
    app._ki_label.setText(str(ki))
    app._kd_label.setText(str(kd))
    if hasattr(app, '_esp32_api'):
        app._esp32_api.set_pid(kp=kp / 100.0, ki=ki / 100.0, kd=kd / 100.0)


def _toggle_led_flash(app):
    checked = app._led_flash_btn.isChecked()
    if checked:
        app._led_flash_state = False
        app._led_flash_timer = QTimer()
        app._led_flash_timer.timeout.connect(lambda: _flash_led(app))
        app._led_flash_timer.start(200)
        app._add_log("LED", "Flash mode ON")
    else:
        if hasattr(app, '_led_flash_timer'):
            app._led_flash_timer.stop()
        if hasattr(app, '_esp32_api'):
            app._esp32_api.set_led(0)
        app._add_log("LED", "Flash mode OFF")


def _flash_led(app):
    app._led_flash_state = not getattr(app, '_led_flash_state', False)
    if hasattr(app, '_esp32_api'):
        app._esp32_api.set_led(255 if app._led_flash_state else 0)
