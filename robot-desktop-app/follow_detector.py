import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

sys.path.insert(0, str(Path(__file__).parent))
from rccar_pose_inference import PoseInference, DetectionResult


class FollowDetector(QThread):
    """YOLOv8-pose based car detection for follow mode.
    
    Uses PoseInference module (Kalman-filtered, ArUco-fused, gimbal-compensated)
    to detect 3 keypoints (L wheel, R wheel, front) and compute yaw angle
    and distance to the target car.
    """
    
    detected = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, confidence: float = 0.35, gimbal_thread=None):
        super().__init__()
        self._running = False
        self._frame = None
        self._frame_lock = False
        self._detector = None
        self._confidence = confidence
        self._gimbal_thread = gimbal_thread
        
    def start_detection(self):
        """Initialize the pose inference module."""
        try:
            model_dir = Path(__file__).parent / "rccar_pose_inference" / "rccar_pose_model"
            weights_path = Path(__file__).parent / "follow-mode" / "weight" / "best.pt"
            gimbal_provider = self._gimbal_thread.get_pan_tilt_state if self._gimbal_thread else None
            self._detector = PoseInference(
                model_dir=model_dir, weights_path=weights_path,
                confidence=self._confidence, gimbal_provider=gimbal_provider,
            )
            self._add_log("FOLLOW", "Pose inference module loaded")
        except Exception as e:
            self._add_log("FOLLOW", f"Failed to load model: {e}")
            self.error.emit(str(e))
            
    def set_gimbal_thread(self, gimbal_thread):
        """Set the gimbal thread reference (call before start_detection)."""
        self._gimbal_thread = gimbal_thread
            
    def set_frame(self, frame: np.ndarray):
        """Set the current frame for detection (thread-safe)."""
        if not self._frame_lock:
            self._frame = frame.copy()
            if not hasattr(self, '_frame_set_count'):
                self._frame_set_count = 0
            self._frame_set_count += 1
            if self._frame_set_count % 50 == 0:
                self._add_log("FOLLOW", f"フレーム受信中... {self._frame_set_count}枚目")
            
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
                    if frame_count % 10 == 0:
                        self._add_log("FOLLOW", f"frame={frame_count} yaw={result.yaw_deg} dist={result.dist_m} conf={result.confidence:.2f} bbox={result.bbox is not None}")
                    if result.bbox is not None and (result.yaw_deg is None or result.dist_m is None):
                        if frame_count % 5 == 0:
                            self._add_log("FOLLOW", f"[POSE-DIAG] bbox={result.bbox} yaw={result.yaw_deg} dist={result.dist_m}")
                    
                    self.detected.emit({
                        "yaw_deg": result.yaw_deg,
                        "dist_m": result.dist_m,
                        "bearing_deg": result.bearing_deg,
                        "theta_deg": result.yaw_deg,
                        "confidence": result.confidence,
                        "bbox": result.bbox,
                        "frame_w": result.frame_w,
                        "frame_h": result.frame_h,
                    })
                except Exception as e:
                    self._frame_lock = False
                    self.error.emit(f"Detection error: {e}")
            else:
                if frame_count == 0 and self._frame is None:
                    pass
                elif frame_count == 0 and self._detector is None:
                    self._add_log("FOLLOW", "検出器が初期化されていません")
                    
            self.msleep(100)
            
    def stop(self):
        """Stop the detection loop."""
        self._running = False
        self.wait()
        
    def _add_log(self, category, message):
        """Add log message (placeholder for app integration)."""
        print(f"[{category}] {message}")
