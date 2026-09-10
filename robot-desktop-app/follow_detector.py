import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

# Add app2 to path for importing RcCarPoseDetector
sys.path.insert(0, str(Path(__file__).parent))
from app2.detectors import RcCarPoseDetector


class FollowDetector(QThread):
    """YOLOv8-pose based car detection for follow mode.
    
    Uses RcCarPoseDetector from app2 to detect 3 keypoints (L wheel, R wheel, front)
    and compute yaw angle and distance to the target car.
    """
    
    detected = pyqtSignal(dict)  # {yaw_deg, dist_m, confidence, bbox, keypoints}
    error = pyqtSignal(str)
    
    def __init__(self, confidence: float = 0.35):
        super().__init__()
        self._running = False
        self._frame = None
        self._frame_lock = False
        self._detector = None
        self._confidence = confidence
        
    def start_detection(self):
        """Initialize the YOLO model."""
        try:
            self._detector = RcCarPoseDetector(confidence=self._confidence)
            self._add_log("FOLLOW", "YOLOv8-pose model loaded")
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
                self._add_log("FOLLOW", f"フレーム受信中... {self._frame_set_count}枚目")
            
    def run(self):
        """Main detection loop."""
        self._running = True
        frame_count = 0
        while self._running:
            if self._frame is not None and self._detector is not None:
                try:
                    self._frame_lock = True
                    result = self._detector.detect(self._frame)
                    self._frame_lock = False
                    
                    frame_count += 1
                    if frame_count % 50 == 0:
                        self._add_log("FOLLOW", f"フレーム処理中... {frame_count}フレーム目")
                    
                    if result.boxes:
                        # Get best detection
                        best_idx = int(np.argmax(result.scores))
                        box = result.boxes[best_idx]
                        label = result.labels[best_idx]
                        score = result.scores[best_idx]
                        
                        # Use yaw_deg and dist_m directly from Detection object
                        yaw_deg = result.yaw_deg
                        dist_m = result.dist_m
                        
                        # Get frame dimensions
                        h, w = self._frame.shape[:2]
                        
                        # Emit detection result
                        self.detected.emit({
                            "yaw_deg": yaw_deg,
                            "dist_m": dist_m,
                            "confidence": score,
                            "bbox": box,
                            "label": label,
                            "frame_w": w,
                            "frame_h": h,
                        })
                    else:
                        # No detection
                        self.detected.emit({
                            "yaw_deg": None,
                            "dist_m": None,
                            "confidence": 0.0,
                            "bbox": None,
                            "label": None,
                            "frame_w": 640,
                            "frame_h": 480,
                        })
                        
                except Exception as e:
                    self._frame_lock = False
                    self.error.emit(f"Detection error: {e}")
            else:
                if frame_count == 0 and self._frame is None:
                    pass  # Frame not received yet
                elif frame_count == 0 and self._detector is None:
                    self._add_log("FOLLOW", "検出器が初期化されていません")
                    
            self.msleep(100)  # ~10 FPS detection rate
            
    def stop(self):
        """Stop the detection loop."""
        self._running = False
        self.wait()
        
    def _add_log(self, category, message):
        """Add log message (placeholder for app integration)."""
        print(f"[{category}] {message}")
