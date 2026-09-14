from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QProgressBar, QPushButton, QSlider, QVBoxLayout,
    QWidget, QFrame
)


CARD_STYLE = """
    QFrame {
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #1e293b, stop:1 #0f172a);
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 16px;
    }
"""

SECTION_TITLE_STYLE = """
    color: #22d3ee;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 2px;
    padding: 4px 0;
    background-color: transparent;
"""

GROUP_BOX_STYLE = """
    QGroupBox {
        background-color: transparent;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 16px 12px 12px 12px;
        margin-top: 16px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 14px;
        padding: 0 8px;
        color: #e2e8f0;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 2px;
    }
"""

INPUT_STYLE = """
    QLineEdit {
        background-color: #0f172a;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 8px 12px;
        color: #e2e8f0;
        font-size: 12px;
        font-family: 'JetBrains Mono', monospace;
        selection-background-color: #06b6d4;
    }
    QLineEdit:focus {
        border: 1px solid #06b6d4;
    }
    QLineEdit:hover {
        border: 1px solid #475569;
    }
    QLineEdit::placeholder {
        color: #64748b;
    }
"""

SLIDER_STYLE = """
    QSlider::groove:horizontal {
        background: #1e293b;
        height: 6px;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background: #06b6d4;
        width: 16px;
        height: 16px;
        margin: -5px 0;
        border-radius: 8px;
    }
    QSlider::handle:horizontal:hover {
        background: #22d3ee;
    }
    QSlider::sub-page:horizontal {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #0891b2, stop:1 #06b6d4);
        border-radius: 3px;
    }
"""

PURPLE_SLIDER_STYLE = """
    QSlider::groove:horizontal {
        background: #1e293b;
        height: 6px;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background: #7c3aed;
        width: 16px;
        height: 16px;
        margin: -5px 0;
        border-radius: 8px;
    }
    QSlider::handle:horizontal:hover {
        background: #8b5cf6;
    }
    QSlider::sub-page:horizontal {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #6d28d9, stop:1 #7c3aed);
        border-radius: 3px;
    }
"""

AMBER_SLIDER_STYLE = """
    QSlider::groove:horizontal {
        background: #1e293b;
        height: 6px;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background: #f59e0b;
        width: 16px;
        height: 16px;
        margin: -5px 0;
        border-radius: 8px;
    }
    QSlider::handle:horizontal:hover {
        background: #fbbf24;
    }
    QSlider::sub-page:horizontal {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #d97706, stop:1 #f59e0b);
        border-radius: 3px;
    }
"""

TOGGLE_ON_STYLE = """
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #059669, stop:1 #10b981);
        color: white;
        font-weight: 700;
        font-size: 10px;
        border: none;
        border-radius: 12px;
        padding: 0 16px;
    }
"""

TOGGLE_OFF_STYLE = """
    QPushButton {
        background-color: #334155;
        color: #94a3b8;
        font-weight: 600;
        font-size: 10px;
        border: none;
        border-radius: 12px;
        padding: 0 16px;
    }
    QPushButton:hover {
        background-color: #475569;
    }
"""

PRIMARY_BTN_STYLE = """
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #0891b2, stop:1 #06b6d4);
        color: white;
        font-weight: 700;
        font-size: 11px;
        border: none;
        border-radius: 6px;
        padding: 8px 20px;
        letter-spacing: 1px;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #06b6d4, stop:1 #22d3ee);
    }
    QPushButton:pressed {
        background: #0891b2;
    }
    QPushButton:disabled {
        background-color: #334155;
        color: #64748b;
    }
"""

AMBER_BTN_STYLE = """
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #d97706, stop:1 #f59e0b);
        color: #0a0e1a;
        font-weight: 700;
        font-size: 11px;
        border: none;
        border-radius: 6px;
        padding: 8px 20px;
        letter-spacing: 1px;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #f59e0b, stop:1 #fbbf24);
    }
    QPushButton:pressed {
        background: #d97706;
    }
    QPushButton:disabled {
        background-color: #334155;
        color: #64748b;
    }
"""

