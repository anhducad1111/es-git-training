"""実機キャリブレーション用のデバッグタブが使うロジック(UI非依存)。

開発中のみ使う道具であり、恒久機能ではない。follow_controller.py等の
本番コードには一切依存させず、このファイルとviews/debug_view.pyの2つに
閉じ込めることで、将来まるごと削除しやすくしてある。
"""

import csv
import os
import time
from typing import Optional


class GyroYawIntegrator:
    """ESP32がWebSocketで配信する{"type":"imu","yaw_rate":...}フレームを
    積分し、旋回テスト中の実際の回転角度(度)を推定する。

    yaw_rateの単位・符号がAPI_DOCUMENTATION.mdに明記されていないため、
    実機で符号が逆だった場合はUI側の手動入力で上書きできるようにしてある
    (このクラス自体は素直にyaw_rate*dtを積算するだけ)。
    """

    def __init__(self, message_signal):
        """message_signal: .connect(callback)/.disconnect(callback)を持つ
        オブジェクト(PyQtのpyqtSignal(dict)、またはテスト用の互換オブジェクト)。
        """
        self._message_signal = message_signal
        self._running = False
        self._connected = False
        self._accumulated_deg = 0.0
        self._last_frame_t: Optional[float] = None
        self._last_frame_received_at: Optional[float] = None

    def start(self) -> None:
        self._accumulated_deg = 0.0
        self._last_frame_t = None
        self._last_frame_received_at = None
        self._running = True
        self._message_signal.connect(self._on_message)
        self._connected = True

    def stop(self) -> float:
        self._running = False
        if self._connected:
            self._message_signal.disconnect(self._on_message)
            self._connected = False
        return self._accumulated_deg

    @property
    def last_frame_age_sec(self) -> Optional[float]:
        """直近でimuフレームを受信してから何秒経過したか。
        一度も受信していなければNone。"""
        if self._last_frame_received_at is None:
            return None
        return time.time() - self._last_frame_received_at

    def _on_message(self, data: dict) -> None:
        if not self._running:
            return
        if data.get("type") != "imu":
            return
        yaw_rate = data.get("yaw_rate")
        if yaw_rate is None:
            return

        now = time.time()
        self._last_frame_received_at = now
        if self._last_frame_t is not None:
            dt = now - self._last_frame_t
            self._accumulated_deg += yaw_rate * dt
        self._last_frame_t = now


class CalibrationLogger:
    """logs/calibration.csvへのキャリブレーション結果の追記・読み込み。"""

    FIELDNAMES = [
        "timestamp", "test_type", "pwm", "duration_s",
        "measured_value", "unit", "source", "note",
    ]

    def __init__(self, csv_path: str = "logs/calibration.csv"):
        self._csv_path = csv_path

    def append(self, test_type: str, pwm: int, duration_s: float,
               measured_value: float, unit: str, source: str, note: str = "") -> None:
        directory = os.path.dirname(self._csv_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        file_exists = os.path.isfile(self._csv_path)
        with open(self._csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
            if not file_exists:
                writer.writeheader()
            writer.writerow({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "test_type": test_type,
                "pwm": pwm,
                "duration_s": duration_s,
                "measured_value": measured_value,
                "unit": unit,
                "source": source,
                "note": note,
            })

    def read_recent(self, limit: int = 20) -> list:
        """直近limit件を新しい順に返す。ファイルが無ければ空リスト。"""
        if not os.path.isfile(self._csv_path):
            return []
        with open(self._csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        return list(reversed(rows))[:limit]
