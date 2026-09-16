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

    detected = pyqtSignal(dict)  # {yaw_deg, dist_m, confidence, bbox, frame_w, frame_h, bearing_deg, vx_mps, vz_mps, dist_m_predicted, yaw_deg_predicted}
    error = pyqtSignal(str)

    # フレームがこの秒数より新しく更新されていなければ「鮮度切れ」とみなし、
    # 推論をスキップする。カメラは通常10-20fps(50-100ms間隔)で更新されるため、
    # この閾値は通常のジッターは許容しつつ、切断やFPS大幅低下(実機で報告された、
    # 切断イベントが発火しなくてもFPSが極端に落ちると同じ古いフレームを
    # 何度も再推論し続け、実際には映像が止まっているのに過去の計算のまま
    # 前進し続けるように見える)を早めに検知できる値にしてある。
    STALE_FRAME_SEC = 0.5

    def __init__(self, confidence: float = 0.35, gimbal_thread=None):
        super().__init__()
        self._running = False
        self._frame = None
        self._pending_image = None
        self._frame_received_at = None
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
            self._frame_received_at = time.time()
            if not hasattr(self, '_frame_set_count'):
                self._frame_set_count = 0
            self._frame_set_count += 1
            if self._frame_set_count % 50 == 0:
                self._add_log("FOLLOW", f"Receiving frame... {self._frame_set_count}")

    def set_qimage(self, image):
        """Set the current frame as a raw QImage (thread-safe handoff, no copy).

        This exists separately from set_frame() to keep the GUI thread's
        video-paint timer cheap: converting QImage(BGRA)->numpy(BGR) via
        cv2.cvtColor is real per-pixel work, and previously ran synchronously
        on the GUI thread on every paint tick whenever follow mode was
        active (app.py _update_video_frame), competing with the video
        canvas repaint and causing visible stutter in the on-screen feed.
        DecodeThread (mjpeg_receiver.py) never mutates a QImage after
        creating it, so holding a reference to it from this thread and
        converting it later in run() is safe.
        """
        self._pending_image = image
        self._frame_received_at = time.time()
        if not hasattr(self, '_frame_set_count'):
            self._frame_set_count = 0
        self._frame_set_count += 1
        if self._frame_set_count % 50 == 0:
            self._add_log("FOLLOW", f"Receiving frame... {self._frame_set_count}")

    def _consume_pending_image(self):
        """Convert a pending QImage (set via set_qimage) to a BGR numpy frame.

        Runs on this thread (called from run()), not the GUI thread.
        """
        image = self._pending_image
        if image is None:
            return
        self._pending_image = None
        ptr = image.bits()
        ptr.setsize(image.sizeInBytes())
        arr = np.array(ptr).reshape(image.height(), image.width(), 4)
        # See app.py's prior comment (now removed) on why BGRA2BGR (not
        # RGBA2BGR) is correct for QImage.Format_RGB32's in-memory layout.
        self._frame = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)

    def clear_frame(self):
        """カメラストリーム切断時に呼ぶ。set_frame()が呼ばれなくなった間、
        run()のループが最後に受け取った古いフレームを際限なく再推論し続け、
        （同じ画像なので）同じyaw/dist/confidenceを返し続けることで、実際には
        映像が止まっているのに追従を続けている(過去の計算のまま前進し続ける)
        ように見えるバグが実機で報告された。切断時にNoneへ戻すことで、
        run()の`if self._frame is not None`が成立しなくなり、新しいフレームが
        届くまで検出結果を一切emitしなくなる(再接続後は最初の新フレームから
        再開する)。"""
        self._frame = None
        self._pending_image = None
        self._frame_received_at = None

    def _is_frame_stale(self) -> bool:
        """カメラが「切断」イベントを出さないまま(接続維持のまま)FPSだけ極端に
        落ちた場合、clear_frame()は呼ばれないため、鮮度を時刻で直接判定する。"""
        if self._frame_received_at is None:
            return False
        return (time.time() - self._frame_received_at) > self.STALE_FRAME_SEC

    def run(self):
        """Main detection loop."""
        self._running = True
        frame_count = 0
        while self._running:
            if self._is_frame_stale():
                # 鮮度切れの古いフレームを再推論し続けると、同じ画像なので
                # 毎回同じyaw/dist/confidenceを返し続け、実際には映像が
                # 止まっているのに過去の計算のまま前進し続けるように見える
                # (実機で報告されたバグ)。新しいフレームが届くまで検出を
                # 一切emitしない(この間の追従側の挙動はFollowState.SEARCHING/
                # LOST_TIMEOUTの通常のロスト処理に委ねる)。
                self.msleep(100)
                continue
            self._consume_pending_image()
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
                        # それをprediction_time_sec先まで投影した予測距離・予測ヨー。
                        # フィルタ初期化前はNone
                        "vx_mps": result.vx_mps,
                        "vz_mps": result.vz_mps,
                        "dist_m_predicted": result.dist_m_predicted,
                        "yaw_deg_predicted": result.yaw_deg_predicted,
                        "aruco_detected": result.aruco_detected,
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