PURPLE_BTN_STYLE = """
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #6d28d9, stop:1 #7c3aed);
        color: white;
        font-weight: 700;
        font-size: 11px;
        border: none;
        border-radius: 6px;
        padding: 8px 20px;
        letter-spacing: 1px;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #7c3aed, stop:1 #8b5cf6);
    }
    QPushButton:pressed {
        background: #6d28d9;
    }
"""

VALUE_LABEL_STYLE = """
    color: #67e8f9;
    font-size: 11px;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    background-color: transparent;
    border: none;
"""

PURPLE_VALUE_STYLE = """
    color: #ddd6fe;
    font-size: 11px;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    background-color: transparent;
    border: none;
"""

LABEL_STYLE = """
    color: #e2e8f0;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    background-color: transparent;
    border: none;
"""

PROGRESS_STYLE = """
    QProgressBar {
        background-color: #1e293b;
        border: none;
        border-radius: 4px;
        height: 12px;
    }
    QProgressBar::chunk {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #d97706, stop:1 #f59e0b);
        border-radius: 4px;
    }
    QProgressBar {
        color: #e2e8f0;
        font-size: 9px;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 700;
        text-align: center;
    }
"""


def create_settings_view(app):
    widget = QWidget()
    widget.setStyleSheet("background-color: #0a0e1a;")
    layout = QHBoxLayout()
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(20)

    left_panel = QWidget()
    left_panel.setStyleSheet("background-color: transparent;")
    left_panel.setMaximumWidth(600)
    left_layout = QVBoxLayout()
    left_layout.setContentsMargins(0, 0, 0, 0)
    left_layout.setSpacing(16)

    title_row = QHBoxLayout()
    title_icon = QLabel("\u2699")
    title_icon.setStyleSheet("color: #06b6d4; font-size: 18px;")
    title_row.addWidget(title_icon)
    title = QLabel("SETTINGS")
    title.setStyleSheet(SECTION_TITLE_STYLE)
    title_row.addWidget(title)
    title_row.addStretch()
    left_layout.addLayout(title_row)

    pid_card = QFrame()
    pid_card.setStyleSheet(CARD_STYLE)
    pid_layout = QVBoxLayout()
    pid_layout.setContentsMargins(0, 0, 0, 0)
    pid_layout.addWidget(_create_pid_group(app))
    pid_card.setLayout(pid_layout)
    left_layout.addWidget(pid_card)

    ota_card = QFrame()
    ota_card.setStyleSheet(CARD_STYLE)
    ota_layout = QVBoxLayout()
    ota_layout.setContentsMargins(0, 0, 0, 0)
    ota_layout.addWidget(_create_ota_group(app))
    ota_card.setLayout(ota_layout)
    left_layout.addWidget(ota_card)

    cam_card = QFrame()
    cam_card.setStyleSheet(CARD_STYLE)
    cam_layout = QVBoxLayout()
    cam_layout.setContentsMargins(0, 0, 0, 0)
    cam_layout.addWidget(_create_camera_group(app))
    cam_card.setLayout(cam_layout)
    left_layout.addWidget(cam_card)

    left_layout.addStretch()
    left_panel.setLayout(left_layout)
    layout.addWidget(left_panel, 1)

    right_panel = QWidget()
    right_panel.setStyleSheet("background-color: transparent;")
    right_panel.setFixedWidth(400)
    right_layout = QVBoxLayout()
    right_layout.setContentsMargins(0, 0, 0, 0)
    right_layout.setSpacing(16)

    cloud_card = QFrame()
    cloud_card.setStyleSheet(CARD_STYLE)
    cloud_layout = QVBoxLayout()
    cloud_layout.setContentsMargins(0, 0, 0, 0)
    cloud_layout.addWidget(_create_cloud_group(app))
    cloud_card.setLayout(cloud_layout)
    right_layout.addWidget(cloud_card)

    follow_card = QFrame()
    follow_card.setStyleSheet(CARD_STYLE)
    follow_layout = QVBoxLayout()
    follow_layout.setContentsMargins(0, 0, 0, 0)
    follow_layout.addWidget(_create_follow_group(app))
    follow_card.setLayout(follow_layout)
    right_layout.addWidget(follow_card)

    right_layout.addStretch()
    right_panel.setLayout(right_layout)
    layout.addWidget(right_panel)

    widget.setLayout(layout)
    return widget


