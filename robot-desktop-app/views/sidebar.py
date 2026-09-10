from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
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

    sensors_layout.addStretch()
    sensors_page.setLayout(sensors_layout)
    app._sidebar_stack.addWidget(sensors_page)

    settings_page = QWidget()
    settings_layout = QVBoxLayout()
    settings_layout.setContentsMargins(0, 4, 0, 4)
    settings_layout.setSpacing(14)

    pid_group = QGroupBox("PID STRAIGHT")
    pid_group.setStyleSheet("""
        QGroupBox {
            background-color: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 8px;
            padding: 14px 10px 10px 10px;
            margin-top: 14px;
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
    pid_layout = QVBoxLayout()
    pid_layout.setContentsMargins(8, 6, 8, 6)
    pid_layout.setSpacing(6)

    app._pid_toggle = QPushButton("OFF")
    app._pid_toggle.setCheckable(True)
    app._pid_toggle.setFixedHeight(26)
    app._pid_toggle.setStyleSheet("""
        QPushButton {
            background-color: #475569;
            color: white;
            font-weight: 600;
            font-size: 10px;
            border: none;
            border-radius: 13px;
            padding: 0 14px;
        }
        QPushButton:checked {
            background-color: #10b981;
        }
    """)
    app._pid_toggle.clicked.connect(lambda: _toggle_pid(app))
    pid_layout.addWidget(app._pid_toggle)

    kp_row = QHBoxLayout()
    kp_row.setSpacing(8)
    kp_label = QLabel("Kp")
    kp_label.setFixedWidth(24)
    kp_label.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 500;")
    kp_row.addWidget(kp_label)
    app._kp_slider = QSlider(Qt.Orientation.Horizontal)
    app._kp_slider.setRange(0, 100)
    app._kp_slider.setValue(20)
    app._kp_slider.valueChanged.connect(lambda v: _on_pid_change(app))
    kp_row.addWidget(app._kp_slider, 1)
    app._kp_label = QLabel("20")
    app._kp_label.setStyleSheet("color: #06b6d4; font-size: 11px; font-family: 'JetBrains Mono', monospace; font-weight: 600;")
    app._kp_label.setFixedWidth(28)
    app._kp_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    kp_row.addWidget(app._kp_label)
    pid_layout.addLayout(kp_row)

    ki_row = QHBoxLayout()
    ki_row.setSpacing(8)
    ki_label = QLabel("Ki")
    ki_label.setFixedWidth(24)
    ki_label.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 500;")
    ki_row.addWidget(ki_label)
    app._ki_slider = QSlider(Qt.Orientation.Horizontal)
    app._ki_slider.setRange(0, 100)
    app._ki_slider.setValue(5)
    app._ki_slider.valueChanged.connect(lambda v: _on_pid_change(app))
    ki_row.addWidget(app._ki_slider, 1)
    app._ki_label = QLabel("5")
    app._ki_label.setStyleSheet("color: #06b6d4; font-size: 11px; font-family: 'JetBrains Mono', monospace; font-weight: 600;")
    app._ki_label.setFixedWidth(28)
    app._ki_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    ki_row.addWidget(app._ki_label)
    pid_layout.addLayout(ki_row)

    kd_row = QHBoxLayout()
    kd_row.setSpacing(8)
    kd_label = QLabel("Kd")
    kd_label.setFixedWidth(24)
    kd_label.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 500;")
    kd_row.addWidget(kd_label)
    app._kd_slider = QSlider(Qt.Orientation.Horizontal)
    app._kd_slider.setRange(0, 100)
    app._kd_slider.setValue(10)
    app._kd_slider.valueChanged.connect(lambda v: _on_pid_change(app))
    kd_row.addWidget(app._kd_slider, 1)
    app._kd_label = QLabel("10")
    app._kd_label.setStyleSheet("color: #06b6d4; font-size: 11px; font-family: 'JetBrains Mono', monospace; font-weight: 600;")
    app._kd_label.setFixedWidth(28)
    app._kd_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    kd_row.addWidget(app._kd_label)
    pid_layout.addLayout(kd_row)

    pid_group.setLayout(pid_layout)
    settings_layout.addWidget(pid_group)

    cam_group = QGroupBox("CAMERA")
    cam_group.setStyleSheet("""
        QGroupBox {
            background-color: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 8px;
            padding: 14px 10px 10px 10px;
            margin-top: 14px;
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
    cam_layout = QVBoxLayout()
    cam_layout.setContentsMargins(8, 6, 8, 6)
    cam_layout.setSpacing(8)

    led_row = QHBoxLayout()
    led_row.setSpacing(8)
    led_label = QLabel("LED")
    led_label.setFixedWidth(24)
    led_label.setStyleSheet("color: #64748b; font-size: 11px; letter-spacing: 1px;")
    led_row.addWidget(led_label)

    app._led_slider = QSlider(Qt.Orientation.Horizontal)
    app._led_slider.setRange(0, 255)
    app._led_slider.setValue(0)
    app._led_slider.setFixedWidth(120)
    app._led_slider.valueChanged.connect(lambda v: _on_led_change(app, v))
    led_row.addWidget(app._led_slider)

    app._led_label = QLabel("0")
    app._led_label.setStyleSheet("color: #e2e8f0; font-size: 11px; font-family: 'JetBrains Mono', monospace; font-weight: 600;")
    app._led_label.setFixedWidth(28)
    app._led_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    led_row.addWidget(app._led_label)

    app._led_flash_btn = QPushButton("FLASH")
    app._led_flash_btn.setCheckable(True)
    app._led_flash_btn.setFixedWidth(50)
    app._led_flash_btn.setFixedHeight(22)
    app._led_flash_btn.setStyleSheet("""
        QPushButton {
            background-color: #475569;
            color: white;
            font-weight: 600;
            font-size: 9px;
            border: none;
            border-radius: 11px;
        }
        QPushButton:checked {
            background-color: #f59e0b;
        }
    """)
    app._led_flash_btn.clicked.connect(lambda: _toggle_led_flash(app))
    led_row.addWidget(app._led_flash_btn)

    cam_layout.addLayout(led_row)

    quality_row = QHBoxLayout()
    quality_row.setSpacing(8)
    quality_label = QLabel("Q")
    quality_label.setFixedWidth(24)
    quality_label.setStyleSheet("color: #64748b; font-size: 11px; letter-spacing: 1px;")
    quality_row.addWidget(quality_label)

    app._quality_slider = QSlider(Qt.Orientation.Horizontal)
    app._quality_slider.setRange(0, 63)
    app._quality_slider.setValue(14)
    app._quality_slider.setFixedWidth(120)
    app._quality_slider.valueChanged.connect(lambda v: _on_quality_change(app, v))
    quality_row.addWidget(app._quality_slider)

    app._quality_label = QLabel("14")
    app._quality_label.setStyleSheet("color: #e2e8f0; font-size: 11px; font-family: 'JetBrains Mono', monospace; font-weight: 600;")
    app._quality_label.setFixedWidth(28)
    app._quality_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    quality_row.addWidget(app._quality_label)

    quality_row.addStretch()
    cam_layout.addLayout(quality_row)

    cam_group.setLayout(cam_layout)
    settings_layout.addWidget(cam_group)

    hf_group = QGroupBox("HF TOKEN")
    hf_group.setStyleSheet("""
        QGroupBox {
            background-color: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 8px;
            padding: 14px 10px 10px 10px;
            margin-top: 14px;
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
    hf_layout = QVBoxLayout()
    hf_layout.setContentsMargins(8, 6, 8, 6)
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
        font-size: 11px;
        padding: 6px 10px;
        border-radius: 4px;
    """)
    app._hf_token_input.returnPressed.connect(lambda: _save_hf_token(app))
    hf_layout.addWidget(app._hf_token_input)

    hf_group.setLayout(hf_layout)
    settings_layout.addWidget(hf_group)

    cloud_group = QGroupBox("CLOUD")
    cloud_group.setStyleSheet("""
        QGroupBox {
            background-color: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 8px;
            padding: 14px 10px 10px 10px;
            margin-top: 14px;
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
    cloud_layout = QVBoxLayout()
    cloud_layout.setContentsMargins(8, 6, 8, 6)
    cloud_layout.setSpacing(6)

    cloud_btn_row = QHBoxLayout()
    cloud_btn_row.setSpacing(8)

    app._cloud_send_btn = QPushButton("SEND")
    app._cloud_send_btn.setFixedHeight(30)
    app._cloud_send_btn.setStyleSheet("""
        QPushButton {
            background-color: #7c3aed;
            color: white;
            font-weight: 600;
            font-size: 11px;
            border: none;
            padding: 4px 16px;
            letter-spacing: 1px;
        }
        QPushButton:hover {
            background-color: #6d28d9;
        }
    """)
    app._cloud_send_btn.clicked.connect(app._manual_send_to_cloud)
    cloud_btn_row.addWidget(app._cloud_send_btn, 1)

    app._toggle_view_btn = QPushButton("DATA")
    app._toggle_view_btn.setFixedHeight(30)
    app._toggle_view_btn.setCheckable(True)
    app._toggle_view_btn.setStyleSheet("""
        QPushButton {
            background-color: #1e293b;
            border: 1px solid #334155;
            color: #06b6d4;
            font-weight: 600;
            font-size: 11px;
            padding: 4px 16px;
            letter-spacing: 1px;
        }
        QPushButton:checked {
            background-color: #06b6d4;
            color: #0a0e1a;
        }
    """)
    app._toggle_view_btn.clicked.connect(app._toggle_view)
    cloud_btn_row.addWidget(app._toggle_view_btn, 1)

    cloud_layout.addLayout(cloud_btn_row)
    cloud_group.setLayout(cloud_layout)
    settings_layout.addWidget(cloud_group)

    follow_group = QGroupBox("FOLLOW MODE")
    follow_group.setStyleSheet("""
        QGroupBox {
            background-color: #0f172a;
            border: 1px solid rgba(124, 58, 237, 0.4);
            border-radius: 8px;
            padding: 14px 10px 10px 10px;
            margin-top: 14px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            color: #7c3aed;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1.5px;
        }
    """)
    follow_layout = QVBoxLayout()
    follow_layout.setContentsMargins(8, 6, 8, 6)
    follow_layout.setSpacing(5)

    k_row = QHBoxLayout()
    k_row.setSpacing(8)
    k_label = QLabel("k")
    k_label.setFixedWidth(24)
    k_label.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 500;")
    k_row.addWidget(k_label)
    app._follow_k_slider = QSlider(Qt.Orientation.Horizontal)
    app._follow_k_slider.setRange(1, 20)
    app._follow_k_slider.setValue(5)
    app._follow_k_slider.valueChanged.connect(lambda v: _on_follow_param_change(app))
    k_row.addWidget(app._follow_k_slider, 1)
    app._follow_k_label = QLabel("0.5")
    app._follow_k_label.setStyleSheet("color: #7c3aed; font-size: 11px; font-family: 'JetBrains Mono', monospace; font-weight: 600;")
    app._follow_k_label.setFixedWidth(30)
    app._follow_k_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    k_row.addWidget(app._follow_k_label)
    follow_layout.addLayout(k_row)

    kp_row = QHBoxLayout()
    kp_row.setSpacing(8)
    kp_label = QLabel("kp")
    kp_label.setFixedWidth(24)
    kp_label.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 500;")
    kp_row.addWidget(kp_label)
    app._follow_kp_slider = QSlider(Qt.Orientation.Horizontal)
    app._follow_kp_slider.setRange(1, 50)
    app._follow_kp_slider.setValue(20)
    app._follow_kp_slider.valueChanged.connect(lambda v: _on_follow_param_change(app))
    kp_row.addWidget(app._follow_kp_slider, 1)
    app._follow_kp_label = QLabel("2.0")
    app._follow_kp_label.setStyleSheet("color: #7c3aed; font-size: 11px; font-family: 'JetBrains Mono', monospace; font-weight: 600;")
    app._follow_kp_label.setFixedWidth(30)
    app._follow_kp_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    kp_row.addWidget(app._follow_kp_label)
    follow_layout.addLayout(kp_row)

    ki_row = QHBoxLayout()
    ki_row.setSpacing(8)
    ki_label = QLabel("ki")
    ki_label.setFixedWidth(24)
    ki_label.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 500;")
    ki_row.addWidget(ki_label)
    app._follow_ki_slider = QSlider(Qt.Orientation.Horizontal)
    app._follow_ki_slider.setRange(0, 50)
    app._follow_ki_slider.setValue(1)
    app._follow_ki_slider.valueChanged.connect(lambda v: _on_follow_param_change(app))
    ki_row.addWidget(app._follow_ki_slider, 1)
    app._follow_ki_label = QLabel("0.1")
    app._follow_ki_label.setStyleSheet("color: #7c3aed; font-size: 11px; font-family: 'JetBrains Mono', monospace; font-weight: 600;")
    app._follow_ki_label.setFixedWidth(30)
    app._follow_ki_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    ki_row.addWidget(app._follow_ki_label)
    follow_layout.addLayout(ki_row)

    kd_row = QHBoxLayout()
    kd_row.setSpacing(8)
    kd_label = QLabel("kd")
    kd_label.setFixedWidth(24)
    kd_label.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 500;")
    kd_row.addWidget(kd_label)
    app._follow_kd_slider = QSlider(Qt.Orientation.Horizontal)
    app._follow_kd_slider.setRange(1, 30)
    app._follow_kd_slider.setValue(5)
    app._follow_kd_slider.valueChanged.connect(lambda v: _on_follow_param_change(app))
    kd_row.addWidget(app._follow_kd_slider, 1)
    app._follow_kd_label = QLabel("0.5")
    app._follow_kd_label.setStyleSheet("color: #7c3aed; font-size: 11px; font-family: 'JetBrains Mono', monospace; font-weight: 600;")
    app._follow_kd_label.setFixedWidth(30)
    app._follow_kd_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    kd_row.addWidget(app._follow_kd_label)
    follow_layout.addLayout(kd_row)

    dist_kp_row = QHBoxLayout()
    dist_kp_row.setSpacing(8)
    dist_kp_label = QLabel("dist")
    dist_kp_label.setFixedWidth(24)
    dist_kp_label.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 500;")
    dist_kp_row.addWidget(dist_kp_label)
    app._follow_dist_kp_slider = QSlider(Qt.Orientation.Horizontal)
    app._follow_dist_kp_slider.setRange(1, 30)
    app._follow_dist_kp_slider.setValue(10)
    app._follow_dist_kp_slider.valueChanged.connect(lambda v: _on_follow_param_change(app))
    dist_kp_row.addWidget(app._follow_dist_kp_slider, 1)
    app._follow_dist_kp_label = QLabel("1.0")
    app._follow_dist_kp_label.setStyleSheet("color: #7c3aed; font-size: 11px; font-family: 'JetBrains Mono', monospace; font-weight: 600;")
    app._follow_dist_kp_label.setFixedWidth(30)
    app._follow_dist_kp_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    dist_kp_row.addWidget(app._follow_dist_kp_label)
    follow_layout.addLayout(dist_kp_row)

    # Camera yaw offset
    cam_offset_row = QHBoxLayout()
    cam_offset_label = QLabel("CAM OFFSET")
    cam_offset_label.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 600; letter-spacing: 1px;")
    cam_offset_label.setFixedWidth(75)
    cam_offset_row.addWidget(cam_offset_label)
    app._follow_cam_offset_slider = QSlider(Qt.Orientation.Horizontal)
    app._follow_cam_offset_slider.setRange(-45, 45)  # -45 to +45 degrees
    app._follow_cam_offset_slider.setValue(0)
    app._follow_cam_offset_slider.valueChanged.connect(lambda v: _on_follow_param_change(app))
    cam_offset_row.addWidget(app._follow_cam_offset_slider, 1)
    app._follow_cam_offset_label = QLabel("0.0")
    app._follow_cam_offset_label.setStyleSheet("color: #7c3aed; font-size: 11px; font-family: 'JetBrains Mono', monospace; font-weight: 600;")
    app._follow_cam_offset_label.setFixedWidth(30)
    app._follow_cam_offset_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    cam_offset_row.addWidget(app._follow_cam_offset_label)
    follow_layout.addLayout(cam_offset_row)

    follow_group.setLayout(follow_layout)
    settings_layout.addWidget(follow_group)

    settings_layout.addStretch()
    settings_page.setLayout(settings_layout)
    app._sidebar_stack.addWidget(settings_page)

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
    diag_btn.setCheckable(True)
    diag_btn.setStyleSheet("""
        QPushButton {
            background-color: #1e293b;
            border: 1px solid #334155;
            color: #64748b;
            font-weight: 600;
            font-size: 10px;
            letter-spacing: 1px;
        }
        QPushButton:checked {
            background-color: #f59e0b;
            color: #0a0e1a;
        }
    """)
    diag_btn.clicked.connect(app._toggle_view)
    app._diag_btn = diag_btn
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
    app._follow_btn = follow_btn
    main_layout.addWidget(follow_btn)

    snapshot_btn = QPushButton("SNAPSHOTS")
    snapshot_btn.setCheckable(True)
    snapshot_btn.setStyleSheet("""
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
    snapshot_btn.clicked.connect(app._toggle_snapshots_view)
    app._snapshot_btn = snapshot_btn
    main_layout.addWidget(snapshot_btn)

    app._web_control_btn = QPushButton("WEB CONTROL: OFF")
    app._web_control_btn.setCheckable(True)
    app._web_control_btn.setStyleSheet("""
        QPushButton {
            background-color: #1e293b;
            border: 1px solid #334155;
            color: #64748b;
            font-weight: 600;
            font-size: 10px;
            letter-spacing: 1px;
        }
        QPushButton:checked {
            background-color: #10b981;
            color: #0a0e1a;
            border-color: #10b981;
        }
    """)
    app._web_control_btn.clicked.connect(app._toggle_web_control)
    main_layout.addWidget(app._web_control_btn)

    sidebar.setLayout(main_layout)
    return sidebar


def _toggle_snapshots(app):
    if app._sidebar_stack.currentIndex() == 2:
        app._sidebar_stack.setCurrentIndex(0)
    else:
        app._sidebar_stack.setCurrentIndex(2)
        _load_snapshots(app)


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


def _on_follow_param_change(app):
    k = app._follow_k_slider.value() / 10.0
    kp = app._follow_kp_slider.value() / 10.0
    ki = app._follow_ki_slider.value() / 10.0
    kd = app._follow_kd_slider.value() / 10.0
    dist_kp = app._follow_dist_kp_slider.value() / 10.0
    cam_offset = app._follow_cam_offset_slider.value()
    
    app._follow_k_label.setText(f"{k:.1f}")
    app._follow_kp_label.setText(f"{kp:.1f}")
    app._follow_ki_label.setText(f"{ki:.1f}")
    app._follow_kd_label.setText(f"{kd:.1f}")
    app._follow_dist_kp_label.setText(f"{dist_kp:.1f}")
    app._follow_cam_offset_label.setText(f"{cam_offset:.0f}")
    
    if hasattr(app, '_detection_mgr') and app._detection_mgr._follow_controller:
        app._detection_mgr._follow_controller.config.k = k
        app._detection_mgr._follow_controller.config.kp = kp
        app._detection_mgr._follow_controller.config.ki = ki
        app._detection_mgr._follow_controller.config.kd = kd
        app._detection_mgr._follow_controller.config.dist_kp = dist_kp
        app._detection_mgr._follow_controller.config.camera_yaw_offset = cam_offset


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
