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
    main_layout.setContentsMargins(12, 12, 12, 12)
    main_layout.setSpacing(8)

    header_layout = QHBoxLayout()
    header_layout.setContentsMargins(4, 4, 4, 8)
    
    header_col = QVBoxLayout()
    header_label = QLabel("TELEMETRY SENSORS")
    header_label.setStyleSheet("""
        color: #f1f5f9;
        font-weight: 700;
        font-size: 11px;
        letter-spacing: 1px;
    """)
    header_col.addWidget(header_label)
    
    app._link_label = QLabel("Link: 98% (Optimal)")
    app._link_label.setStyleSheet("""
        color: #10b981;
        font-size: 10px;
        font-weight: 500;
    """)
    header_col.addWidget(app._link_label)
    header_layout.addLayout(header_col)
    
    header_layout.addStretch()

    estop_btn = QPushButton("E-STOP")
    estop_btn.setFixedHeight(28)
    estop_btn.setStyleSheet("""
        background-color: rgba(239, 68, 68, 0.15);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.3);
        font-weight: 700;
        font-size: 10px;
        padding: 4px 12px;
        border-radius: 4px;
    """)
    estop_btn.clicked.connect(app._emergency_stop)
    header_layout.addWidget(estop_btn)

    main_layout.addLayout(header_layout)

    app._sidebar_stack = QStackedWidget()

    sensors_page = QWidget()
    sensors_layout = QVBoxLayout()
    sensors_layout.setContentsMargins(0, 0, 0, 0)
    sensors_layout.setSpacing(8)

    compact_sensors = QWidget()
    compact_sensors.setFixedHeight(40)
    compact_sensors.setStyleSheet("""
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 6px;
    """)
    compact_layout = QHBoxLayout()
    compact_layout.setContentsMargins(8, 4, 8, 4)
    compact_layout.setSpacing(12)

    app._temp_label = QLabel("28.5°C")
    app._temp_label.setStyleSheet("color: #10b981; font-size: 11px; font-family: 'JetBrains Mono', monospace; font-weight: 600;")
    compact_layout.addWidget(app._temp_label)

    app._humidity_label = QLabel("47.0%")
    app._humidity_label.setStyleSheet("color: #3b82f6; font-size: 11px; font-family: 'JetBrains Mono', monospace; font-weight: 600;")
    compact_layout.addWidget(app._humidity_label)

    app._gas_label = QLabel("150 PPM")
    app._gas_label.setStyleSheet("color: #f59e0b; font-size: 11px; font-family: 'JetBrains Mono', monospace; font-weight: 600;")
    compact_layout.addWidget(app._gas_label)

    compact_sensors.setLayout(compact_layout)
    sensors_layout.addWidget(compact_sensors)

    app._distance_card = SensorCard("Distance", "cm", "D", 0, 200)
    sensors_layout.addWidget(app._distance_card)

    health_group = QGroupBox("SUBSYSTEM HEALTH")
    health_group.setStyleSheet("""
        QGroupBox {
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 10px;
            margin-top: 8px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
            color: #94a3b8;
            font-size: 9px;
            font-weight: 600;
            letter-spacing: 1px;
        }
    """)
    health_layout = QVBoxLayout()
    health_layout.setSpacing(6)
    health_layout.setContentsMargins(8, 12, 8, 8)

    for name in ["ESP32 Main MCU", "Motor Drivers", "Pan/Tilt Servos"]:
        row = QHBoxLayout()
        label = QLabel(name)
        label.setStyleSheet("color: #94a3b8; font-size: 10px;")
        row.addWidget(label)
        row.addStretch()
        status = QLabel("OK")
        status.setStyleSheet("""
            color: #10b981;
            font-size: 10px;
            font-weight: bold;
            background-color: rgba(16, 185, 129, 0.15);
            padding: 2px 8px;
            border-radius: 4px;
        """)
        row.addWidget(status)
        health_layout.addLayout(row)

    battery_row = QHBoxLayout()
    battery_label = QLabel("Battery Level")
    battery_label.setStyleSheet("color: #94a3b8; font-size: 10px;")
    battery_row.addWidget(battery_label)
    battery_row.addStretch()
    app._battery_label = QLabel("12.4V (88%)")
    app._battery_label.setStyleSheet("color: #f1f5f9; font-size: 10px; font-weight: bold; font-family: 'JetBrains Mono', monospace;")
    battery_row.addWidget(app._battery_label)
    health_layout.addLayout(battery_row)

    health_group.setLayout(health_layout)
    sensors_layout.addWidget(health_group)

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

    hf_group = QGroupBox("HF TOKEN")
    hf_group.setStyleSheet("""
        background-color: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 6px;
        padding: 8px;
    """)
    hf_layout = QVBoxLayout()
    hf_layout.setContentsMargins(8, 4, 8, 4)
    hf_layout.setSpacing(4)

    from PyQt6.QtWidgets import QLineEdit
    app._hf_token_input = QLineEdit()
    app._hf_token_input.setPlaceholderText("Enter HF token...")
    app._hf_token_input.setEchoMode(QLineEdit.EchoMode.Password)
    app._hf_token_input.setText(app._config.get("hf_token", ""))
    app._hf_token_input.setStyleSheet("""
        background-color: #1e293b;
        border: 1px solid #334155;
        color: #e2e8f0;
        font-size: 9px;
        padding: 4px 8px;
        border-radius: 4px;
    """)
    app._hf_token_input.returnPressed.connect(lambda: _save_hf_token(app))
    hf_layout.addWidget(app._hf_token_input)

    hf_group.setLayout(hf_layout)
    settings_layout.addWidget(hf_group)

    cloud_group = QGroupBox("CLOUD")
    cloud_group.setStyleSheet("""
        background-color: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 6px;
        padding: 8px;
    """)
    cloud_layout = QVBoxLayout()
    cloud_layout.setContentsMargins(8, 4, 8, 4)
    cloud_layout.setSpacing(6)

    cloud_btn_row = QHBoxLayout()
    cloud_btn_row.setSpacing(6)

    app._cloud_send_btn = QPushButton("SEND")
    app._cloud_send_btn.setFixedHeight(26)
    app._cloud_send_btn.setStyleSheet("""
        QPushButton {
            background-color: #7c3aed;
            color: white;
            font-weight: 600;
            font-size: 10px;
            border: none;
            padding: 4px 12px;
            letter-spacing: 1px;
        }
        QPushButton:hover {
            background-color: #6d28d9;
        }
    """)
    app._cloud_send_btn.clicked.connect(app._manual_send_to_cloud)
    cloud_btn_row.addWidget(app._cloud_send_btn)

    app._toggle_view_btn = QPushButton("DATA")
    app._toggle_view_btn.setFixedHeight(26)
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
    cloud_btn_row.addWidget(app._toggle_view_btn)

    cloud_layout.addLayout(cloud_btn_row)
    cloud_group.setLayout(cloud_layout)
    settings_layout.addWidget(cloud_group)

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


def _save_hf_token(app):
    from config import save_config
    token = app._hf_token_input.text().strip()
    app._config["hf_token"] = token
    save_config(app._config)
    app._add_log("CONFIG", f"HF token saved ({len(token)} chars)")


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
