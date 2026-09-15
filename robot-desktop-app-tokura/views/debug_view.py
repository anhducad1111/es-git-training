"""実機キャリブレーション用のデバッグタブ。開発中のみ使う道具であり、
恒久機能ではない。ロジックはcalibration.pyに閉じ込めてあるので、
不要になったらこのファイルとcalibration.pyを削除し、app.py/
views/sidebar.pyの数行(このビューを参照する箇所)を取り除くだけで
まるごと撤去できる。
"""

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import (
    QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QPushButton, QSlider, QTabWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget
)

from calibration import CalibrationLogger, GyroYawIntegrator
from follow_controller import FollowConfig

TABLE_STYLE = """
    QTableWidget {
        background-color: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 6px;
        color: #94a3b8;
        font-size: 10px;
        font-family: 'JetBrains Mono', monospace;
    }
    QTableWidget::item { padding: 4px; }
    QHeaderView::section {
        background-color: #1e293b;
        color: #64748b;
        border: none;
        border-bottom: 1px solid #1e293b;
        padding: 4px;
        font-size: 9px;
        letter-spacing: 1px;
    }
"""


def create_debug_view(app):
    """DEBUGボタン1つで切り替えられる2タブ構成。サイドバー/app.py側の配線は
    このビュー全体を1つのQWidgetとして_center_stackに載せる従来通りのままでよい
    (タブの切替はこのウィジェット内部で完結する)。"""
    app._calibration_logger = CalibrationLogger()

    tabs = QTabWidget()
    tabs.addTab(_create_calibration_tab(app), "CALIBRATION")
    tabs.addTab(_create_follow_tuning_tab(app), "FOLLOW TUNING")
    return tabs


def _create_calibration_tab(app):
    widget = QWidget()
    layout = QVBoxLayout()
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(16)

    title = QLabel("DEBUG / CALIBRATION")
    title.setStyleSheet("color: #22d3ee; font-size: 13px; font-weight: 700; letter-spacing: 2px;")
    layout.addWidget(title)

    panels_row = QHBoxLayout()
    panels_row.addWidget(_create_spin_test_panel(app))
    panels_row.addWidget(_create_forward_test_panel(app))
    layout.addLayout(panels_row)

    layout.addWidget(_create_history_table(app))

    widget.setLayout(layout)
    return widget


def _create_spin_test_panel(app):
    box = QGroupBox("旋回テスト (drive:0,w を連続送信)")
    form = QVBoxLayout()

    w_row = QHBoxLayout()
    w_row.addWidget(QLabel("w (旋回PWM, 例 190=右 / -190=左):"))
    app._debug_spin_w_input = QLineEdit("190")
    w_row.addWidget(app._debug_spin_w_input)
    form.addLayout(w_row)

    dur_row = QHBoxLayout()
    dur_row.addWidget(QLabel("実行時間(秒):"))
    app._debug_spin_duration_input = QLineEdit("1.0")
    dur_row.addWidget(app._debug_spin_duration_input)
    form.addLayout(dur_row)

    run_btn = QPushButton("RUN")
    run_btn.clicked.connect(lambda: _run_spin_test(app))
    form.addWidget(run_btn)

    gyro_row = QHBoxLayout()
    gyro_row.addWidget(QLabel("ジャイロ計測値:"))
    app._debug_spin_gyro_label = QLabel("-")
    gyro_row.addWidget(app._debug_spin_gyro_label)
    form.addLayout(gyro_row)

    manual_row = QHBoxLayout()
    manual_row.addWidget(QLabel("手動入力(任意, 優先):"))
    app._debug_spin_manual_input = QLineEdit("")
    app._debug_spin_manual_input.setPlaceholderText("度")
    manual_row.addWidget(app._debug_spin_manual_input)
    form.addLayout(manual_row)

    save_btn = QPushButton("SAVE")
    save_btn.clicked.connect(lambda: _save_spin_result(app))
    form.addWidget(save_btn)

    box.setLayout(form)
    return box


def _create_forward_test_panel(app):
    box = QGroupBox("前進テスト (speed:N + forward/backward)")
    form = QVBoxLayout()

    pwm_row = QHBoxLayout()
    pwm_row.addWidget(QLabel("PWM (例 200=前進 / -150=後退):"))
    app._debug_forward_pwm_input = QLineEdit("200")
    pwm_row.addWidget(app._debug_forward_pwm_input)
    form.addLayout(pwm_row)

    dur_row = QHBoxLayout()
    dur_row.addWidget(QLabel("実行時間(秒):"))
    app._debug_forward_duration_input = QLineEdit("1.0")
    dur_row.addWidget(app._debug_forward_duration_input)
    form.addLayout(dur_row)

    run_btn = QPushButton("RUN")
    run_btn.clicked.connect(lambda: _run_forward_test(app))
    form.addWidget(run_btn)

    dist_row = QHBoxLayout()
    dist_row.addWidget(QLabel("実測距離(m):"))
    app._debug_forward_distance_input = QLineEdit("")
    app._debug_forward_distance_input.setPlaceholderText("m")
    dist_row.addWidget(app._debug_forward_distance_input)
    form.addLayout(dist_row)

    save_btn = QPushButton("SAVE")
    save_btn.clicked.connect(lambda: _save_forward_result(app))
    form.addWidget(save_btn)

    box.setLayout(form)
    return box


