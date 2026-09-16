"""ジャイロ直進PID(ESP32 /api/pid)の既定値。

実機で確認済みの良好値。ESP32のAPIは他クライアント(ブラウザ等)からも
変更されうるため、アプリ起動時(ローバー接続確立時)にこの値を必ず送信して
上書きする(app.py:_enforce_gyro_pid_defaults)。SettingsタブのPIDスライダーや
DEBUGタブのGyro PID欄の初期表示も、値がバラバラにならないようこの定数を参照する。
"""

GYRO_PID_DEFAULTS = {
    "kp": 0.2,
    "ki": 0.05,
    "kd": 0.4,
    "enabled": True,
    "turn": 0.4,
    "bias": 0,
}
