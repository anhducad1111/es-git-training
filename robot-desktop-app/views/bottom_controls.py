from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QSlider, QVBoxLayout, QWidget
)


def create_bottom_controls(app):
    widget = QWidget()
    widget.setFixedHeight(80)
    widget.setStyleSheet("""
        background-color: #0f172a;
        border-top: 1px solid #1e293b;
    """)
    layout = QHBoxLayout()
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(6)

    speed_group = QGroupBox("SPEED")
    speed_group.setStyleSheet("""
        background-color: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 6px;
        padding: 6px;
    """)
    speed_layout = QHBoxLayout()
    speed_layout.setContentsMargins(6, 2, 6, 2)
    speed_layout.setSpacing(4)

    app._speed_slider = QSlider(Qt.Orientation.Horizontal)
    app._speed_slider.setRange(180, 255)
    app._speed_slider.setValue(app._current_speed)
    app._speed_slider.setFixedWidth(60)
    app._speed_slider.valueChanged.connect(lambda v: _on_speed_change(app, v))
    speed_layout.addWidget(app._speed_slider)

    app._speed_label = QLabel(f"{app._current_speed}")
    app._speed_label.setStyleSheet("""
        color: #06b6d4;
        font-size: 11px;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
    """)
    app._speed_label.setFixedWidth(35)
    speed_layout.addWidget(app._speed_label)

    speed_group.setLayout(speed_layout)
    layout.addWidget(speed_group)

    brake_group = QGroupBox("BRAKE")
    brake_group.setStyleSheet("""
        background-color: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 6px;
        padding: 6px;
    """)
    brake_layout = QHBoxLayout()
    brake_layout.setContentsMargins(6, 2, 6, 2)
    brake_layout.setSpacing(6)

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
            padding: 2px 8px;
        }
        QPushButton:!checked {
            background-color: #475569;
        }
    """)
    app._brake_toggle.clicked.connect(lambda: _toggle_brake(app))
    brake_layout.addWidget(app._brake_toggle)

    brake_group.setLayout(brake_layout)
    layout.addWidget(brake_group)

    layout.addSpacing(6)

    gimbal_group = QGroupBox("GIMBAL")
    gimbal_group.setStyleSheet("""
        background-color: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 6px;
        padding: 6px;
    """)
    gimbal_layout = QHBoxLayout()
    gimbal_layout.setContentsMargins(6, 2, 6, 2)
    gimbal_layout.setSpacing(6)

    pan_label = QLabel("PAN")
    pan_label.setStyleSheet("color: #475569; font-size: 8px; letter-spacing: 1px;")
    gimbal_layout.addWidget(pan_label)

    app._gimbal_pan_label = QLabel(f"{app._gimbal_pan}°")
    app._gimbal_pan_label.setStyleSheet("""
        color: #e2e8f0;
        font-size: 10px;
        font-family: 'JetBrains Mono', monospace;
    """)
    gimbal_layout.addWidget(app._gimbal_pan_label)

    tilt_label = QLabel("TILT")
    tilt_label.setStyleSheet("color: #475569; font-size: 8px; letter-spacing: 1px;")
    gimbal_layout.addWidget(tilt_label)

    app._gimbal_tilt_label = QLabel(f"{app._gimbal_tilt}°")
    app._gimbal_tilt_label.setStyleSheet("""
        color: #e2e8f0;
        font-size: 10px;
        font-family: 'JetBrains Mono', monospace;
    """)
    gimbal_layout.addWidget(app._gimbal_tilt_label)

    center_btn = QPushButton("C")
    center_btn.setFixedSize(28, 28)
    center_btn.setStyleSheet("""
        QPushButton {
            background-color: #1e293b;
            border: 1px solid #334155;
            color: #06b6d4;
            font-weight: 700;
            font-size: 10px;
            border-radius: 14px;
        }
        QPushButton:hover {
            background-color: #334155;
        }
    """)
    center_btn.clicked.connect(app._center_gimbal)
    gimbal_layout.addWidget(center_btn)

    app._mouse_gimbal_btn = QPushButton("MOUSE")
    app._mouse_gimbal_btn.setFixedHeight(28)
    app._mouse_gimbal_btn.setCheckable(True)
    app._mouse_gimbal_btn.setChecked(True)
    app._mouse_gimbal_btn.setStyleSheet("""
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
    app._mouse_gimbal_btn.clicked.connect(lambda: _toggle_mouse_gimbal(app))
    gimbal_layout.addWidget(app._mouse_gimbal_btn)

    gimbal_group.setLayout(gimbal_layout)
    layout.addWidget(gimbal_group)

    layout.addSpacing(6)

    snapshot_btn = QPushButton("SNAP")
    snapshot_btn.setFixedHeight(28)
    snapshot_btn.setStyleSheet("""
        QPushButton {
            background-color: rgba(59, 130, 246, 0.15);
            border: 1px solid rgba(59, 130, 246, 0.3);
            color: #3b82f6;
            font-weight: 600;
            font-size: 10px;
            padding: 4px 12px;
            letter-spacing: 1px;
        }
        QPushButton:hover {
            background-color: rgba(59, 130, 246, 0.25);
        }
    """)
    snapshot_btn.clicked.connect(app._take_snapshot)
    layout.addWidget(snapshot_btn)

    app._super_res_check = QCheckBox("SR")
    app._super_res_check.setStyleSheet("color: #64748b; font-size: 9px;")
    layout.addWidget(app._super_res_check)

    layout.addSpacing(6)

    app._detect_combo = QComboBox()
    app._detect_combo.addItems(["HOG", "YOLO"])
    app._detect_combo.setFixedHeight(26)
    app._detect_combo.setFixedWidth(55)
    app._detect_combo.setStyleSheet("""
        QComboBox {
            background-color: #1e293b;
            border: 1px solid #334155;
            color: #e2e8f0;
            font-size: 10px;
            padding: 2px 6px;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox::down-arrow {
            image: none;
        }
        QComboBox QAbstractItemView {
            background-color: #1e293b;
            color: #e2e8f0;
            selection-background-color: #06b6d4;
        }
    """)
    app._detect_combo.currentTextChanged.connect(lambda t: _on_detect_method_change(app, t))
    layout.addWidget(app._detect_combo)

    app._hog_btn = QPushButton("DETECT")
    app._hog_btn.setFixedHeight(28)
    app._hog_btn.setCheckable(True)
    app._hog_btn.setStyleSheet("""
        QPushButton {
            background-color: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: #10b981;
            font-weight: 600;
            font-size: 10px;
            padding: 4px 12px;
            letter-spacing: 1px;
        }
        QPushButton:hover {
            background-color: rgba(16, 185, 129, 0.25);
        }
        QPushButton:checked {
            background-color: #10b981;
            color: #0a0e1a;
        }
    """)
    app._hog_btn.clicked.connect(app._toggle_hog_detection)
    layout.addWidget(app._hog_btn)

    layout.addStretch()

    widget.setLayout(layout)
    return widget


def _on_speed_change(app, value):
    app._global_speed = value
    app._speed_label.setText(f"{value}")
    app._send_command(f"speed:{value}")


def _toggle_brake(app):
    checked = app._brake_toggle.isChecked()
    app._brake_toggle.setText("ON" if checked else "OFF")
    if hasattr(app, '_esp32_api'):
        app._esp32_api.set_brake(checked)
    app._add_log("SAFETY", f"Auto-brake {'enabled' if checked else 'disabled'}")


def _toggle_mouse_gimbal(app):
    checked = app._mouse_gimbal_btn.isChecked()
    if hasattr(app, '_video_canvas'):
        app._video_canvas._mouse_gimbal_enabled = checked
    app._add_log("GIMBAL", f"Mouse gimbal {'enabled' if checked else 'disabled'}")


def _on_detect_method_change(app, method):
    if hasattr(app, '_detection_method'):
        app._detection_method = method
        app._add_log("DETECT", f"Detection method: {method}")
