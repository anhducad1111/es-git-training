from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QCheckBox, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSlider, QStackedWidget, QVBoxLayout, QWidget
)
from widgets.sensor_card import SensorCard

# Gimbal display offset: 85, 70 is the center position displayed as 0, 0
_GIMBAL_PAN_OFFSET = 85
_GIMBAL_TILT_OFFSET = 70

def _actual_to_display_pan(actual):
    """Convert actual pan angle to display value (reversed direction)."""
    return _GIMBAL_PAN_OFFSET - actual

def _actual_to_display_tilt(actual):
    """Convert actual tilt angle to display value (reversed direction)."""
    return _GIMBAL_TILT_OFFSET - actual

def _display_to_actual_pan(display):
    """Convert display value to actual pan angle (reversed direction)."""
    return _GIMBAL_PAN_OFFSET - display

def _display_to_actual_tilt(display):
    """Convert display value to actual tilt angle (reversed direction)."""
    return _GIMBAL_TILT_OFFSET - display


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

    app._controls_group = _create_controls_group(app)
    main_layout.addWidget(app._controls_group)

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

    # Create sensor cards for diagnostics view
    app._temp_card = SensorCard("Temp", "°C", "T", 0, 50)
    app._humidity_card = SensorCard("Humidity", "%", "H", 0, 100)
    app._gas_card = SensorCard("Gas", "PPM", "G", 0, 1000)
    
    app._distance_card = SensorCard("Distance", "cm", "D", 0, 200)
    sensors_layout.addWidget(app._distance_card)

    dpad_widget = QWidget()
    dpad_widget.setFixedHeight(140)
    dpad_layout = QVBoxLayout()
    dpad_layout.setContentsMargins(0, 0, 0, 0)
    dpad_layout.setSpacing(4)

    dpad_base = """
        QPushButton {
            background-color: #0f172a;
            border: 1px solid #1e293b;
            color: #475569;
            font-weight: 700;
            font-size: 18px;
        }
        QPushButton:pressed {
            background-color: #06b6d4;
            color: #0a0e1a;
            border-color: #06b6d4;
        }
    """

    dpad_active = """
        QPushButton {
            background-color: #06b6d4;
            color: #0a0e1a;
            border: 1px solid #06b6d4;
            font-weight: 700;
            font-size: 18px;
        }
    """

    dpad_center = """
        QPushButton {
            background-color: #1e293b;
            border: 1px solid #334155;
            color: #64748b;
            font-weight: 700;
            font-size: 16px;
        }
        QPushButton:pressed {
            background-color: #ef4444;
            color: white;
            border-color: #ef4444;
        }
    """

    def _update_dpad_button(btn, active, style_normal, style_active):
        btn.setStyleSheet(style_active if active else style_normal)

    row_up = QHBoxLayout()
    row_up.setContentsMargins(60, 0, 60, 0)
    app._dpad_fwd = QPushButton("▲")
    app._dpad_fwd.setFixedSize(50, 40)
    app._dpad_fwd.setStyleSheet(dpad_base)
    app._dpad_fwd.pressed.connect(lambda: app._send_command("forward"))
    app._dpad_fwd.released.connect(lambda: app._send_command("stop"))
    row_up.addWidget(app._dpad_fwd)
    dpad_layout.addLayout(row_up)

    row_mid = QHBoxLayout()
    row_mid.setContentsMargins(0, 0, 0, 0)
    row_mid.setSpacing(4)
    app._dpad_left = QPushButton("◀")
    app._dpad_left.setFixedSize(50, 40)
    app._dpad_left.setStyleSheet(dpad_base)
    app._dpad_left.pressed.connect(lambda: app._send_command("left"))
    app._dpad_left.released.connect(lambda: app._send_command("stop"))
    row_mid.addWidget(app._dpad_left)

    btn_stop = QPushButton("■")
    btn_stop.setFixedSize(50, 40)
    btn_stop.setStyleSheet(dpad_center)
    btn_stop.pressed.connect(lambda: app._send_command("stop"))
    row_mid.addWidget(btn_stop)

    app._dpad_right = QPushButton("▶")
    app._dpad_right.setFixedSize(50, 40)
    app._dpad_right.setStyleSheet(dpad_base)
    app._dpad_right.pressed.connect(lambda: app._send_command("right"))
    app._dpad_right.released.connect(lambda: app._send_command("stop"))
    row_mid.addWidget(app._dpad_right)
    dpad_layout.addLayout(row_mid)

    row_down = QHBoxLayout()
    row_down.setContentsMargins(60, 0, 60, 0)
    app._dpad_rev = QPushButton("▼")
    app._dpad_rev.setFixedSize(50, 40)
    app._dpad_rev.setStyleSheet(dpad_base)
    app._dpad_rev.pressed.connect(lambda: app._send_command("backward"))
    app._dpad_rev.released.connect(lambda: app._send_command("stop"))
    row_down.addWidget(app._dpad_rev)
    dpad_layout.addLayout(row_down)

    def _on_key_state(direction, pressed):
        mapping = {
            "forward": app._dpad_fwd,
            "backward": app._dpad_rev,
            "left": app._dpad_left,
            "right": app._dpad_right,
        }
        btn = mapping.get(direction)
        if btn:
            _update_dpad_button(btn, pressed, dpad_base, dpad_active)

    if hasattr(app, '_input_handler'):
        app._input_handler.key_state_changed.connect(_on_key_state)

    dpad_widget.setLayout(dpad_layout)
    sensors_layout.addWidget(dpad_widget)

    sensors_layout.addStretch()
    sensors_page.setLayout(sensors_layout)
    app._sidebar_stack.addWidget(sensors_page)

    snapshots_page = QWidget()
    snapshots_layout = QVBoxLayout()
    snapshots_layout.setContentsMargins(0, 0, 0, 0)
    snapshots_layout.setSpacing(8)

    snap_header = QLabel("SNAPSHOTS")
    snap_header.setStyleSheet("""
        color: #f1f5f9;
        font-weight: 700;
        font-size: 11px;
        letter-spacing: 1px;
    """)
    snapshots_layout.addWidget(snap_header)

    app._snapshot_list = QVBoxLayout()
    app._snapshot_list.setSpacing(6)
    snapshots_layout.addLayout(app._snapshot_list)

    snapshots_layout.addStretch()
    snapshots_page.setLayout(snapshots_layout)
    app._sidebar_stack.addWidget(snapshots_page)

    main_layout.addWidget(app._sidebar_stack, 1)

    safety_grid = QHBoxLayout()
    safety_grid.setSpacing(6)

    safety_left = QVBoxLayout()
    safety_left.setSpacing(4)
    app._sidebar_led_btn = QPushButton("LED: OFF")
    app._sidebar_led_btn.setCheckable(True)
    app._sidebar_led_btn.setFixedHeight(28)
    app._sidebar_led_btn.setStyleSheet("""
        QPushButton {
            background-color: rgba(245, 158, 11, 0.12);
            border: 1px solid rgba(245, 158, 11, 0.25);
            color: #f59e0b;
            font-weight: 700;
            font-size: 11px;
            letter-spacing: 1px;
            padding: 0 8px;
        }
        QPushButton:hover {
            background-color: rgba(245, 158, 11, 0.2);
        }
        QPushButton:checked {
            background-color: rgba(245, 158, 11, 0.3);
            color: #fbbf24;
        }
    """)
    app._sidebar_led_btn.clicked.connect(lambda: _toggle_led(app))
    safety_left.addWidget(app._sidebar_led_btn)
    snapshot_action_btn = QPushButton("📷 SNAP")
    snapshot_action_btn.setFixedHeight(28)
    snapshot_action_btn.setStyleSheet("""
        QPushButton {
            background-color: rgba(6, 182, 212, 0.12);
            border: 1px solid rgba(6, 182, 212, 0.25);
            color: #06b6d4;
            font-weight: 700;
            font-size: 11px;
            letter-spacing: 1px;
            padding: 0 8px;
        }
        QPushButton:hover {
            background-color: rgba(6, 182, 212, 0.25);
        }
        QPushButton:pressed {
            background-color: rgba(6, 182, 212, 0.4);
        }
    """)
    snapshot_action_btn.clicked.connect(lambda: app._take_snapshot())
    safety_left.addWidget(snapshot_action_btn)
    safety_grid.addLayout(safety_left)

    safety_right = QVBoxLayout()
    safety_right.setSpacing(4)
    app._sidebar_pid_btn = QPushButton("PID: ON")
    app._sidebar_pid_btn.setCheckable(True)
    app._sidebar_pid_btn.setChecked(True)
    app._sidebar_pid_btn.setFixedHeight(28)
    app._sidebar_pid_btn.setStyleSheet("""
        QPushButton {
            background-color: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.25);
            color: #10b981;
            font-weight: 700;
            font-size: 11px;
            letter-spacing: 1px;
            padding: 0 8px;
        }
        QPushButton:hover {
            background-color: rgba(16, 185, 129, 0.2);
        }
        QPushButton:checked {
            background-color: rgba(16, 185, 129, 0.3);
            color: #34d399;
        }
    """)
    app._sidebar_pid_btn.clicked.connect(lambda: _toggle_pid(app))
    safety_right.addWidget(app._sidebar_pid_btn)
    app._rec_btn = QPushButton("🎬 REC")
    app._rec_btn.setFixedHeight(28)
    app._rec_btn.setCheckable(True)
    app._rec_btn.setStyleSheet("""
        QPushButton {
            background-color: rgba(239, 68, 68, 0.12);
            border: 1px solid rgba(239, 68, 68, 0.25);
            color: #ef4444;
            font-weight: 700;
            font-size: 11px;
            letter-spacing: 1px;
            padding: 0 8px;
        }
        QPushButton:hover {
            background-color: rgba(239, 68, 68, 0.25);
        }
        QPushButton:checked {
            background-color: rgba(239, 68, 68, 0.35);
            color: #f87171;
            border-color: rgba(239, 68, 68, 0.5);
        }
    """)
    app._rec_btn.clicked.connect(lambda: app._toggle_recording())
    safety_right.addWidget(app._rec_btn)
    safety_grid.addLayout(safety_right)

    main_layout.addLayout(safety_grid)

    app._web_control_btn = QPushButton("WEB CONTROL: OFF")
    app._web_control_btn.setCheckable(True)
    app._web_control_btn.setStyleSheet("""
        QPushButton {
            background-color: rgba(59, 130, 246, 0.12);
            border: 1px solid rgba(59, 130, 246, 0.25);
            color: #3b82f6;
            font-weight: 700;
            font-size: 11px;
            letter-spacing: 1px;
        }
        QPushButton:hover {
            background-color: rgba(59, 130, 246, 0.2);
        }
        QPushButton:checked {
            background-color: rgba(59, 130, 246, 0.3);
            color: #60a5fa;
        }
    """)
    app._web_control_btn.clicked.connect(app._toggle_web_control)
    main_layout.addWidget(app._web_control_btn)

    main_layout.addStretch()

    follow_btn = QPushButton("FOLLOW MODE")
    follow_btn.setStyleSheet("""
        QPushButton {
            background-color: rgba(124, 58, 237, 0.12);
            border: 1px solid rgba(124, 58, 237, 0.25);
            color: #7c3aed;
            font-weight: 700;
            font-size: 11px;
            letter-spacing: 1px;
        }
        QPushButton:hover {
            background-color: rgba(124, 58, 237, 0.2);
        }
    """)
    follow_btn.clicked.connect(app._toggle_follow_mode)
    app._follow_btn = follow_btn
    main_layout.addWidget(follow_btn)

    sidebar.setLayout(main_layout)
    return sidebar