def _create_pid_group(app):
    group = QGroupBox("PID STRAIGHT")
    group.setStyleSheet(GROUP_BOX_STYLE)
    layout = QVBoxLayout()
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(10)

    toggle_row = QHBoxLayout()
    app._pid_toggle = QPushButton("OFF")
    app._pid_toggle.setCheckable(True)
    app._pid_toggle.setFixedHeight(28)
    app._pid_toggle.setStyleSheet(TOGGLE_OFF_STYLE)
    app._pid_toggle.clicked.connect(lambda: _toggle_pid(app))
    toggle_row.addWidget(app._pid_toggle)
    toggle_row.addStretch()
    layout.addLayout(toggle_row)

    kp_row = QHBoxLayout()
    kp_row.setSpacing(10)
    kp_label = QLabel("Kp")
    kp_label.setFixedWidth(36)
    kp_label.setStyleSheet(LABEL_STYLE)
    kp_row.addWidget(kp_label)
    app._kp_slider = QSlider(Qt.Orientation.Horizontal)
    app._kp_slider.setRange(0, 100)
    app._kp_slider.setValue(20)
    app._kp_slider.setStyleSheet(SLIDER_STYLE)
    app._kp_slider.valueChanged.connect(lambda v: _on_pid_change(app))
    kp_row.addWidget(app._kp_slider, 1)
    app._kp_label = QLabel("20")
    app._kp_label.setStyleSheet(VALUE_LABEL_STYLE)
    app._kp_label.setFixedWidth(40)
    app._kp_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    kp_row.addWidget(app._kp_label)
    layout.addLayout(kp_row)

    ki_row = QHBoxLayout()
    ki_row.setSpacing(10)
    ki_label = QLabel("Ki")
    ki_label.setFixedWidth(36)
    ki_label.setStyleSheet(LABEL_STYLE)
    ki_row.addWidget(ki_label)
    app._ki_slider = QSlider(Qt.Orientation.Horizontal)
    app._ki_slider.setRange(0, 100)
    app._ki_slider.setValue(5)
    app._ki_slider.setStyleSheet(SLIDER_STYLE)
    app._ki_slider.valueChanged.connect(lambda v: _on_pid_change(app))
    ki_row.addWidget(app._ki_slider, 1)
    app._ki_label = QLabel("5")
    app._ki_label.setStyleSheet(VALUE_LABEL_STYLE)
    app._ki_label.setFixedWidth(40)
    app._ki_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    ki_row.addWidget(app._ki_label)
    layout.addLayout(ki_row)

    kd_row = QHBoxLayout()
    kd_row.setSpacing(10)
    kd_label = QLabel("Kd")
    kd_label.setFixedWidth(36)
    kd_label.setStyleSheet(LABEL_STYLE)
    kd_row.addWidget(kd_label)
    app._kd_slider = QSlider(Qt.Orientation.Horizontal)
    app._kd_slider.setRange(0, 100)
    app._kd_slider.setValue(10)
    app._kd_slider.setStyleSheet(SLIDER_STYLE)
    app._kd_slider.valueChanged.connect(lambda v: _on_pid_change(app))
    kd_row.addWidget(app._kd_slider, 1)
    app._kd_label = QLabel("10")
    app._kd_label.setStyleSheet(VALUE_LABEL_STYLE)
    app._kd_label.setFixedWidth(40)
    app._kd_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    kd_row.addWidget(app._kd_label)
    layout.addLayout(kd_row)

    bias_row = QHBoxLayout()
    bias_row.setSpacing(10)
    bias_label = QLabel("Bias")
    bias_label.setFixedWidth(36)
    bias_label.setStyleSheet(LABEL_STYLE)
    bias_row.addWidget(bias_label)
    app._pid_bias_slider = QSlider(Qt.Orientation.Horizontal)
    app._pid_bias_slider.setRange(-50, 50)
    app._pid_bias_slider.setValue(0)
    app._pid_bias_slider.setStyleSheet(SLIDER_STYLE)
    app._pid_bias_slider.valueChanged.connect(lambda v: _on_pid_change(app))
    bias_row.addWidget(app._pid_bias_slider, 1)
    app._pid_bias_label = QLabel("0")
    app._pid_bias_label.setStyleSheet(VALUE_LABEL_STYLE)
    app._pid_bias_label.setFixedWidth(40)
    app._pid_bias_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    bias_row.addWidget(app._pid_bias_label)
    layout.addLayout(bias_row)

    group.setLayout(layout)
    return group


