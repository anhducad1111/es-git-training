import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

# rccar_pose_inference はこのファイルと同じ D:\robot-desktop-app 直下に
# トップレベルパッケージとして配置されているため、このディレクトリをパスに
# 追加すれば `from rccar_pose_inference import ...` で解決できる。
sys.path.insert(0, str(Path(__file__).parent))
from rccar_pose_inference import PoseInference


class FollowDetector(QThread):
    """YOLOv8-pose based car detection for follow mode.

    rccar_pose_inference.PoseInference を使い、車の3キーポイント（左右輪・前）から
    ヨー角と距離を推定する。ジンバル(GimbalThread)のpan/tilt状態が分かれば、
    PoseInference側でカメラ座標系から車体本体相対座標系への変換も行う。
    """

    detected = pyqtSignal(dict)  # {yaw_deg, dist_m, confidence, bbox, frame_w, frame_h, bearing_deg, vx_mps, vz_mps, dist_m_predicted}
    error = pyqtSignal(str)

    def __init__(self, confidence: float = 0.35, gimbal_thread=None):
        super().__init__()
        self._running = False
        self._frame = None
        self._frame_lock = False
        self._detector = None
        self._confidence = confidence
        # GimbalThreadはFollowController.start()内で生成されるため、通常は
        # FollowDetectorの方が先に作られる（detection_manager.py参照）。
        # その場合はNoneのまま構築し、後からset_gimbal_thread()で配線する。
        self._gimbal_thread = gimbal_thread

    def set_gimbal_thread(self, gimbal_thread):
        """GimbalThread生成後に呼び出して配線するためのsetter。

        _gimbal_provider()は呼び出しの都度self._gimbal_threadを参照するので、
        start_detection()でPoseInferenceを構築した後にこのsetterを呼んでも
        ジンバル補正は正しく有効になる。
        """
        self._gimbal_thread = gimbal_thread

    def _gimbal_provider(self):
        """PoseInferenceのgimbal_providerとして渡すコールバック。

        (pan_deg, tilt_deg, is_settled) を返す。GimbalThreadがまだ配線されて
        いない場合はキャリブレーション位置（パン中央85度・チルト70度、settled扱い）
        を返し、据え置きカメラに近い挙動にフォールバックする。

        実機検証が必要: パンの正負とカメラ回転方向の符号規約は自動テストでは
        検証できていない（car_follow_car/superpowers/specs/
        2026-09-11-gimbal-pose-compensation-design.md 参照）。
        """
        if self._gimbal_thread is not None:
            return self._gimbal_thread.get_pan_tilt_state()
        return (85.0, 70.0, True)

    def start_detection(self):
        """Initialize the PoseInference model."""
        try:
            model_dir = Path(__file__).parent / "rccar_pose_inference" / "rccar_pose_model"
            weights_path = model_dir / "weights" / "best.pt"
            self._detector = PoseInference(
                model_dir=model_dir,
                weights_path=weights_path,
                confidence=self._confidence,
                gimbal_provider=self._gimbal_provider,
            )
            self._add_log("FOLLOW", "PoseInference model loaded")
        except Exception as e:
            self._add_log("FOLLOW", f"Failed to load model: {e}")
            self.error.emit(str(e))

    def set_frame(self, frame: np.ndarray):
        """Set the current frame for detection (thread-safe)."""
        if not self._frame_lock:
            self._frame = frame.copy()
            if not hasattr(self, '_frame_set_count'):
                self._frame_set_count = 0
            self._frame_set_count += 1
            if self._frame_set_count % 50 == 0:
                self._add_log("FOLLOW", f"Receiving frame... {self._frame_set_count}")

    def run(self):
        """Main detection loop."""
        self._running = True
        frame_count = 0
        while self._running:
            if self._frame is not None and self._detector is not None:
                try:
                    self._frame_lock = True
                    result = self._detector.infer(self._frame)
                    self._frame_lock = False

                    frame_count += 1
                    if frame_count % 50 == 0:
                        self._add_log("FOLLOW", f"Processing frame... {frame_count}")

                    # Emit detection result (follow_controller.py側が期待する辞書形式は変更しない)
                    self.detected.emit({
                        "yaw_deg": result.yaw_deg,
                        "dist_m": result.dist_m,
                        "confidence": result.confidence,
                        "bbox": result.bbox,
                        "frame_w": result.frame_w,
                        "frame_h": result.frame_h,
                        # ジンバルセンタリング用のカメラ相対bearing角(atan2(X,Z))。
                        # 遠距離等でGround.pose()が失敗したフレームはNone
                        "bearing_deg": result.bearing_deg,
                        # Phase 6(未来位置予測): Kalmanフィルタの速度推定値と、
                        # それをprediction_time_sec先まで投影した予測距離。
                        # フィルタ初期化前はNone
                        "vx_mps": result.vx_mps,
                        "vz_mps": result.vz_mps,
                        "dist_m_predicted": result.dist_m_predicted,
                    })

                except Exception as e:
                    self._frame_lock = False
                    self.error.emit(f"Detection error: {e}")
            else:
                if frame_count == 0 and self._frame is None:
                    pass  # Frame not received yet
                elif frame_count == 0 and self._detector is None:
                    self._add_log("FOLLOW", "Detector not initialized")

            self.msleep(100)  # ~10 FPS detection rate

    def stop(self):
        """Stop the detection loop."""
        self._running = False
        self.wait()

    def _add_log(self, category, message):
        """Add log message (placeholder for app integration)."""
        print(f"[{category}] {message}")