def _create_history_table(app):
    app._debug_history_table = QTableWidget()
    app._debug_history_table.setColumnCount(8)
    app._debug_history_table.setHorizontalHeaderLabels(
        ["Time", "Type", "PWM", "Duration(s)", "Value", "Unit", "Source", "Note"]
    )
    app._debug_history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    app._debug_history_table.verticalHeader().setVisible(False)
    app._debug_history_table.setStyleSheet(TABLE_STYLE)
    _reload_history_table(app)
    return app._debug_history_table


def _reload_history_table(app):
    rows = app._calibration_logger.read_recent(limit=20)
    table = app._debug_history_table
    table.setRowCount(len(rows))
    for i, row in enumerate(rows):
        for col, key in enumerate([
            "timestamp", "test_type", "pwm", "duration_s",
            "measured_value", "unit", "source", "note",
        ]):
            item = QTableWidgetItem(str(row.get(key, "")))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(i, col, item)


def _rover_connected(app) -> bool:
    rover_ws = getattr(app._conn_mgr, "rover_ws", None)
    return bool(rover_ws and rover_ws.is_connected)


def _run_spin_test(app):
    if not _rover_connected(app):
        app._add_log("DEBUG", "旋回テスト中止: ローバー未接続")
        return
    try:
        w = int(app._debug_spin_w_input.text().strip())
        duration_s = float(app._debug_spin_duration_input.text().strip())
    except ValueError:
        app._add_log("DEBUG", "旋回テスト中止: w/実行時間の入力値が不正")
        return

    integrator = GyroYawIntegrator(app._conn_mgr.rover_ws.message_received)
    app._debug_spin_integrator = integrator
    integrator.start()
    app._send_command(f"drive:0,{w}")
    app._add_log("DEBUG", f"旋回テスト開始: w={w} duration={duration_s}s")

    def _on_timeout():
        app._send_command("stop")
        angle = integrator.stop()
        if integrator.last_frame_age_sec is None:
            app._debug_spin_gyro_label.setText("未受信")
        else:
            app._debug_spin_gyro_label.setText(f"{angle:.1f}")
        app._add_log("DEBUG", f"旋回テスト終了: ジャイロ計測={angle:.1f}deg")

    QTimer.singleShot(int(duration_s * 1000), _on_timeout)


def _save_spin_result(app):
    manual_text = app._debug_spin_manual_input.text().strip()
    gyro_text = app._debug_spin_gyro_label.text().strip()

    if manual_text:
        try:
            value = float(manual_text)
        except ValueError:
            app._add_log("DEBUG", "旋回結果保存中止: 手動入力値が不正")
            return
        source = "manual"
    elif gyro_text and gyro_text not in ("-", "未受信"):
        value = float(gyro_text)
        source = "gyro"
    else:
        app._add_log("DEBUG", "旋回結果保存中止: ジャイロ計測値も手動入力もありません")
        return

    try:
        w = int(app._debug_spin_w_input.text().strip())
        duration_s = float(app._debug_spin_duration_input.text().strip())
    except ValueError:
        app._add_log("DEBUG", "旋回結果保存中止: w/実行時間の入力値が不正")
        return

    app._calibration_logger.append("spin", w, duration_s, value, "deg", source)
    app._add_log("DEBUG", f"旋回結果を保存: w={w} duration={duration_s}s value={value}deg source={source}")

    app._debug_spin_gyro_label.setText("-")
    app._debug_spin_manual_input.setText("")
    _reload_history_table(app)


def _run_forward_test(app):
    if not _rover_connected(app):
        app._add_log("DEBUG", "前進テスト中止: ローバー未接続")
        return
    try:
        pwm = int(app._debug_forward_pwm_input.text().strip())
        duration_s = float(app._debug_forward_duration_input.text().strip())
    except ValueError:
        app._add_log("DEBUG", "前進テスト中止: PWM/実行時間の入力値が不正")
        return

    app._send_command(f"speed:{abs(pwm)}")
    app._send_command("forward" if pwm >= 0 else "backward")
    app._add_log("DEBUG", f"前進テスト開始: pwm={pwm} duration={duration_s}s")

    def _on_timeout():
        app._send_command("stop")
        app._add_log("DEBUG", "前進テスト終了: 実測距離を入力してSAVEしてください")

    QTimer.singleShot(int(duration_s * 1000), _on_timeout)