def _create_camera_group(app):
    group = QGroupBox("CAMERA")
    group.setStyleSheet(GROUP_BOX_STYLE)
    layout = QVBoxLayout()
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(10)

    led_row = QHBoxLayout()
    led_row.setSpacing(10)
    led_label = QLabel("LED")
    led_label.setFixedWidth(36)
    led_label.setStyleSheet(LABEL_STYLE)
    led_row.addWidget(led_label)

    app._led_slider = QSlider(Qt.Orientation.Horizontal)
    app._led_slider.setRange(0, 255)
    app._led_slider.setValue(0)
    app._led_slider.setFixedWidth(140)
    app._led_slider.setStyleSheet(AMBER_SLIDER_STYLE)
    app._led_slider.valueChanged.connect(lambda v: _on_led_change(app, v))
    led_row.addWidget(app._led_slider)

    app._led_label = QLabel("0")
    app._led_label.setStyleSheet("""
        color: #fbbf24;
        font-size: 12px;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 700;
        background-color: transparent;
        border: none;
    """)
    app._led_label.setFixedWidth(40)
    app._led_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    led_row.addWidget(app._led_label)

    app._led_toggle_btn = QPushButton("OFF")
    app._led_toggle_btn.setCheckable(True)
    app._led_toggle_btn.setFixedWidth(44)
    app._led_toggle_btn.setFixedHeight(24)
    app._led_toggle_btn.setStyleSheet(TOGGLE_OFF_STYLE)
    app._led_toggle_btn.clicked.connect(lambda: _toggle_led(app))
    led_row.addWidget(app._led_toggle_btn)

    layout.addLayout(led_row)
    group.setLayout(layout)
    return group


def _create_cloud_group(app):
    group = QGroupBox("CLOUD")
    group.setStyleSheet(GROUP_BOX_STYLE)
    layout = QVBoxLayout()
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(10)

    btn_row = QHBoxLayout()
    btn_row.setSpacing(10)

    app._cloud_send_btn = QPushButton("SEND")
    app._cloud_send_btn.setFixedHeight(36)
    app._cloud_send_btn.setStyleSheet(PURPLE_BTN_STYLE)
    app._cloud_send_btn.clicked.connect(app._manual_send_to_cloud)
    btn_row.addWidget(app._cloud_send_btn, 1)

    app._toggle_view_btn = QPushButton("DATA")
    app._toggle_view_btn.setFixedHeight(36)
    app._toggle_view_btn.setCheckable(True)
    app._toggle_view_btn.setStyleSheet("""
        QPushButton {
            background-color: #1e293b;
            border: 1px solid #334155;
            color: #06b6d4;
            font-weight: 700;
            font-size: 11px;
            padding: 4px 16px;
            border-radius: 6px;
            letter-spacing: 1px;
        }
        QPushButton:hover {
            background-color: #334155;
            border-color: #06b6d4;
        }
        QPushButton:checked {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #0891b2, stop:1 #06b6d4);
            color: white;
            border: none;
        }
    """)
    app._toggle_view_btn.clicked.connect(app._toggle_view)
    btn_row.addWidget(app._toggle_view_btn, 1)

    layout.addLayout(btn_row)
    group.setLayout(layout)
    return group