def _create_controls_group(app):
    """Drive/camera controls (speed, brake, gimbal, snapshot, recording, detection).

    Kept outside the sidebar's page stack so it stays visible regardless of
    which page (sensors/settings/snapshots) is active.
    """
    group = QGroupBox("CONTROLS")
    group.setStyleSheet("""
        QGroupBox {
            background-color: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 8px;
            padding: 14px 10px 10px 10px;
            margin-top: 6px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            color: #94a3b8;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1.5px;
        }
    """)
    layout = QVBoxLayout()
    layout.setContentsMargins(8, 6, 8, 6)
    layout.setSpacing(8)

    speed_row = QHBoxLayout()
    speed_row.setSpacing(8)
    speed_label = QLabel("SPEED")
    speed_label.setFixedWidth(45)
    speed_label.setStyleSheet("color: #64748b; font-size: 10px; letter-spacing: 1px;")
    speed_row.addWidget(speed_label)
    app._speed_slider = QSlider(Qt.Orientation.Horizontal)
    app._speed_slider.setRange(180, 255)
    app._speed_slider.setValue(app._current_speed)
    app._speed_slider.valueChanged.connect(lambda v: _on_speed_change(app, v))
    speed_row.addWidget(app._speed_slider, 1)
    app._speed_label = QLabel(f"{app._current_speed}")
    app._speed_label.setStyleSheet("color: #06b6d4; font-size: 11px; font-family: 'JetBrains Mono', monospace; font-weight: 600;")
    app._speed_label.setFixedWidth(28)
    app._speed_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    speed_row.addWidget(app._speed_label)
    layout.addLayout(speed_row)

    brake_row = QHBoxLayout()
    brake_row.setSpacing(8)
    brake_label = QLabel("BRAKE")
    brake_label.setFixedWidth(45)
    brake_label.setStyleSheet("color: #64748b; font-size: 10px; letter-spacing: 1px;")
    brake_row.addWidget(brake_label)
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
        }
        QPushButton:!checked {
            background-color: #475569;
        }
    """)
    app._brake_toggle.clicked.connect(lambda: _toggle_brake(app))
    brake_row.addWidget(app._brake_toggle)
    brake_row.addStretch()
    layout.addLayout(brake_row)

    gimbal_row = QHBoxLayout()
    gimbal_row.setSpacing(6)
    pan_label = QLabel("PAN")
    pan_label.setStyleSheet("color: #475569; font-size: 8px; letter-spacing: 1px;")
    gimbal_row.addWidget(pan_label)
    app._gimbal_pan_input = QLineEdit(str(_actual_to_display_pan(app._gimbal_pan)))
    app._gimbal_pan_input.setFixedWidth(36)
    app._gimbal_pan_input.setFixedHeight(22)
    app._gimbal_pan_input.setStyleSheet("""
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 3px;
        color: #e2e8f0;
        font-size: 10px;
        font-family: 'JetBrains Mono', monospace;
        padding: 2px 4px;
    """)
    app._gimbal_pan_input.returnPressed.connect(lambda: _on_gimbal_input(app, 'pan'))
    gimbal_row.addWidget(app._gimbal_pan_input)
    tilt_label = QLabel("TILT")
    tilt_label.setStyleSheet("color: #475569; font-size: 8px; letter-spacing: 1px;")
    gimbal_row.addWidget(tilt_label)
    app._gimbal_tilt_input = QLineEdit(str(_actual_to_display_tilt(app._gimbal_tilt)))
    app._gimbal_tilt_input.setFixedWidth(36)
    app._gimbal_tilt_input.setFixedHeight(22)
    app._gimbal_tilt_input.setStyleSheet("""
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 3px;
        color: #e2e8f0;
        font-size: 10px;
        font-family: 'JetBrains Mono', monospace;
        padding: 2px 4px;
    """)
    app._gimbal_tilt_input.returnPressed.connect(lambda: _on_gimbal_input(app, 'tilt'))
    gimbal_row.addWidget(app._gimbal_tilt_input)
    gimbal_row.addStretch()
    center_btn = QPushButton("C")
    center_btn.setFixedSize(28, 28)
    center_btn.setStyleSheet("""
        QPushButton {
            background-color: #1e293b;
            border: 1px solid #06b6d4;
            color: #06b6d4;
            font-weight: 700;
            font-size: 12px;
            border-radius: 14px;
        }
        QPushButton:hover {
            background-color: #06b6d4;
            color: #0a0e1a;
        }
    """)
    center_btn.clicked.connect(app._center_gimbal)
    gimbal_row.addWidget(center_btn)
    layout.addLayout(gimbal_row)

    app._mouse_gimbal_btn = QPushButton("MOUSE GIMBAL")
    app._mouse_gimbal_btn.setFixedHeight(26)
    app._mouse_gimbal_btn.setCheckable(True)
    app._mouse_gimbal_btn.setChecked(True)
    app._mouse_gimbal_btn.setStyleSheet("""
        QPushButton {
            background-color: #1e293b;
            border: 1px solid #334155;
            color: #06b6d4;
            font-weight: 600;
            font-size: 10px;
            letter-spacing: 1px;
        }
        QPushButton:checked {
            background-color: #06b6d4;
            color: #0a0e1a;
        }
    """)
    app._mouse_gimbal_btn.clicked.connect(lambda: _toggle_mouse_gimbal(app))
    layout.addWidget(app._mouse_gimbal_btn)

    app._super_res_check = QCheckBox("Super Resolution")
    app._super_res_check.setStyleSheet("color: #64748b; font-size: 10px;")
    layout.addWidget(app._super_res_check)

    group.setLayout(layout)
    return group


def _on_speed_change(app, value):
    app._global_speed = value
    app._speed_label.setText(f"{value}")
    app._schedule_speed_apply()


def _toggle_mouse_gimbal(app):
    checked = app._mouse_gimbal_btn.isChecked()
    if hasattr(app, '_video_canvas'):
        app._video_canvas._mouse_gimbal_enabled = checked
    app._add_log("GIMBAL", f"Mouse gimbal {'enabled' if checked else 'disabled'}")


def _on_gimbal_input(app, axis):
    if axis == 'pan':
        text = app._gimbal_pan_input.text().strip()
    else:
        text = app._gimbal_tilt_input.text().strip()
    try:
        display_value = int(text)
    except ValueError:
        return
    # Convert display value to actual angle
    if axis == 'pan':
        actual_angle = max(0, min(180, _display_to_actual_pan(display_value)))
        app._gimbal_pan = actual_angle
    else:
        actual_angle = max(0, min(180, _display_to_actual_tilt(display_value)))
        app._gimbal_tilt = actual_angle
    app._send_command(f"servo:{app._gimbal_pan},{app._gimbal_tilt}")
    if hasattr(app, '_gimbal_hud'):
        app._gimbal_hud.set_gimbal(app._gimbal_pan, app._gimbal_tilt)



def _toggle_recording(app):
    checked = app._rec_btn.isChecked()
    if checked:
        app._start_recording()
    else:
        app._stop_recording()


def _toggle_snapshots(app):
    if app._sidebar_stack.currentIndex() == 2:
        app._sidebar_stack.setCurrentIndex(0)
    else:
        app._sidebar_stack.setCurrentIndex(2)
        _load_snapshots(app)


def _toggle_brake(app):
    checked = app._brake_toggle.isChecked()
    app._brake_toggle.setText("ON" if checked else "OFF")
    if hasattr(app, '_config'):
        app._config["auto_brake"] = checked
    if hasattr(app, '_esp32_api'):
        app._esp32_api.set_brake(checked)
    app._add_log("SAFETY", f"Auto-brake {'enabled' if checked else 'disabled'}")


def _on_led_change(app, value):
    if hasattr(app, '_sidebar_led_label'):
        app._sidebar_led_label.setText(str(value))
    if hasattr(app, '_sidebar_led_toggle'):
        app._sidebar_led_toggle.setChecked(value > 0)
        app._sidebar_led_toggle.setText("ON" if value > 0 else "OFF")
    if hasattr(app, '_esp32_api'):
        app._esp32_api.set_led(value)
    app._add_log("LED", f"Brightness: {value}")


def _toggle_led(app):
    if hasattr(app, '_led_debounce_timer') and app._led_debounce_timer.isActive():
        return
    app._led_debounce_timer = QTimer()
    app._led_debounce_timer.setSingleShot(True)
    app._led_debounce_timer.start(500)
    checked = app._sidebar_led_btn.isChecked()
    app._sidebar_led_btn.setText("LED: ON" if checked else "LED: OFF")
    if hasattr(app, '_apply_led'):
        app._apply_led(255 if checked else 0)
    app._add_log("LED", f"{'ON' if checked else 'OFF'}")


def _toggle_pid(app):
    """実機で「PIDのkpが勝手に2になる」と報告されたバグの原因: このボタンは
    以前 esp32_api.set_pid(enabled=checked) を直接呼んでおり、enabledだけを
    送ってkp/ki/kd/biasを一切含めていなかった。ESP32側がkp/ki/kd未指定を
    「ファームウェアのデフォルトへリセット」として扱っていたため、このボタンを
    押すたびにSETTINGSタブ・DEBUGタブで調整した値が消えていた。
    SETTINGSタブの_pid_toggle/_apply_pid_params()と同じ経路(kp/ki/kd/biasの
    現在値を必ず一緒に送る)に統一する。"""
    checked = app._sidebar_pid_btn.isChecked()
    app._sidebar_pid_btn.setText("PID: ON" if checked else "PID: OFF")
    if hasattr(app, '_pid_toggle'):
        app._pid_toggle.setChecked(checked)
        app._pid_toggle.setText("ON" if checked else "OFF")
        from views.settings_view import TOGGLE_ON_STYLE, TOGGLE_OFF_STYLE
        app._pid_toggle.setStyleSheet(TOGGLE_ON_STYLE if checked else TOGGLE_OFF_STYLE)
    if hasattr(app, '_apply_pid_params'):
        app._apply_pid_params()
    app._add_log("PID", f"PID straight {'enabled' if checked else 'disabled'}")


def _load_snapshots(app):
    if not hasattr(app, '_cloud_api') or not app._cloud_api:
        return

    while app._snapshot_list.count():
        item = app._snapshot_list.takeAt(0)
        if item.widget():
            item.widget().deleteLater()

    from cloud_worker import CloudWorker
    url = f"{app._cloud_api._base_url}/rovers/{app._cloud_api._device_uid}/media"
    worker = CloudWorker("GET", url)
    worker.result.connect(lambda data: _on_snapshots_loaded(app, data))
    worker.error.connect(lambda e: app._add_log("SNAPSHOT", f"Load error: {e}"))
    app._cloud_workers.append(worker)
    worker.finished.connect(lambda: app._cloud_workers.remove(worker) if worker in app._cloud_workers else None)
    worker.start()


def _extract_video_frame(video_data):
    """Extract first frame from video data for thumbnail."""
    import cv2
    import numpy as np
    import os
    from tempfile import gettempdir
    from PyQt6.QtGui import QImage, QPixmap

    tmp_path = os.path.join(gettempdir(), "thumb_temp.avi")
    try:
        with open(tmp_path, "wb") as f:
            f.write(video_data)

        cap = cv2.VideoCapture(tmp_path)
        ret, frame = cap.read()
        cap.release()
        os.remove(tmp_path)

        if ret and frame is not None:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            return QPixmap.fromImage(qimg)
    except Exception:
        pass
    return None


def _on_snapshots_loaded(app, data):
    if isinstance(data, dict):
        data = data.get("media", [])
    if not isinstance(data, list):
        return

    for snap in data[:10]:
        item = QWidget()
        item.setFixedHeight(60)
        item.setStyleSheet("""
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 4px;
            padding: 2px;
        """)
        item_layout = QHBoxLayout()
        item_layout.setContentsMargins(4, 2, 4, 2)
        item_layout.setSpacing(6)

        thumb_label = QLabel()
        thumb_label.setFixedSize(52, 52)
        thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb_label.setStyleSheet("background-color: #0f172a; border-radius: 4px; color: #64748b; font-size: 8px;")
        thumb_label.setText("...")

        snap_id = snap.get("id")
        media_type = snap.get("media_type", "photo")
        
        if snap_id:
            media_data = app._cloud_api.get_media_item(snap_id)
            if media_data:
                if media_type == "video":
                    pixmap = _extract_video_frame(media_data)
                else:
                    pixmap = QPixmap()
                    pixmap.loadFromData(media_data)
                
                if pixmap and not pixmap.isNull():
                    scaled = pixmap.scaled(52, 52, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    thumb_label.setPixmap(scaled)
                else:
                    thumb_label.setText("N/A")
            else:
                thumb_label.setText("N/A")

        type_label = QLabel("V" if media_type == "video" else "P")
        type_label.setFixedSize(14, 14)
        type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        type_label.setStyleSheet("""
            background-color: %s;
            color: white;
            font-size: 7px;
            font-weight: bold;
            border-radius: 7px;
        """ % ("#8b5cf6" if media_type == "video" else "#10b981"))
        item_layout.addWidget(type_label)

        item_layout.addWidget(thumb_label)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        time_label = QLabel(str(snap.get("captured_at", ""))[:16].replace("T", " "))
        time_label.setStyleSheet("color: #94a3b8; font-size: 9px; font-family: 'JetBrains Mono', monospace;")
        info_layout.addWidget(time_label)
        size = snap.get("file_size_bytes", 0)
        size_label = QLabel(f"{size // 1024}KB")
        size_label.setStyleSheet("color: #64748b; font-size: 8px;")
        info_layout.addWidget(size_label)
        item_layout.addLayout(info_layout, 1)

        delete_btn = QPushButton("X")
        delete_btn.setFixedSize(18, 18)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.2);
                color: #ef4444;
                border: none;
                border-radius: 9px;
                font-size: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.4);
            }
        """)
        delete_btn.clicked.connect(lambda checked, sid=snap_id: _delete_snapshot(app, sid))
        item_layout.addWidget(delete_btn)

        item.setLayout(item_layout)
        app._snapshot_list.addWidget(item)


def _delete_snapshot(app, snap_id):
    if not hasattr(app, '_cloud_api') or not app._cloud_api:
        return

    from cloud_worker import CloudWorker
    url = f"{app._cloud_api._base_url}/rovers/{app._cloud_api._device_uid}/media/{snap_id}"
    worker = CloudWorker("DELETE", url)
    worker.result.connect(lambda: _load_snapshots(app))
    worker.error.connect(lambda e: app._add_log("SNAPSHOT", f"Delete error: {e}"))
    app._cloud_workers.append(worker)
    worker.finished.connect(lambda: app._cloud_workers.remove(worker) if worker in app._cloud_workers else None)
    worker.start()