def _save_forward_result(app):
    distance_text = app._debug_forward_distance_input.text().strip()
    if not distance_text:
        app._add_log("DEBUG", "前進結果保存中止: 実測距離が未入力")
        return
    try:
        distance_m = float(distance_text)
        pwm = int(app._debug_forward_pwm_input.text().strip())
        duration_s = float(app._debug_forward_duration_input.text().strip())
    except ValueError:
        app._add_log("DEBUG", "前進結果保存中止: 入力値が不正")
        return

    app._calibration_logger.append("forward", pwm, duration_s, distance_m, "m", "manual")
    app._add_log("DEBUG", f"前進結果を保存: pwm={pwm} duration={duration_s}s distance={distance_m}m")

    app._debug_forward_distance_input.setText("")
    _reload_history_table(app)


# --- FOLLOW TUNING タブ ---
# follow_controller.FollowConfigの値をfollow mode実行中でも即座に書き換える
# ためのスライダー群。views/settings_view.pyの_on_follow_param_change
# (kp/ki/kd)と同じ仕組み(ControlThreadが毎tick self.configから読むため、
# アプリ再起動やfollow mode再開始なしに反映される)を、このセッションで
# 調整対象になったパラメータ全部に拡張したもの。

# (属性名, 表示ラベル, スライダー最小, スライダー最大, スケール, 小数桁数)
# スライダーの整数値をscaleで割った値が実際のconfig値になる
# (例: distance_bandはスライダー2-20を100で割って0.02-0.20にする)
_FOLLOW_TUNING_PARAMS = [
    ("turn_speed", "turn_speed (旋回PWM)", 150, 255, 1, 0),
    ("max_follow_pwm", "max_follow_pwm (前進上限)", 180, 255, 1, 0),
    ("min_pwm", "min_pwm (前進下限)", 150, 220, 1, 0),
    ("spin_pulse_on_sec", "spin_pulse_on_sec (旋回パルスON秒)", 2, 30, 100, 2),
    ("straight_command_w_threshold", "straight_command_w_threshold (直進判定閾値)", 0, 40, 1, 0),
    ("distance_band", "distance_band (距離帯幅, m)", 2, 20, 100, 2),
    ("approach_slowdown_dist", "approach_slowdown_dist (減速開始距離, m)", 20, 200, 100, 2),
]


def _create_follow_tuning_tab(app):
    widget = QWidget()
    layout = QVBoxLayout()
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(16)

    title = QLabel("FOLLOW MODE PARAMETER TUNING")
    title.setStyleSheet("color: #22d3ee; font-size: 13px; font-weight: 700; letter-spacing: 2px;")
    layout.addWidget(title)

    note = QLabel(
        "follow mode実行中に値を変えると即座に反映されます"
        "(follow modeが開始されるまでは表示のみで、開始後に反映されます)。"
    )
    note.setWordWrap(True)
    note.setStyleSheet("color: #64748b; font-size: 10px;")
    layout.addWidget(note)

    box = QGroupBox("FollowConfig")
    form = QVBoxLayout()
    app._debug_follow_sliders = {}
    app._debug_follow_labels = {}

    defaults = FollowConfig()
    for attr, label_text, lo, hi, scale, decimals in _FOLLOW_TUNING_PARAMS:
        row = QHBoxLayout()
        label = QLabel(label_text)
        label.setFixedWidth(260)
        row.addWidget(label)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(lo, hi)
        initial = getattr(defaults, attr)
        slider.setValue(int(round(initial * scale)))
        row.addWidget(slider, 1)

        value_label = QLabel(f"{initial:.{decimals}f}" if decimals else str(int(initial)))
        value_label.setFixedWidth(60)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(value_label)

        slider.valueChanged.connect(
            lambda v, a=attr, s=scale, d=decimals: _on_follow_tuning_change(app, a, v, s, d)
        )

        app._debug_follow_sliders[attr] = slider
        app._debug_follow_labels[attr] = value_label
        form.addLayout(row)

    box.setLayout(form)
    layout.addWidget(box)
    layout.addStretch()

    widget.setLayout(layout)
    return widget


def _on_follow_tuning_change(app, attr: str, slider_value: int, scale: int, decimals: int):
    value = slider_value / scale
    label = app._debug_follow_labels[attr]
    label.setText(f"{value:.{decimals}f}" if decimals else str(int(value)))

    if hasattr(app, "_detection_mgr") and app._detection_mgr._follow_controller:
        setattr(app._detection_mgr._follow_controller.config, attr,
                value if decimals else int(value))
        app._add_log("DEBUG", f"follow config更新: {attr}={value}")