def _create_follow_group(app):
    group = QGroupBox("FOLLOW MODE")
    group.setStyleSheet("""
        QGroupBox {
            background-color: transparent;
            border: 1px solid rgba(124, 58, 237, 0.3);
            border-radius: 8px;
            padding: 16px 12px 12px 12px;
            margin-top: 16px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 14px;
            padding: 0 8px;
            color: #a78bfa;
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 2px;
        }
    """)
    layout = QVBoxLayout()
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(10)

    kp_row = QHBoxLayout()
    kp_row.setSpacing(10)
    kp_label = QLabel("kp")
    kp_label.setFixedWidth(36)
    kp_label.setStyleSheet(LABEL_STYLE)
    kp_row.addWidget(kp_label)
    app._follow_kp_slider = QSlider(Qt.Orientation.Horizontal)
    app._follow_kp_slider.setRange(0, 1500)
    app._follow_kp_slider.setValue(700)
    app._follow_kp_slider.setStyleSheet(PURPLE_SLIDER_STYLE)
    app._follow_kp_slider.valueChanged.connect(lambda v: _on_follow_param_change(app))
    kp_row.addWidget(app._follow_kp_slider, 1)
    app._follow_kp_label = QLabel("70.0")
    app._follow_kp_label.setStyleSheet(PURPLE_VALUE_STYLE)
    app._follow_kp_label.setFixedWidth(40)
    app._follow_kp_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    kp_row.addWidget(app._follow_kp_label)
    layout.addLayout(kp_row)

    ki_row = QHBoxLayout()
    ki_row.setSpacing(10)
    ki_label = QLabel("ki")
    ki_label.setFixedWidth(36)
    ki_label.setStyleSheet(LABEL_STYLE)
    ki_row.addWidget(ki_label)
    app._follow_ki_slider = QSlider(Qt.Orientation.Horizontal)
    app._follow_ki_slider.setRange(0, 20)
    app._follow_ki_slider.setValue(4)
    app._follow_ki_slider.setStyleSheet(PURPLE_SLIDER_STYLE)
    app._follow_ki_slider.valueChanged.connect(lambda v: _on_follow_param_change(app))
    ki_row.addWidget(app._follow_ki_slider, 1)
    app._follow_ki_label = QLabel("0.4")
    app._follow_ki_label.setStyleSheet(PURPLE_VALUE_STYLE)
    app._follow_ki_label.setFixedWidth(40)
    app._follow_ki_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    ki_row.addWidget(app._follow_ki_label)
    layout.addLayout(ki_row)

    kd_row = QHBoxLayout()
    kd_row.setSpacing(10)
    kd_label = QLabel("kd")
    kd_label.setFixedWidth(36)
    kd_label.setStyleSheet(LABEL_STYLE)
    kd_row.addWidget(kd_label)
    app._follow_kd_slider = QSlider(Qt.Orientation.Horizontal)
    app._follow_kd_slider.setRange(0, 300)
    app._follow_kd_slider.setValue(100)
    app._follow_kd_slider.setStyleSheet(PURPLE_SLIDER_STYLE)
    app._follow_kd_slider.valueChanged.connect(lambda v: _on_follow_param_change(app))
    kd_row.addWidget(app._follow_kd_slider, 1)
    app._follow_kd_label = QLabel("10.0")
    app._follow_kd_label.setStyleSheet(PURPLE_VALUE_STYLE)
    app._follow_kd_label.setFixedWidth(40)
    app._follow_kd_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    kd_row.addWidget(app._follow_kd_label)
    layout.addLayout(kd_row)

    cam_offset_row = QHBoxLayout()
    cam_offset_row.setSpacing(10)
    cam_offset_label = QLabel("CAM")
    cam_offset_label.setFixedWidth(36)
    cam_offset_label.setStyleSheet(LABEL_STYLE)
    cam_offset_row.addWidget(cam_offset_label)
    app._follow_cam_offset_slider = QSlider(Qt.Orientation.Horizontal)
    app._follow_cam_offset_slider.setRange(-45, 45)
    app._follow_cam_offset_slider.setValue(0)
    app._follow_cam_offset_slider.setStyleSheet(PURPLE_SLIDER_STYLE)
    app._follow_cam_offset_slider.valueChanged.connect(lambda v: _on_follow_param_change(app))
    cam_offset_row.addWidget(app._follow_cam_offset_slider, 1)
    app._follow_cam_offset_label = QLabel("0")
    app._follow_cam_offset_label.setStyleSheet(PURPLE_VALUE_STYLE)
    app._follow_cam_offset_label.setFixedWidth(40)
    app._follow_cam_offset_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    cam_offset_row.addWidget(app._follow_cam_offset_label)
    layout.addLayout(cam_offset_row)

    group.setLayout(layout)
    return group


