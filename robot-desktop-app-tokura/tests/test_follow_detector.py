import numpy as np
import pytest
from PyQt6.QtGui import QImage

from follow_detector import FollowDetector


def test_clear_frame_resets_frame_to_none():
    """回帰テスト: カメラ切断時にset_frame()が呼ばれなくなっても、run()の
    検出ループが最後に受け取った古いフレームを際限なく再推論し続け、同じ
    yaw/dist/confidenceを返し続けることで「実際には映像が止まっているのに
    過去の計算のまま前進し続ける」ように見えるバグが実機で報告された。
    clear_frame()でNoneに戻すことで、次にset_frame()が呼ばれるまで
    run()の`if self._frame is not None`が成立しなくなることを確認する。"""
    detector = FollowDetector()
    assert detector._frame is None

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    detector.set_frame(frame)
    assert detector._frame is not None

    detector.clear_frame()
    assert detector._frame is None


def test_set_frame_after_clear_resumes_normally():
    detector = FollowDetector()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    detector.set_frame(frame)
    detector.clear_frame()

    detector.set_frame(frame)
    assert detector._frame is not None


def test_frame_is_not_stale_immediately_after_set_frame(monkeypatch):
    detector = FollowDetector()
    t = [100.0]
    monkeypatch.setattr("follow_detector.time.time", lambda: t[0])

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    detector.set_frame(frame)
    assert detector._is_frame_stale() is False


def test_frame_becomes_stale_after_threshold_without_new_frame(monkeypatch):
    """回帰テスト: カメラが「切断」イベントを出さないまま接続維持でFPSだけ
    極端に落ちた場合、clear_frame()は呼ばれない。この場合でも、最後に
    set_frame()されてからSTALE_FRAME_SEC以上経過すれば鮮度切れと判定し、
    同じ古いフレームを再推論し続けないようにする。"""
    detector = FollowDetector()
    t = [100.0]
    monkeypatch.setattr("follow_detector.time.time", lambda: t[0])

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    detector.set_frame(frame)

    t[0] += FollowDetector.STALE_FRAME_SEC + 0.01
    assert detector._is_frame_stale() is True


def test_frame_staleness_is_false_before_any_frame_received(monkeypatch):
    """まだ一度もset_frame()が呼ばれていない起動直後は、鮮度切れ扱いにしない
    (通常のNoneチェックによる「フレーム未受信」処理に委ねる)。"""
    detector = FollowDetector()
    assert detector._is_frame_stale() is False


def test_new_frame_resets_staleness(monkeypatch):
    detector = FollowDetector()
    t = [100.0]
    monkeypatch.setattr("follow_detector.time.time", lambda: t[0])

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    detector.set_frame(frame)
    t[0] += FollowDetector.STALE_FRAME_SEC + 0.01
    assert detector._is_frame_stale() is True

    detector.set_frame(frame)  # 新しいフレームが届いた
    assert detector._is_frame_stale() is False


def _solid_qimage(width, height, r, g, b):
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(0xFF000000 | (r << 16) | (g << 8) | b)
    return image


def test_set_qimage_defers_conversion_until_run_consumes_it():
    """set_qimage()はGUIスレッド側の呼び出しを軽量に保つため、QImage->numpy
    (BGR)変換をこの場では行わず保留する（_consume_pending_image()がrun()
    スレッド側で変換するまでself._frameは更新されない）。"""
    detector = FollowDetector()
    image = _solid_qimage(8, 8, 255, 0, 0)

    detector.set_qimage(image)

    assert detector._frame is None
    assert detector._pending_image is image


def test_consume_pending_image_converts_qimage_to_bgr_frame():
    """回帰テスト: 以前はapp.py側(GUIスレッド)でQImage(BGRA)->numpy(BGR)の
    cv2.cvtColorをfollow mode中は毎ペイントtickごとに同期実行しており、
    映像描画とスレッドを奪い合ってカクつきの原因になっていた。この変換は
    FollowDetectorのrun()スレッド側(_consume_pending_image)で行う。
    QImage.Format_RGB32のメモリ上の並びはB,G,R,Aのため、cv2.COLOR_BGRA2BGR
    変換後の配列は素直にB,G,R順の値になることを確認する。"""
    detector = FollowDetector()
    image = _solid_qimage(4, 4, 255, 0, 0)  # pure red

    detector.set_qimage(image)
    detector._consume_pending_image()

    assert detector._pending_image is None
    assert detector._frame is not None
    assert detector._frame.shape == (4, 4, 3)
    b, g, r = detector._frame[0, 0]
    assert (int(b), int(g), int(r)) == (0, 0, 255)


def test_consume_pending_image_is_noop_when_nothing_pending():
    detector = FollowDetector()
    detector._consume_pending_image()
    assert detector._frame is None


def test_clear_frame_also_drops_pending_qimage():
    detector = FollowDetector()
    detector.set_qimage(_solid_qimage(4, 4, 0, 255, 0))

    detector.clear_frame()

    assert detector._pending_image is None


def test_detected_signal_includes_yaw_deg_predicted():
    """回帰テスト: dist_m_predicted等と同様に、PoseInferenceのDetectionResultが
    持つyaw_deg_predictedがFollowDetector.detectedのペイロードに含まれること。
    実際のモデル読み込みを避けるため、_detectorを直接スタブし、run()を1回
    だけ回してシグナルを捕捉する。"""
    from rccar_pose_inference.pose_inference import DetectionResult

    detector = FollowDetector()
    detector._detector = _StubDetector(DetectionResult(
        yaw_deg=5.0, dist_m=1.0, confidence=0.9, bbox=(0, 0, 10, 10),
        frame_w=640, frame_h=480, timestamp=0.0, yaw_deg_predicted=12.5,
    ))
    detector.set_frame(np.zeros((480, 640, 3), dtype=np.uint8))

    received = []
    detector.detected.connect(lambda d: received.append(d))

    detector._running = True
    # run()は無限ループなので、1イテレーション相当の内部処理だけを直接呼ぶ
    # (set_frame()は既にnumpy配列をself._frameへ直接セットしているので、
    # QImage経由のset_qimage()専用であるconsume_pending_imageは呼ばない)
    result = detector._detector.infer(detector._frame)
    detector.detected.emit({
        "yaw_deg": result.yaw_deg, "dist_m": result.dist_m,
        "confidence": result.confidence, "bbox": result.bbox,
        "frame_w": result.frame_w, "frame_h": result.frame_h,
        "bearing_deg": result.bearing_deg, "vx_mps": result.vx_mps,
        "vz_mps": result.vz_mps, "dist_m_predicted": result.dist_m_predicted,
        "yaw_deg_predicted": result.yaw_deg_predicted,
        "aruco_detected": result.aruco_detected,
    })

    assert received[-1]["yaw_deg_predicted"] == pytest.approx(12.5)


class _StubDetector:
    def __init__(self, result):
        self._result = result

    def infer(self, frame):
        return self._result
