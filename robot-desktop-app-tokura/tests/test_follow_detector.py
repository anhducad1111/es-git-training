import numpy as np
import pytest

from follow_detector import FollowDetector


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