def _create_ota_group(app):
    OTA_KEY = "shodai-haru-2026-8-25"

    group = QGroupBox("OTA FIRMWARE")
    group.setStyleSheet("""
        QGroupBox {
            background-color: transparent;
            border: 1px solid rgba(245, 158, 11, 0.3);
            border-radius: 8px;
            padding: 16px 12px 12px 12px;
            margin-top: 16px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 14px;
            padding: 0 8px;
            color: #fbbf24;
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 2px;
        }
    """)
    layout = QVBoxLayout()
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(10)

    file_row = QHBoxLayout()
    file_row.setSpacing(10)
    app._ota_file_btn = QPushButton("SELECT")
    app._ota_file_btn.setFixedHeight(32)
    app._ota_file_btn.setStyleSheet(AMBER_BTN_STYLE)
    app._ota_file_btn.clicked.connect(lambda: _select_ota_file(app))
    file_row.addWidget(app._ota_file_btn)

    app._ota_file_label = QLabel("No file selected")
    app._ota_file_label.setStyleSheet("color: #94a3b8; font-size: 11px; background-color: transparent; border: none;")
    app._ota_file_label.setWordWrap(True)
    file_row.addWidget(app._ota_file_label, 1)
    layout.addLayout(file_row)

    ver_row = QHBoxLayout()
    ver_row.setSpacing(10)
    ver_label = QLabel("VER")
    ver_label.setFixedWidth(36)
    ver_label.setStyleSheet(LABEL_STYLE)
    ver_row.addWidget(ver_label)
    app._ota_ver_input = QLineEdit()
    app._ota_ver_input.setPlaceholderText("1.0.0")
    app._ota_ver_input.setStyleSheet(INPUT_STYLE)
    ver_row.addWidget(app._ota_ver_input)
    layout.addLayout(ver_row)

    info_row = QHBoxLayout()
    info_row.setSpacing(10)
    info_label = QLabel("INFO")
    info_label.setFixedWidth(36)
    info_label.setStyleSheet(LABEL_STYLE)
    info_row.addWidget(info_label)
    app._ota_info_input = QLineEdit()
    app._ota_info_input.setPlaceholderText("Release notes")
    app._ota_info_input.setStyleSheet(INPUT_STYLE)
    info_row.addWidget(app._ota_info_input)
    layout.addLayout(info_row)

    url_row = QHBoxLayout()
    url_row.setSpacing(10)
    url_label = QLabel("URL")
    url_label.setFixedWidth(36)
    url_label.setStyleSheet(LABEL_STYLE)
    url_row.addWidget(url_label)
    app._ota_url_input = QLineEdit()
    app._ota_url_input.setPlaceholderText("http://rpi5.local/api/v1")
    app._ota_url_input.setText(app._config.get("ota_server_url", ""))
    app._ota_url_input.setStyleSheet(INPUT_STYLE)
    url_row.addWidget(app._ota_url_input)
    layout.addLayout(url_row)

    app._ota_upload_btn = QPushButton("UPLOAD")
    app._ota_upload_btn.setFixedHeight(36)
    app._ota_upload_btn.setVisible(False)
    app._ota_upload_btn.setStyleSheet(AMBER_BTN_STYLE)
    app._ota_upload_btn.clicked.connect(lambda: _upload_ota_file(app))
    layout.addWidget(app._ota_upload_btn)

    app._ota_progress = QProgressBar()
    app._ota_progress.setFixedHeight(8)
    app._ota_progress.setTextVisible(True)
    app._ota_progress.setStyleSheet(PROGRESS_STYLE)
    app._ota_progress.setValue(0)
    layout.addWidget(app._ota_progress)

    group.setLayout(layout)
    return group


