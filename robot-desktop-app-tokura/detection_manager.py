from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication, QProgressDialog
from follow_detector import FollowDetector
from follow_controller import FollowController, FollowConfig
import time


class DetectionManager(QObject):
    """Manages HOG, YOLO, and Follow mode detection."""
    
    detections_updated = pyqtSignal(list)
    follow_detected = pyqtSignal(dict)
    target_lost = pyqtSignal()
    target_found = pyqtSignal()
    aruco_lost = pyqtSignal()
    aruco_found = pyqtSignal()
    
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

    def _show_loading_dialog(self, message: str):
        """推論モデルの読み込み(YOLO/PoseInference)は数百ms〜数秒かかる同期処理で、
        呼び出し元がGUIスレッド(ボタンクリックハンドラ)のためその間UIがフリーズする。
        せめて読み込み中であることが分かるよう、ブロッキング呼び出しの直前に
        ビジー表示のダイアログを出し、processEvents()で強制的に描画させる。"""
        parent = self._app if self._app else None
        dialog = QProgressDialog(message, None, 0, 0, parent)
        dialog.setWindowTitle("読み込み中")
        dialog.setCancelButton(None)
        dialog.setMinimumDuration(0)
        dialog.setAutoClose(False)
        dialog.setAutoReset(False)
        dialog.show()
        QApplication.processEvents()
        return dialog

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
                loading_dialog = self._show_loading_dialog("YOLOモデルを読み込み中...")
                try:
                    self._yolo_detector.start_detection()
                finally:
                    loading_dialog.close()
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
            if self._app and hasattr(self._app, '_video_canvas'):
                self._app._video_canvas.set_follow_detections([])
            self._target_lost_timer.stop()
            self._last_detection_time = None
            self._is_target_lost = False
            self._last_aruco_time = None
            self._is_aruco_lost = False
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
            loading_dialog = self._show_loading_dialog("追従用モデルを読み込み中...")
            try:
                self._follow_detector.start_detection()
            finally:
                loading_dialog.close()
            self._follow_detector.start()
            
            config = FollowConfig()
            if self._app and hasattr(self._app, '_follow_kp_slider'):
                config.kp_lin = self._app._follow_kp_slider.value() / 10.0
                config.ki_lin = self._app._follow_ki_slider.value() / 10.0
                config.kd_lin = self._app._follow_kd_slider.value() / 10.0
            
            self._follow_controller = FollowController(
                config=config,
                dry_run=False,
                log_callback=self._log,
                send_command=lambda cmd: self._app._send_command(cmd) if self._app else self._log("CMD", cmd),
                set_speed=lambda spd: self._app._send_command(f"speed:{spd}") if self._app else self._log("SPEED", str(spd)),
                set_gimbal=lambda pan, tilt: self._set_gimbal_with_ui(pan, tilt)
            )
            self._follow_controller.start()

            # FollowDetectorはFollowController(ひいてはGimbalThread)より先に生成されるため、
            # GimbalThread生成後にここで配線する（follow_detector.pyのset_gimbal_thread参照）。
            if self._follow_detector and self._follow_controller._gimbal_thread:
                self._follow_detector.set_gimbal_thread(self._follow_controller._gimbal_thread)

            # カメラストリーム接続イベント(app._on_camera_connected)は、follow mode開始
            # より前に一度だけ発火していることが多く、その時点ではまだGimbalThreadが
            # 存在しないため取りこぼされる。ここで新しく生成したGimbalThreadに対して
            # 現在の接続状態を反映させないと、GimbalThread.run()が永久にcamera_connected
            # 待ちのまま何も追従しない（実機で「追従されない」として発現したバグ）。
            if (self._app and getattr(self._app, "_camera_connected", False)
                    and self._follow_controller._gimbal_thread):
                self._follow_controller._gimbal_thread.on_camera_connected()

            self._log("FOLLOW", f"Follow mode started | kp_lin={config.kp_lin:.1f} ki_lin={config.ki_lin:.1f} kd_lin={config.kd_lin:.1f}")
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
            self._log("FOLLOW", f"[DIST] yaw={yaw:+.1f}° dist={dist:.2f}m conf={conf:.2f}")
        else:
            self._log("FOLLOW", f"[DIST] No detection (yaw/dist missing) conf={conf:.2f}")
            
        self.follow_detected.emit(detection)
        
        if self._follow_controller:
            self._follow_controller.update(detection)

        if detection.get("bbox") and detection.get("confidence", 0) > 0.3:
            self._last_detection_time = time.time()
            if self._is_target_lost:
                self._is_target_lost = False
                self.target_found.emit()
                self._log("FOLLOW", "Target found")
        
        if detection.get("aruco_detected"):
            self._last_aruco_time = time.time()
            if self._is_aruco_lost:
                self._is_aruco_lost = False
                self.aruco_found.emit()
                self._log("FOLLOW", "ArUco marker found")
        
        if not self._target_lost_timer.isActive():
            self._target_lost_timer.start(500)

    def _check_target_lost(self):
        """Check if target has been lost."""
        if self._last_detection_time is not None:
            elapsed = time.time() - self._last_detection_time
            if elapsed > self._target_lost_timeout and not self._is_target_lost:
                self._is_target_lost = True
                self.target_lost.emit()
                self._log("FOLLOW", "Target lost")
        
        if self._last_aruco_time is not None:
            elapsed_aruco = time.time() - self._last_aruco_time
            if elapsed_aruco > self._aruco_lost_timeout and not self._is_aruco_lost:
                self._is_aruco_lost = True
                self.aruco_lost.emit()
                self._log("FOLLOW", "ArUco marker lost")
            
    def set_frame(self, bgr):
        """Set frame for detection."""
        if self._follow_mode_active and self._follow_detector and self._follow_detector.isRunning():
            self._follow_detector.set_frame(bgr)
    
    def _set_gimbal_with_ui(self, pan, tilt):
        """Send gimbal command and update UI labels."""
        from views.sidebar import _actual_to_display_pan, _actual_to_display_tilt
        if self._app:
            self._app._gimbal_pan = int(pan)
            self._app._gimbal_tilt = int(tilt)
            if hasattr(self._app, '_gimbal_pan_input'):
                self._app._gimbal_pan_input.setText(str(_actual_to_display_pan(int(pan))))
            if hasattr(self._app, '_gimbal_tilt_input'):
                self._app._gimbal_tilt_input.setText(str(_actual_to_display_tilt(int(tilt))))
            if hasattr(self._app, '_gimbal_hud'):
                self._app._gimbal_hud.set_gimbal(int(pan), int(tilt))
            if hasattr(self._app, '_target_angle_display'):
                target_angle = int(pan) - 90
                if target_angle > 0:
                    self._app._target_angle_display.setText(f"+{target_angle}°")
                else:
                    self._app._target_angle_display.setText(f"{target_angle}°")
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
