import os

from calibration import CalibrationLogger, GyroYawIntegrator


class _FakeSignal:
    """pyqtSignal(dict)の最小互換フェイク。connect()されたcallbackを
    emit()で直接呼び出せる。"""

    def __init__(self):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def disconnect(self, callback):
        self._callbacks.remove(callback)

    def emit(self, data: dict):
        for cb in list(self._callbacks):
            cb(data)


def test_gyro_integrator_accumulates_yaw_rate_over_time(monkeypatch):
    signal = _FakeSignal()
    integrator = GyroYawIntegrator(signal)

    t = [1000.0]
    monkeypatch.setattr("calibration.time.time", lambda: t[0])

    integrator.start()
    signal.emit({"type": "imu", "yaw_rate": 10.0})  # 最初のフレーム: dt無しなので積算されない
    t[0] += 0.5
    signal.emit({"type": "imu", "yaw_rate": 10.0})  # 0.5秒 * 10deg/s = 5deg
    t[0] += 0.5
    signal.emit({"type": "imu", "yaw_rate": 20.0})  # 0.5秒 * 20deg/s = 10deg

    angle = integrator.stop()
    assert angle == 15.0


def test_gyro_integrator_ignores_non_imu_frames(monkeypatch):
    signal = _FakeSignal()
    integrator = GyroYawIntegrator(signal)
    t = [0.0]
    monkeypatch.setattr("calibration.time.time", lambda: t[0])

    integrator.start()
    signal.emit({"type": "status", "msg": "CONNECTED"})
    t[0] += 1.0
    signal.emit({"type": "imu", "yaw_rate": 5.0})
    t[0] += 1.0
    signal.emit({"type": "status", "msg": "CONNECTED"})
    t[0] += 1.0
    signal.emit({"type": "imu", "yaw_rate": 5.0})

    angle = integrator.stop()
    # statusフレームはlast_frame_tを更新しない(imuフレーム間のdtがそのまま使われる):
    # t=1でyaw_rate=5、次のimuフレームがt=3なのでdt=2 -> 5*2=10
    assert angle == 10.0


def test_gyro_integrator_last_frame_age_is_none_before_any_imu_frame():
    signal = _FakeSignal()
    integrator = GyroYawIntegrator(signal)
    integrator.start()
    assert integrator.last_frame_age_sec is None
    signal.emit({"type": "status", "msg": "CONNECTED"})
    assert integrator.last_frame_age_sec is None  # imu以外は無視される


def test_gyro_integrator_last_frame_age_updates_after_imu_frame(monkeypatch):
    signal = _FakeSignal()
    integrator = GyroYawIntegrator(signal)
    t = [100.0]
    monkeypatch.setattr("calibration.time.time", lambda: t[0])

    integrator.start()
    signal.emit({"type": "imu", "yaw_rate": 1.0})
    t[0] += 3.0
    assert integrator.last_frame_age_sec == 3.0


def test_gyro_integrator_stop_without_start_does_not_raise():
    signal = _FakeSignal()
    integrator = GyroYawIntegrator(signal)
    assert integrator.stop() == 0.0


def test_calibration_logger_appends_and_creates_header(tmp_path):
    csv_path = tmp_path / "calibration.csv"
    logger = CalibrationLogger(csv_path=str(csv_path))

    logger.append("spin", 190, 1.0, 42.5, "deg", "gyro", "")

    assert csv_path.is_file()
    content = csv_path.read_text(encoding="utf-8")
    assert "timestamp,test_type,pwm,duration_s,measured_value,unit,source,note" in content
    assert "spin,190,1.0,42.5,deg,gyro" in content


def test_calibration_logger_creates_parent_directory(tmp_path):
    csv_path = tmp_path / "nested" / "dir" / "calibration.csv"
    logger = CalibrationLogger(csv_path=str(csv_path))
    logger.append("forward", 200, 2.0, 1.05, "m", "manual", "note here")
    assert csv_path.is_file()


def test_calibration_logger_read_recent_returns_newest_first(tmp_path):
    csv_path = tmp_path / "calibration.csv"
    logger = CalibrationLogger(csv_path=str(csv_path))
    logger.append("spin", 190, 1.0, 10.0, "deg", "gyro")
    logger.append("spin", 190, 1.0, 20.0, "deg", "gyro")
    logger.append("forward", 200, 1.0, 0.5, "m", "manual")

    rows = logger.read_recent(limit=20)
    assert [r["measured_value"] for r in rows] == ["0.5", "20.0", "10.0"]


def test_calibration_logger_read_recent_respects_limit(tmp_path):
    csv_path = tmp_path / "calibration.csv"
    logger = CalibrationLogger(csv_path=str(csv_path))
    for i in range(5):
        logger.append("spin", 190, 1.0, float(i), "deg", "gyro")

    rows = logger.read_recent(limit=2)
    assert len(rows) == 2
    assert rows[0]["measured_value"] == "4.0"
    assert rows[1]["measured_value"] == "3.0"


def test_calibration_logger_read_recent_empty_when_file_missing(tmp_path):
    csv_path = tmp_path / "does_not_exist.csv"
    logger = CalibrationLogger(csv_path=str(csv_path))
    assert logger.read_recent() == []