def _toggle_pid(app):
    checked = app._pid_toggle.isChecked()
    app._pid_toggle.setText("ON" if checked else "OFF")
    app._pid_toggle.setStyleSheet(TOGGLE_ON_STYLE if checked else TOGGLE_OFF_STYLE)
    app._add_log("PID", f"PID straight {'enabled' if checked else 'disabled'}")
    app._schedule_pid_apply()


def _on_pid_change(app):
    kp = app._kp_slider.value()
    ki = app._ki_slider.value()
    kd = app._kd_slider.value()
    bias = app._pid_bias_slider.value()
    app._kp_label.setText(str(kp))
    app._ki_label.setText(str(ki))
    app._kd_label.setText(str(kd))
    app._pid_bias_label.setText(str(bias))
    app._schedule_pid_apply()


def _on_led_change(app, value):
    app._led_label.setText(str(value))
    app._led_toggle_btn.setChecked(value > 0)
    app._led_toggle_btn.setText("ON" if value > 0 else "OFF")
    app._led_toggle_btn.setStyleSheet(TOGGLE_ON_STYLE if value > 0 else TOGGLE_OFF_STYLE)
    app._schedule_led_apply()


def _toggle_led(app):
    checked = app._led_toggle_btn.isChecked()
    value = app._led_slider.value() if checked and app._led_slider.value() > 0 else (255 if checked else 0)
    app._led_toggle_btn.setText("ON" if checked else "OFF")
    app._led_toggle_btn.setStyleSheet(TOGGLE_ON_STYLE if checked else TOGGLE_OFF_STYLE)
    app._led_slider.blockSignals(True)
    app._led_slider.setValue(value)
    app._led_slider.blockSignals(False)
    app._led_label.setText(str(value))
    app._schedule_led_apply()


def _on_follow_param_change(app):
    kp_lin = app._follow_kp_slider.value() / 10.0
    ki_lin = app._follow_ki_slider.value() / 10.0
    kd_lin = app._follow_kd_slider.value() / 10.0
    cam_offset = app._follow_cam_offset_slider.value()

    app._follow_kp_label.setText(f"{kp_lin:.1f}")
    app._follow_ki_label.setText(f"{ki_lin:.1f}")
    app._follow_kd_label.setText(f"{kd_lin:.1f}")
    app._follow_cam_offset_label.setText(f"{cam_offset}")

    if hasattr(app, '_detection_mgr') and app._detection_mgr._follow_controller:
        app._detection_mgr._follow_controller.config.kp_lin = kp_lin
        app._detection_mgr._follow_controller.config.ki_lin = ki_lin
        app._detection_mgr._follow_controller.config.kd_lin = kd_lin
        app._detection_mgr._follow_controller.config.camera_yaw_offset = cam_offset


