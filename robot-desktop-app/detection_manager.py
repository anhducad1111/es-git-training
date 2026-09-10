from PyQt6.QtCore import QObject, pyqtSignal
from follow_detector import FollowDetector
from follow_controller import FollowController, FollowConfig


class DetectionManager(QObject):
    """Manages HOG, YOLO, and Follow mode detection."""
    
    detections_updated = pyqtSignal(list)
    follow_detected = pyqtSignal(dict)
    
    def __init__(self, log_callback, app=None):
        super().__init__()
        self._log = log_callback
        self._app = app
        
        self._hog_detector = None
        self._yolo_detector = None
        self._detection_method = "HOG"
        self._detections = []
        
        self._follow_mode_active = False
        self._follow_detector = None
        self._follow_controller = None
        self._follow_detections = []
        
    def toggle_detection(self):
        """Toggle HOG or YOLO detection."""
        if self._detection_method == "HOG":
            if self._hog_detector and self._hog_detector.isRunning():
                self._hog_detector.stop_detection()
                self._detections = []
                self._log("HOG", "Human detection stopped")
            else:
                from hog_detector import HOGDetector
                self._hog_detector = HOGDetector()
                self._hog_detector.detected.connect(self._on_hog_detected)
                self._hog_detector.error.connect(lambda e: self._log("HOG", f"Error: {e}"))
                self._hog_detector.start_detection()
                self._log("HOG", "Human detection started")
        elif self._detection_method == "YOLO":
            if self._yolo_detector and self._yolo_detector.isRunning():
                self._yolo_detector.stop_detection()
                self._detections = []
                self._log("YOLO", "Object detection stopped")
            else:
                from yolo_detector import YOLODetector
                self._yolo_detector = YOLODetector()
                self._yolo_detector.detected.connect(self._on_hog_detected)
                self._yolo_detector.error.connect(lambda e: self._log("YOLO", f"Error: {e}"))
                self._yolo_detector.status.connect(lambda e: self._log("YOLO", e))
                self._yolo_detector.start_detection()
                self._log("YOLO", "Object detection started")
                
    def _on_hog_detected(self, detections):
        """Handle HOG/YOLO detection results."""
        self._detections = detections
        self.detections_updated.emit(detections)
        if detections:
            self._log("DETECT", f"Detected {len(detections)} object(s)")
            
    def toggle_follow_mode(self):
        """Toggle follow mode."""
        if self._follow_mode_active:
            self._follow_mode_active = False
            if self._follow_detector and self._follow_detector.isRunning():
                self._follow_detector.stop()
            if self._follow_controller:
                self._follow_controller.stop()
            self._follow_detections = []
            self._log("FOLLOW", "Follow mode stopped")
            # Update button state
            if self._app and hasattr(self._app, '_follow_btn'):
                self._app._follow_btn.setText("FOLLOW MODE")
                self._app._follow_btn.setStyleSheet("""
                    background-color: #1e293b;
                    border: 1px solid #7c3aed;
                    color: #7c3aed;
                    font-weight: 600;
                    font-size: 10px;
                    letter-spacing: 1px;
                """)
        else:
            self._follow_mode_active = True
            self._follow_detector = FollowDetector(confidence=0.35)
            self._follow_detector.detected.connect(self._on_follow_detected)
            self._follow_detector.error.connect(lambda e: self._log("FOLLOW", f"Error: {e}"))
            self._follow_detector.start_detection()
            self._follow_detector.start()
            
            config = FollowConfig()
            if self._app and hasattr(self._app, '_follow_k_slider'):
                config.k = self._app._follow_k_slider.value() / 10.0
                config.kp = self._app._follow_kp_slider.value() / 10.0
                config.ki = self._app._follow_ki_slider.value() / 10.0
                config.kd = self._app._follow_kd_slider.value() / 10.0
                config.dist_kp = self._app._follow_dist_kp_slider.value() / 10.0
            
            self._follow_controller = FollowController(
                config=config,
                dry_run=False,
                log_callback=self._log,
                send_command=lambda cmd: self._app._send_command(cmd) if self._app else self._log("CMD", cmd),
                set_speed=lambda spd: self._app._send_command(f"speed:{spd}") if self._app else self._log("SPEED", str(spd)),
                set_gimbal=lambda pan, tilt: self._set_gimbal_with_ui(pan, tilt)
            )
            self._follow_controller.start()
            
            self._log("FOLLOW", f"Follow mode started | k={config.k:.1f} kp={config.kp:.1f} ki={config.ki:.1f} kd={config.kd:.1f}")
            # Update button state
            if self._app and hasattr(self._app, '_follow_btn'):
                self._app._follow_btn.setText("FOLLOWING...")
                self._app._follow_btn.setStyleSheet("""
                    background-color: #7c3aed;
                    border: 1px solid #7c3aed;
                    color: white;
                    font-weight: 600;
                    font-size: 10px;
                    letter-spacing: 1px;
                """)
            
    def _on_follow_detected(self, detection):
        """Handle follow mode detection."""
        if not self._follow_mode_active:
            return
            
        self._follow_detections = [detection] if detection.get("bbox") else []
        
        yaw = detection.get("yaw_deg")
        dist = detection.get("dist_m")
        conf = detection.get("confidence", 0.0)
        
        if yaw is not None and dist is not None:
            self._log("FOLLOW", f"yaw={yaw:+.1f}° dist={dist:.2f}m conf={conf:.2f}")
        else:
            self._log("FOLLOW", f"検出なし conf={conf:.2f}")
            
        self.follow_detected.emit(detection)
        
        if self._follow_controller:
            self._follow_controller.update(detection)
            
    def set_frame(self, bgr):
        """Set frame for detection."""
        if self._follow_mode_active and self._follow_detector and self._follow_detector.isRunning():
            self._follow_detector.set_frame(bgr)
    
    def _set_gimbal_with_ui(self, pan, tilt):
        """Send gimbal command and update UI labels."""
        if self._app:
            self._app._gimbal_pan = int(pan)
            self._app._gimbal_tilt = int(tilt)
            if hasattr(self._app, '_gimbal_pan_label'):
                self._app._gimbal_pan_label.setText(f"{int(pan)}°")
            if hasattr(self._app, '_gimbal_tilt_label'):
                self._app._gimbal_tilt_label.setText(f"{int(tilt)}°")
            if hasattr(self._app, '_gimbal_hud'):
                self._app._gimbal_hud.set_gimbal(int(pan), int(tilt))
            self._app._send_command(f"servo:{int(pan)},{int(tilt)}")
            
    def stop_all(self):
        """Stop all detection."""
        if self._hog_detector and self._hog_detector.isRunning():
            self._hog_detector.stop_detection()
        if self._yolo_detector and self._yolo_detector.isRunning():
            self._yolo_detector.stop_detection()
        if self._follow_detector and self._follow_detector.isRunning():
            self._follow_detector.stop()
        if self._follow_controller:
            self._follow_controller.stop()
            
    @property
    def detections(self):
        return self._detections
        
    @property
    def follow_detections(self):
        return self._follow_detections
        
    @property
    def follow_mode_active(self):
        return self._follow_mode_active
