import os
import time
from datetime import datetime
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from config import load_config, save_config
from styles import DARK_STYLE
from views.header import create_header
from views.main_view import create_main_view
from views.diagnostics_view import create_diagnostics_view
from views.snapshots_view import create_snapshots_view
from views.settings_view import create_settings_view
from views.debug_view import create_debug_view
from views.sidebar import create_sidebar
from views.key_legend import create_key_legend
from views.log_panel import create_log_panel
from connection_manager import ConnectionManager
from video_manager import VideoManager
from detection_manager import DetectionManager
from input_handler import InputHandler
from cloud_manager import CloudManager
from remote_control_server import RemoteControlServer
from cloud_worker import CloudWorker


class RoverTeleopApp(QWidget):
    log_message = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self._config = load_config()
        self._view_mode = "main"
        self._current_speed = self._config.get("motor_speed", 220)
        self._global_speed = self._current_speed
        self._gimbal_pan = 90
        self._gimbal_tilt = 90
        self._display_frame_count = 0
        self._display_fps_last_time = time.time()
        # カメラストリーム接続状態。follow modeトグル時点で既に接続済みなら
        # 新規生成されるGimbalThreadに即座にon_camera_connected()を伝える必要がある
        # (接続イベントはfollow mode開始より先に一度だけ発火するため、フラグで保持する)
        self._camera_connected = False

        # ジャイロ直進PID(/api/pid)の適用はデバウンス+非同期(CloudWorker)で行う。
        # 以前はスライダーを動かすたびに同期HTTPリクエスト(esp32_api.set_pid)を
        # 直接呼んでおり、ドラッグ中に何度もGUIスレッドをブロックしていた
        # (robot-desktop-app-tokura版はCloudWorker+400msデバウンスで解決していた
        # ため、同じ方式に合わせる)。
        self._pid_apply_timer = QTimer()
        self._pid_apply_timer.setSingleShot(True)
        self._pid_apply_timer.timeout.connect(self._apply_pid_params)
        self._pid_workers = []

        # LEDスライダー(views/sidebar.py)も同じ理由で、動かすたびに
        # esp32_api.set_led()を同期HTTPで直接呼んでおり、ドラッグ中GUIスレッドが
        # 何度もブロックされて映像が激しくカクつく原因になっていた。さらに実機
        # 検証の結果、ESP32-CamのHTTPサーバは映像ストリーム配信中は他の
        # リクエストを一切処理できない(ストリームを止めた直後は正常応答する)
        # ことが分かったため、_apply_led()では送信の間だけ一瞬カメラを止める。
        # PIDと同じデバウンス+CloudWorkerの非同期方式に合わせる
        self._led_apply_timer = QTimer()
        self._led_apply_timer.setSingleShot(True)
        self._led_apply_timer.timeout.connect(self._apply_led_from_slider)
        self._led_workers = []

        # 速度スライダー(views/sidebar.py)も同じ理由で、ドラッグ中に動かすたびに
        # speed:N をWebSocketへ即送信しており、無駄な送信とログ行の大量発生に
        # なっていた。PID/LEDと同じデバウンス方式に合わせ、操作が止まってから
        # 150ms後の1回だけ実際に送信する(ラベル/メーター表示はドラッグ中も
        # 即座に更新する)。
        self._speed_apply_timer = QTimer()
        self._speed_apply_timer.setSingleShot(True)
        self._speed_apply_timer.timeout.connect(self._apply_speed_change)

        # 今後の調整・デバッグ用に、全ログをテキストファイルにも自動保存する。
        # GUIログウィジェットは表示件数に上限があるため、後から見返す・
        # 貼り付ける用途にはこのファイルの方が確実
        os.makedirs("logs", exist_ok=True)
        log_filename = f"logs/follow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self._log_file = open(log_filename, "a", encoding="utf-8")
        print(f"[LOG] Log file: {log_filename}", flush=True)

        # Initialize managers
        # log_message.emit(category, message)をコールバックとして渡す(直接
        # self._add_logを渡さない)。DetectionManager経由のfollow_controller.py
        # (GimbalThread/ControlThread/DetectionThread)は素のthreading.Threadで
        # 動いており、そこから直接self._add_log()経由でQTextEditを操作すると
        # PyQtのGUIスレッド専有ルールに違反する。pyqtSignalは発行元がどのスレッド
        # でも安全で、接続先(self._add_log、GUIスレッド所属)へ自動的にキューイング
        # されるため、ここを経由するだけでバックグラウンドスレッドからのログが
        # 安全になる。
        self._conn_mgr = ConnectionManager(self._config, self.log_message.emit)
        self._video_mgr = VideoManager(None, self.log_message.emit)
        self._detection_mgr = DetectionManager(self.log_message.emit, app=self)
        self._input_handler = InputHandler(self._send_command, self.log_message.emit, on_emergency_stop=self._emergency_stop, on_chassis_follow_toggle=self._toggle_chassis_follow, on_gimbal_update=self._on_gimbal_update)
        self._cloud_mgr = CloudManager(self._config, self.log_message.emit)
        self._latest_telemetry = {}
        self._allow_remote_control = False
        self._remote_server = None
        self._obstacle_brake_active = False
        self._speed_limit_active = False
        
        self._speed_timer = QTimer()
        self._speed_timer.timeout.connect(self._input_handler._tick_speed)
        self._speed_timer.setInterval(50)
        
        self.init_ui()
        self.connect_signals()
        self.start_connections()

    def init_ui(self):
        self.setWindowTitle("Rover Teleop Cockpit v2.5.0")
        self.setMinimumSize(1400, 900)
        self.setStyleSheet(DARK_STYLE)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_layout.addWidget(create_header(self))

        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)

        self._center_stack = QStackedWidget()
        self._center_stack.addWidget(create_main_view(self))
        self._center_stack.addWidget(create_diagnostics_view(self))
        self._center_stack.addWidget(create_snapshots_view(self))
        self._center_stack.addWidget(create_settings_view(self))
        self._center_stack.addWidget(create_debug_view(self))  # index 4: 開発用デバッグタブ、削除時はこの行ごと消せばよい
        content.addWidget(self._center_stack, 1)

        self._sidebar = create_sidebar(self)
        content.addWidget(self._sidebar)

        main_layout.addLayout(content, 1)

        main_layout.addWidget(create_key_legend(self))
        main_layout.addWidget(create_log_panel(self))

        self.setFocus()

    def connect_signals(self):
        self.log_message.connect(self._add_log)
        self._detection_mgr.detections_updated.connect(self._on_detections_updated)
        self._detection_mgr.follow_detected.connect(self._on_follow_detected)
        if hasattr(self, '_video_canvas'):
            self._video_canvas.gimbal_changed.connect(self._on_mouse_gimbal)
        # ConnectionManagerのcamera_connected/camera_disconnectedは宣言されているだけで
        # どこにも接続されていなかった（既知バグ）。これが繋がっていないと
        # self._camera_connectedが常にFalseのままになり、follow mode開始時に新しく
        # 生成されるGimbalThreadへon_camera_connected()が伝わらず、ジンバルが
        # 一切追従しない（実機で「ジンバルが動かない」として発現したバグ）。
        self._conn_mgr.camera_connected.connect(self._on_camera_connected)
        self._conn_mgr.camera_disconnected.connect(self._on_camera_disconnected)
        self._conn_mgr.video_stats.connect(self._on_video_stats)
        self._conn_mgr.rover_connected.connect(self._on_rover_connected)
        self._conn_mgr.rover_disconnected.connect(self._on_rover_disconnected)

    def start_connections(self):
        self._conn_mgr.start_all()
        # TelemetryPollerのdata_receivedをConnectionManager経由で接続。
        # reconnect_rover()でpollerが差し替わってもシグナルが途切れない。
        self._conn_mgr.telemetry_data.connect(self._on_telemetry_received)
        # ConnectionManagerが生成したESP32APIをappにも持たせる。sidebar.py等の
        # UI側は`hasattr(app, '_esp32_api')`で存在チェックしているが、この属性が
        # 一度も設定されておらず、PIDトグル・kp/ki/kdスライダー・ブレーキ・LED・
        # 画質調整が全てエラーも出さず黙って無効化されていた(既知バグ、ここで修正)。
        self._esp32_api = self._conn_mgr.esp32_api
        self._cloud_mgr.initialize()
        self._video_mgr._cloud_api = self._cloud_mgr.cloud_api
        
        port = self._config.get("remote_control_port", 8765)
        self._remote_server = RemoteControlServer("0.0.0.0", port)
        self._remote_server.command_received.connect(self._relay_command)
        self._remote_server.set_rover_connected(
            self._conn_mgr.rover_ws is not None
            and self._conn_mgr.rover_ws.is_connected
        )
        self._conn_mgr.rover_connected.connect(
            lambda: self._remote_server.set_rover_connected(True)
        )
        self._conn_mgr.rover_disconnected.connect(
            lambda: self._remote_server.set_rover_connected(False)
        )
        self._remote_server.start()
        self._add_log("REMOTE", f"Remote control server listening on port {port}")
        
        self._video_timer = QTimer()
        self._video_timer.timeout.connect(self._update_video_frame)
        self._video_timer.start(33)
        
        self._cloud_timer = QTimer()
        self._cloud_timer.timeout.connect(self._send_cloud_update)
        self._cloud_timer.start(10000)
        
        self._add_log("MODE", "Connecting to REAL ESP32 hardware...")
        
        self._gimbal_pan = 90
        self._gimbal_tilt = 90
        self._send_command("servo:90,90")

    def _update_video_frame(self):
        frame = self._conn_mgr.take_frame()
        if frame:
            if isinstance(frame, tuple):
                image, frame_time = frame
            else:
                image, frame_time = frame, None

            if isinstance(image, QImage):
                if self._video_mgr.is_recording:
                    self._video_mgr.save_frame(image)
                self._video_canvas.update_frame_jpeg(image)

                # FPS/latency measured at the point of actual display, not
                # at decode/receive time, so they reflect what's on screen.
                self._display_frame_count += 1
                now = time.time()
                elapsed = now - self._display_fps_last_time
                if elapsed >= 1.0:
                    fps = self._display_frame_count / elapsed
                    if hasattr(self, '_fps_display'):
                        self._fps_display.update_fps(fps)
                    self._display_frame_count = 0
                    self._display_fps_last_time = now
                if frame_time is not None and hasattr(self, '_latency_display'):
                    self._latency_display.update_latency((now - frame_time) * 1000)

                if self._detection_mgr._follow_mode_active:
                    import cv2
                    import numpy as np
                    ptr = image.bits()
                    ptr.setsize(image.sizeInBytes())
                    arr = np.array(ptr).reshape(image.height(), image.width(), 4)
                    # QImage.Format_RGB32 is stored in memory as B,G,R,A (not
                    # R,G,B,A) on little-endian platforms - confirmed by
                    # inspecting the raw bytes of a known pure-red pixel.
                    # COLOR_RGBA2BGR treats the input as R,G,B,A and was
                    # therefore swapping the red/blue channels of every frame
                    # fed into follow-mode's pose inference (a real,
                    # long-standing accuracy bug, not a tuning issue).
                    bgr = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
                    self._detection_mgr.set_frame(bgr)
            elif isinstance(frame, bytes):
                from video_worker import VideoWorker
                if not hasattr(self, '_video_worker'):
                    self._video_worker = VideoWorker()
                    self._video_worker.frame_ready.connect(self._on_video_frame_ready)
                    self._video_worker.start()
                self._video_worker.push_frame(frame)

    def _on_video_frame_ready(self, pixmap, bgr):
        self._video_canvas.update_frame_jpeg(pixmap)
        if bgr is not None:
            self._detection_mgr.set_frame(bgr)

    def _on_detections_updated(self, detections):
        pass

    def _on_follow_detected(self, detection):
        self._video_canvas.set_follow_detections(
            [detection] if detection.get("bbox") else []
        )

    def _send_cloud_update(self):
        pass

    def _toggle_view(self):
        if self._view_mode == "diagnostics":
            self._center_stack.setCurrentIndex(0)
            self._view_mode = "main"
            if hasattr(self, '_diag_btn'):
                self._diag_btn.setChecked(False)
        else:
            self._center_stack.setCurrentIndex(1)
            self._view_mode = "diagnostics"
            if hasattr(self, '_diag_btn'):
                self._diag_btn.setChecked(True)
            if hasattr(self, '_snapshot_btn'):
                self._snapshot_btn.setChecked(False)
            if hasattr(self, '_settings_btn'):
                self._settings_btn.setChecked(False)
            if hasattr(self, '_debug_btn'):
                self._debug_btn.setChecked(False)

    def _toggle_snapshots_view(self):
        if self._view_mode == "snapshots":
            self._center_stack.setCurrentIndex(0)
            self._view_mode = "main"
            if hasattr(self, '_snapshot_btn'):
                self._snapshot_btn.setChecked(False)
        else:
            self._center_stack.setCurrentIndex(2)
            self._view_mode = "snapshots"
            if hasattr(self, '_snapshot_btn'):
                self._snapshot_btn.setChecked(True)
            if hasattr(self, '_diag_btn'):
                self._diag_btn.setChecked(False)
            if hasattr(self, '_settings_btn'):
                self._settings_btn.setChecked(False)
            if hasattr(self, '_debug_btn'):
                self._debug_btn.setChecked(False)
            from views.snapshots_view import _load_snapshots
            _load_snapshots(self)

    def _toggle_settings(self):
        if self._view_mode == "settings":
            self._center_stack.setCurrentIndex(0)
            self._view_mode = "main"
            if hasattr(self, '_settings_btn'):
                self._settings_btn.setChecked(False)
        else:
            self._center_stack.setCurrentIndex(3)
            self._view_mode = "settings"
            if hasattr(self, '_settings_btn'):
                self._settings_btn.setChecked(True)
            if hasattr(self, '_diag_btn'):
                self._diag_btn.setChecked(False)
            if hasattr(self, '_snapshot_btn'):
                self._snapshot_btn.setChecked(False)
            if hasattr(self, '_debug_btn'):
                self._debug_btn.setChecked(False)

    def _toggle_debug_view(self):
        """開発用デバッグ/キャリブレーションタブの表示切替。
        不要になったらこのメソッドとsidebarの_debug_btn配線を削除すればよい。"""
        if self._view_mode == "debug":
            self._center_stack.setCurrentIndex(0)
            self._view_mode = "main"
            if hasattr(self, '_debug_btn'):
                self._debug_btn.setChecked(False)
        else:
            self._center_stack.setCurrentIndex(4)
            self._view_mode = "debug"
            if hasattr(self, '_debug_btn'):
                self._debug_btn.setChecked(True)
            if hasattr(self, '_diag_btn'):
                self._diag_btn.setChecked(False)
            if hasattr(self, '_snapshot_btn'):
                self._snapshot_btn.setChecked(False)
            if hasattr(self, '_settings_btn'):
                self._settings_btn.setChecked(False)

    def _toggle_follow_mode(self):
        self._detection_mgr.toggle_follow_mode()

    def _toggle_hog_detection(self):
        self._detection_mgr.toggle_detection()

    def _center_gimbal(self):
        self._input_handler.center_gimbal()
        self._add_log("GIMBAL", "Centered")

    def _manual_send_to_cloud(self):
        self._add_log("CLOUD", "Manual send triggered")

    @property
    def _cloud_api(self):
        return self._cloud_mgr.cloud_api

    @property
    def _cloud_workers(self):
        return self._cloud_mgr._cloud_workers

    def _start_recording(self):
        self._video_mgr.start_recording()

    def _stop_recording(self):
        self._video_mgr.stop_recording()

    def _on_camera_connected(self):
        """Handle camera stream connected."""
        self._camera_connected = True
        self._add_log("CAMERA", "Stream connected")
        if hasattr(self, '_cam_status'):
            self._cam_status.setText("ONLINE")
            self._cam_status.setStyleSheet("""
                color: #10b981;
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 1px;
                margin-left: 12px;
            """)
        if self._detection_mgr and self._detection_mgr._follow_controller:
            gimbal_thread = self._detection_mgr._follow_controller._gimbal_thread
            if gimbal_thread:
                gimbal_thread.on_camera_connected()

    def _on_camera_disconnected(self):
        """Handle camera stream disconnected."""
        self._camera_connected = False
        self._add_log("CAMERA", "Stream disconnected")
        if hasattr(self, '_cam_status'):
            self._cam_status.setText("OFFLINE")
            self._cam_status.setStyleSheet("""
                color: #ef4444;
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 1px;
                margin-left: 12px;
            """)
        if self._detection_mgr and self._detection_mgr._follow_controller:
            gimbal_thread = self._detection_mgr._follow_controller._gimbal_thread
            if gimbal_thread:
                gimbal_thread.on_camera_disconnected()

    def _on_camera_error(self, error):
        """Handle camera stream error."""
        self._add_log("CAMERA", f"Error: {error}")

    def _on_rover_connected(self):
        """Handle rover WebSocket connected."""
        if hasattr(self, '_rover_status'):
            self._rover_status.setText("ONLINE")
            self._rover_status.setStyleSheet("""
                color: #10b981;
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 1px;
            """)

    def _on_rover_disconnected(self):
        """Handle rover WebSocket disconnected."""
        if hasattr(self, '_rover_status'):
            self._rover_status.setText("OFFLINE")
            self._rover_status.setStyleSheet("""
                color: #ef4444;
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 1px;
            """)

    def _on_video_stats(self, stats):
        if hasattr(self, '_ping_display'):
            self._ping_display.update_ping(stats.get("ping_ms", 0))

    def _on_telemetry_received(self, data):
        """Handle telemetry data from ESP32 and update UI elements."""
        self._latest_telemetry = data
        
        # Update sidebar labels
        if hasattr(self, '_temp_label') and "temperature" in data:
            self._temp_label.setText(f"{data['temperature']:.1f}°C")
        if hasattr(self, '_humidity_label') and "humidity" in data:
            self._humidity_label.setText(f"{data['humidity']:.1f}%")
        if hasattr(self, '_gas_label') and "gas" in data:
            self._gas_label.setText(f"{data['gas']:.0f} PPM")
        if hasattr(self, '_distance_card') and "distance" in data:
            distance = data["distance"]
            self._distance_card.update_value(f"{distance:.1f} cm", distance / 2)
        
        # Obstacle warning + auto-brake + speed limit
        if hasattr(self, '_obstacle_warning') and "distance" in data:
            distance = data["distance"]
            threshold = self._config.get("brake_threshold", 30)
            auto_brake = self._config.get("auto_brake", True)
            if auto_brake and distance < threshold:
                self._obstacle_warning.setText(f"⚠ OBSTACLE: {distance:.0f} cm")
                self._obstacle_warning.adjustSize()
                self._obstacle_warning.move(
                    (self._video_canvas.width() - self._obstacle_warning.width()) // 2, 10
                )
                self._obstacle_warning.show()
                if not self._obstacle_brake_active:
                    self._obstacle_brake_active = True
                    self._send_command("stop")
                    self._add_log("SAFETY", f"Auto-brake: {distance:.0f} cm < {threshold} cm → STOP")
            else:
                self._obstacle_warning.hide()
                self._obstacle_brake_active = False

            # Speed limit: 150-255 range, reduced when distance < 150cm (forward only)
            MIN_SPEED = 150
            SPEED_DIST_MAX = 150
            is_reversing = hasattr(self, '_input_handler') and not self._input_handler._driving_forward
            if not is_reversing and distance < SPEED_DIST_MAX:
                ratio = distance / SPEED_DIST_MAX
                ratio = ratio * ratio
                limited = int(MIN_SPEED + (self._global_speed - MIN_SPEED) * ratio)
                limited = max(MIN_SPEED, min(self._global_speed, limited))
                if not self._speed_limit_active or limited != self._current_speed:
                    self._speed_limit_active = True
                    self._current_speed = limited
                    self._send_command(f"speed:{limited}")
                    if hasattr(self, '_speed_label'):
                        self._speed_label.setText(f"{limited}")
                    if hasattr(self, '_speed_meter'):
                        self._speed_meter.set_speed(limited)
            elif self._speed_limit_active:
                self._speed_limit_active = False
                self._current_speed = self._global_speed
                self._send_command(f"speed:{self._global_speed}")
                if hasattr(self, '_speed_label'):
                    self._speed_label.setText(f"{self._global_speed}")
                if hasattr(self, '_speed_meter'):
                    self._speed_meter.set_speed(self._global_speed)
        
        # Update diagnostics sensor cards
        if hasattr(self, '_temp_card') and "temperature" in data:
            temp = data["temperature"]
            self._temp_card.update_value(f"{temp:.1f}°C", temp / 50 * 100)
        if hasattr(self, '_humidity_card') and "humidity" in data:
            humidity = data["humidity"]
            self._humidity_card.update_value(f"{humidity:.1f}%", humidity)
        if hasattr(self, '_gas_card') and "gas" in data:
            gas = data["gas"]
            self._gas_card.update_value(f"{gas:.0f} PPM", gas / 1000 * 100)
        
        # Update link quality
        if hasattr(self, '_link_label') and "link_quality" in data:
            quality = data["link_quality"]
            self._link_label.setText(f"Link: {quality}% ({'Optimal' if quality >= 80 else 'Weak'})")
        
        # Send telemetry data to cloud
        self._cloud_mgr.send_telemetry(data)

    def _on_gimbal_update(self, pan, tilt):
        """Update gimbal UI when manually controlled."""
        self._gimbal_pan = int(pan)
        self._gimbal_tilt = int(tilt)
        if hasattr(self, '_gimbal_pan_input'):
            self._gimbal_pan_input.setText(str(int(pan)))
        if hasattr(self, '_gimbal_tilt_input'):
            self._gimbal_tilt_input.setText(str(int(tilt)))
        if hasattr(self, '_gimbal_hud'):
            self._gimbal_hud.set_gimbal(int(pan), int(tilt))

    def _take_snapshot(self):
        pixmap = self._video_canvas.pixmap() if hasattr(self, '_video_canvas') else None
        self._video_mgr.take_snapshot(pixmap)

    def _emergency_stop(self):
        self._send_command("stop")
        self._add_log("STOP", "Emergency stop activated")
        if self._detection_mgr and self._detection_mgr.follow_mode_active:
            self._detection_mgr.toggle_follow_mode()
    
    def _toggle_chassis_follow(self):
        """Toggle chassis follow mode (v key)."""
        if self._detection_mgr and self._detection_mgr._follow_controller:
            self._detection_mgr._follow_controller.toggle_chassis_follow()

    def _toggle_web_control(self):
        self._allow_remote_control = self._web_control_btn.isChecked()
        self._web_control_btn.setText(
            "WEB CONTROL: ON" if self._allow_remote_control else "WEB CONTROL: OFF"
        )
        self._remote_server.set_allowed(self._allow_remote_control)
        if hasattr(self, '_web_control_banner'):
            self._web_control_banner.setVisible(self._allow_remote_control)
        state = "enabled" if self._allow_remote_control else "disabled"
        self._add_log("REMOTE", f"Web control {state}")
        
        if self._allow_remote_control:
            self._conn_mgr.stop_camera()
            self._add_log("CAMERA", "Camera stopped for remote control")
        else:
            self._conn_mgr.start_camera()
            self._add_log("CAMERA", "Camera reconnected")

    def _relay_command(self, command):
        self._add_log("REMOTE", f"Relay: {command}")
        self._conn_mgr.send_command(command)

    def _send_command(self, command):
        if self._allow_remote_control:
            self._allow_remote_control = False
            self._web_control_btn.setChecked(False)
            self._web_control_btn.setText("WEB CONTROL: OFF")
            self._remote_server.set_allowed(False)
            if hasattr(self, '_web_control_banner'):
                self._web_control_banner.hide()
            self._add_log("REMOTE", "Local input reclaimed control")
        self._add_log("CMD", command)
        self._conn_mgr.send_command(command)
        if command == "stop":
            if hasattr(self, '_speed_meter'):
                self._speed_meter.reset_speed()
            if hasattr(self, '_speed_label'):
                self._speed_label.setText("0")

    def _schedule_speed_apply(self):
        """speed:Nの送信をデバウンスする。スライダーをドラッグしている間は
        何度も呼ばれるが、実際にESP32へ送るのは操作が止まってから150ms後の
        1回だけにする。"""
        self._speed_apply_timer.start(150)

    def _apply_speed_change(self):
        self._send_command(f"speed:{self._global_speed}")

    def _schedule_pid_apply(self):
        """ジャイロ直進PID(/api/pid)の適用をデバウンスする。スライダーを
        ドラッグしている間は何度も呼ばれるが、実際にESP32へ送るのは操作が
        止まってから400ms後の1回だけにする。"""
        self._pid_apply_timer.start(400)

    def _apply_pid_params(self):
        if not hasattr(self, '_kp_slider'):
            return
        params = {
            "kp": round(self._kp_slider.value() / 100.0, 3),
            "ki": round(self._ki_slider.value() / 100.0, 3),
            "kd": round(self._kd_slider.value() / 100.0, 3),
            "enabled": 1 if self._pid_toggle.isChecked() else 0,
            "bias": self._pid_bias_slider.value(),
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"http://{self._config['car_ip']}/api/pid?{query}"
        worker = CloudWorker("GET", url)
        worker.result.connect(lambda data: self._add_log(
            "PID", f"Applied kp={data.get('kp')} ki={data.get('ki')} kd={data.get('kd')} "
                   f"enabled={data.get('enabled')} bias={data.get('bias')}"
        ))
        worker.error.connect(lambda e: self._add_log("PID", f"Apply failed: {e}"))
        self._pid_workers.append(worker)
        worker.finished.connect(lambda: self._pid_workers.remove(worker) if worker in self._pid_workers else None)
        worker.start()

    def _schedule_led_apply(self):
        """LEDスライダー(views/sidebar.py)のドラッグ中に何度も呼ばれるが、
        実際にESP32へ送るのは操作が止まってから300ms後の1回だけにする。"""
        self._led_apply_timer.start(300)

    def _apply_led_from_slider(self):
        if hasattr(self, '_led_slider'):
            self._apply_led(self._led_slider.value())

    def _apply_led(self, value):
        """LED明るさをESP32-Camへ送る。

        ESP32-Cam実機で検証したところ、MJPEGストリーム配信中は他のHTTP
        リクエストを一切処理できず(/api/ledが5秒でタイムアウト)、ストリームを
        切断した直後は65msで正常応答する(API_DOCUMENTATION記載の
        `{"brightness":N,"status":"ok"}`が返る)ことを確認済み。単に非同期化
        しただけではハード側の同時接続不可という制約自体は解決しないため、
        送信の間だけ一瞬カメラ接続を止め、応答が来たら再接続する。"""
        if not hasattr(self, '_esp32_api'):
            return
        self._conn_mgr.stop_camera()
        url = f"http://{self._esp32_api.cam_ip}/api/led?val={value}"
        worker = CloudWorker("GET", url)
        worker.result.connect(lambda data: self._add_log(
            "LED", f"brightness={data.get('brightness')}"
        ))
        worker.error.connect(lambda e: self._add_log("LED", f"Apply failed: {e}"))
        worker.finished.connect(lambda: self._on_led_worker_finished(worker))
        self._led_workers.append(worker)
        worker.start()

    def _on_led_worker_finished(self, worker):
        if worker in self._led_workers:
            self._led_workers.remove(worker)
        self._conn_mgr.start_camera()

    def _add_log(self, category, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {
            "CONNECTED": "#10b981",
            "CMD": "#f1f5f9",
            "SAFETY": "#f59e0b",
            "STOP": "#ef4444",
            "SNAPSHOT": "#06b6d4",
            "REC": "#ef4444",
            "FOLLOW": "#8b5cf6",
            "ERROR": "#ef4444",
        }
        color = colors.get(category, "#94a3b8")
        html = f'<span style="color: #64748b;">[{timestamp}]</span> <span style="color: {color};">[{category}]</span> <span style="color: #94a3b8;">{message}</span>'
        if hasattr(self, '_log_display'):
            try:
                self._log_display.append(html)
            except RuntimeError:
                pass  # アプリ終了処理中にウィジェットが既に破棄されている場合がある
        # GUIのログウィジェットからコピーするのが手間なため、CLI(コンソール)にも
        # 同じログを出力する。GUIウィジェットのスクロール上限で見えなくなった
        # ログも、コンソール出力ならリダイレクトして全件確認できる。
        print(f"[{timestamp}] [{category}] {message}", flush=True)
        if getattr(self, '_log_file', None):
            try:
                self._log_file.write(f"[{timestamp}] [{category}] {message}\n")
                self._log_file.flush()
            except ValueError:
                # follow_controller等のバックグラウンドスレッドがstop()後も
                # 完全に終了するまでに一瞬ラグがあり、アプリ終了時にログファイルを
                # 閉じた直後にこのメソッドが呼ばれることがある(既知のエラー)。
                # 実害はないため無視する。
                pass

    def keyPressEvent(self, event):
        self._input_handler.handle_key_press(event)

    def keyReleaseEvent(self, event):
        self._input_handler.handle_key_release(event)

    def _on_mouse_gimbal(self, pan, tilt):
        self._input_handler._gimbal_pan = int(pan)
        self._input_handler._gimbal_tilt = int(tilt)
        self._gimbal_pan = int(pan)
        self._gimbal_tilt = int(tilt)
        if hasattr(self, '_gimbal_pan_input'):
            self._gimbal_pan_input.setText(str(int(pan)))
        if hasattr(self, '_gimbal_tilt_input'):
            self._gimbal_tilt_input.setText(str(int(tilt)))
        if hasattr(self, '_gimbal_hud'):
            self._gimbal_hud.set_gimbal(int(pan), int(tilt))
        self._send_command(f"servo:{int(pan)},{int(tilt)}")

    def closeEvent(self, event):
        if hasattr(self, '_ota_url_input'):
            self._config["ota_server_url"] = self._ota_url_input.text().strip()
        if hasattr(self, '_video_timer'):
            self._video_timer.stop()
        if self._remote_server:
            self._remote_server.stop()
        self._conn_mgr.stop_all()
        self._detection_mgr.stop_all()
        self._cloud_mgr.stop_all()
        save_config(self._config)
        if hasattr(self, '_log_file') and self._log_file:
            self._log_file.close()
        event.accept()