def _select_ota_file(app):
    file_path, _ = QFileDialog.getOpenFileName(
        app, "Select Firmware", "", "Firmware Files (*.bin);;All Files (*)"
    )
    if file_path:
        app._ota_file_path = file_path
        fname = file_path.split("/")[-1].split("\\")[-1]
        size_kb = len(open(file_path, "rb").read()) / 1024
        app._ota_file_label.setText(f"{fname} ({size_kb:.1f} KB)")
        app._ota_file_label.setStyleSheet("color: #e2e8f0; font-size: 11px; font-family: 'JetBrains Mono', monospace; background-color: transparent; border: none;")
        app._ota_upload_btn.setVisible(True)


def _upload_ota_file(app):
    import os
    from cloud_worker import CloudWorker

    if not hasattr(app, '_ota_file_path'):
        return

    file_path = app._ota_file_path
    ext = os.path.splitext(file_path)[1].lower()
    if ext != ".bin":
        QMessageBox.warning(app, "File Error", "Only .bin files are allowed.")
        return

    base_url = app._ota_url_input.text().strip()
    if not base_url:
        QMessageBox.warning(app, "URL Error", "Please enter server URL.")
        return

    ver = app._ota_ver_input.text().strip()
    if not ver:
        QMessageBox.warning(app, "Version Error", "Please enter version number.")
        return

    info = app._ota_info_input.text().strip()

    upload_url = base_url.rstrip("/") + "/firmware"
    size = os.path.getsize(file_path)
    app._add_log("OTA", f"Uploading firmware v{ver} ({size} bytes)")
    app._add_log("OTA", f"URL: {upload_url}")

    app._ota_upload_btn.setEnabled(False)
    app._ota_progress.setValue(0)

    form_data = {"version": ver}
    if info:
        form_data["release_notes"] = info

    app._ota_worker = CloudWorker("UPLOAD", upload_url, file_path=file_path, data=form_data)
    app._ota_worker.progress.connect(lambda p: app._ota_progress.setValue(p))
    app._ota_worker.result.connect(lambda r: _on_ota_upload_done(app, r))
    app._ota_worker.error.connect(lambda e: _on_ota_upload_error(app, e))
    app._ota_worker.start()


def _on_ota_upload_done(app, result):
    app._ota_upload_btn.setEnabled(True)
    app._ota_progress.setValue(100)

    if isinstance(result, dict) and result.get("error"):
        error_msg = result["error"]
        if isinstance(error_msg, dict):
            error_msg = error_msg.get("message", str(error_msg))
        app._add_log("OTA", f"Upload failed: {error_msg}")
        QMessageBox.warning(app, "Upload Error", str(error_msg))
        return

    if isinstance(result, dict) and result.get("version"):
        app._add_log("OTA", f"Upload successful - v{result['version']}")
        app._ota_file_label.setText("No file selected")
        app._ota_file_label.setStyleSheet("color: #64748b; font-size: 11px; background-color: transparent; border: none;")
        app._ota_upload_btn.setVisible(False)
        if hasattr(app, '_ota_file_path'):
            del app._ota_file_path
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1000, lambda: _reset_ota_ui(app))
    else:
        msg = result.get("message", str(result)) if isinstance(result, dict) else str(result)
        app._add_log("OTA", f"Upload response: {msg}")
        QMessageBox.information(app, "Upload Result", str(msg))


def _reset_ota_ui(app):
    app._ota_upload_btn.setVisible(True)
    app._ota_progress.setValue(0)


def _on_ota_upload_error(app, error):
    app._ota_upload_btn.setEnabled(True)
    app._ota_progress.setValue(0)
    app._add_log("OTA", f"Upload error: {error}")
    QMessageBox.warning(app, "Upload Error", error)
