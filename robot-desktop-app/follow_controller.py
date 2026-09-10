import math
import queue
import time
import threading
from dataclasses import dataclass
from enum import Enum
from queue import Queue
from typing import Optional, Callable


class FollowState(Enum):
    FOLLOWING = "following"
    TURNING = "turning"
    WAITING = "waiting"
    SEARCHING = "searching"


@dataclass
class FollowConfig:
    """Configuration for follow mode controller."""
    yaw_deadband: float = 5.0
    yaw_max: float = 45.0
    min_distance: float = 0.3
    max_distance: float = 2.0
    follow_distance: float = 0.4
    base_speed: int = 180
    turn_speed: int = 150
    control_rate_hz: float = 10.0
    min_confidence: float = 0.3
    turn_start_dist: float = 1.0
    stop_dist: float = 0.4
    turn_complete_yaw: float = 30.0
    follow_max_yaw: float = 60.0
    # Camera mounting offset relative to car chassis (degrees)
    # Positive = camera rotated right, Negative = camera rotated left
    camera_yaw_offset: float = 0.0


class DetectionThread(threading.Thread):
    def __init__(self, input_queue: Queue, output_queue: Queue, config: FollowConfig, log_callback=None):
        super().__init__(daemon=True)
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.config = config
        self._running = False
        self._log = log_callback
        self._count = 0

    def run(self):
        self._running = True
        if self._log:
            self._log("FOLLOW", "DetectionThread開始")
        while self._running:
            try:
                detection = self.input_queue.get(timeout=0.1)
                result = self._process_detection(detection)
                try:
                    self.output_queue.put_nowait(result)
                except:
                    pass
                self._count += 1
                if self._log and self._count % 10 == 0:
                    self._log("FOLLOW", f"[DetectionThread] 処理数: {self._count} qsize_in={self.input_queue.qsize()} qsize_out={self.output_queue.qsize()}")
            except:
                continue

    def _process_detection(self, detection: dict) -> dict:
        yaw_deg = detection.get("yaw_deg")
        dist_m = detection.get("dist_m")
        confidence = detection.get("confidence", 0.0)
        bbox = detection.get("bbox")
        frame_w = detection.get("frame_w", 640)
        frame_h = detection.get("frame_h", 480)
        
        valid = (yaw_deg is not None and dist_m is not None and 
                confidence >= self.config.min_confidence and
                self.config.min_distance <= dist_m <= self.config.max_distance)
        
        return {
            "valid": valid,
            "yaw_deg": yaw_deg,
            "dist_m": dist_m,
            "confidence": confidence,
            "bbox": bbox,
            "frame_w": frame_w,
            "frame_h": frame_h,
            "timestamp": time.time()
        }

    def stop(self):
        self._running = False


class GimbalThread(threading.Thread):
    """High-speed gimbal tracking thread (~20 Hz, independent of motor control).
    
    Based on ai_tracker_reference.py 2-Tier Visual Servoing:
    - Tapered gain controller (anti-oscillation)
    - Headroom safety margin (keep head at 15% from top)
    - Hip centering (hips at 55% of frame height)
    """
    def __init__(self, set_gimbal: Callable[[int, int], None], log_callback=None):
        super().__init__(daemon=True)
        self._set_gimbal = set_gimbal
        self._log = log_callback
        self._running = False
        self._frame_lock = threading.Lock()
        self._bbox = None
        self._frame_w = 640
        self._frame_h = 480
        # Gimbal state
        self._current_pan = 90.0
        self._current_tilt = 90.0
        # Gimbal center position (degrees)
        self._gimbal_center_pan = 90.0
        # Reference parameters (from ai_tracker_reference.py)
        self._pan_gain = 7.0
        self._tilt_gain = 5.5
        self._smooth_pan_step = 0.0
        self._smooth_tilt_step = 0.0
        self._max_step = 3.0
        # Tapered gain parameters (reference: TAPER_START=0.30, GAIN_FLOOR=0.35)
        self._taper_start = 0.30
        self._gain_floor = 0.35
        # Headroom safety: keep head at 15% from top
        self._headroom_target = 0.15
        # Search state
        self._search_state = "tracking"
        self._last_seen_side = "center"
        self._search_start_pan = 90.0
        self._search_timer = 0.0
        self._search_timeout = 3.0
        self._spin_speed = 1.5
        self._spin_range = 60.0
        # Camera connection state
        self._camera_connected = False
        self._camera_stable_since = 0.0
        self._camera_stable_delay = 2.0

    def update_detection(self, bbox, frame_w: int, frame_h: int):
        """Update detection data (thread-safe, called from main thread)."""
        with self._frame_lock:
            self._bbox = bbox
            self._frame_w = frame_w
            self._frame_h = frame_h

    def on_camera_connected(self):
        """Called when camera stream connects."""
        self._camera_connected = True
        self._camera_stable_since = time.time()
        if self._log:
            self._log("FOLLOW", "[Gimbal] カメラ接続 - 安定するまで待機")

    def on_camera_disconnected(self):
        """Called when camera stream disconnects."""
        self._camera_connected = False
        self._search_state = "tracking"
        self._smooth_pan_step = 0.0
        self._smooth_tilt_step = 0.0
        if self._log:
            self._log("FOLLOW", "[Gimbal] カメラ切断 - 停止")

    def get_camera_yaw_offset(self) -> float:
        """Get camera yaw offset based on current gimbal pan angle.
        
        Returns offset in degrees:
        - Positive: camera rotated right from center
        - Negative: camera rotated left from center
        - 0: camera facing forward (gimbal at center)
        """
        return self._current_pan - self._gimbal_center_pan

    def run(self):
        self._running = True
        if self._log:
            self._log("FOLLOW", "GimbalThread開始 (~20Hz)")
        while self._running:
            try:
                if not self._camera_connected:
                    time.sleep(0.1)
                    continue
                
                elapsed_since_connect = time.time() - self._camera_stable_since
                if elapsed_since_connect < self._camera_stable_delay:
                    time.sleep(0.1)
                    continue
                
                with self._frame_lock:
                    bbox = self._bbox
                    frame_w = self._frame_w
                    frame_h = self._frame_h
                
                if bbox is not None:
                    self._track_target(bbox, frame_w, frame_h)
                else:
                    self._search_target()
                
                time.sleep(0.05)  # ~20 Hz
            except Exception as e:
                if self._log:
                    self._log("FOLLOW", f"[Gimbal] エラー: {e}")
                time.sleep(0.05)

    def _track_target(self, bbox, frame_w: int, frame_h: int):
        """Compute and send gimbal command to center target.
        
        Uses reference architecture:
        - Tapered gain: full gain for large errors, gentle near setpoint
        - Headroom safety: keeps head at 15% from top
        - Hip centering: centers on lower body at 55%
        """
        bx, by, bw, bh = bbox
        cx = bx + bw / 2.0
        
        # Reset search state when target is found
        if self._search_state != "tracking":
            self._search_state = "tracking"
            self._smooth_pan_step = 0.0
            self._smooth_tilt_step = 0.0
        
        # Remember which side the target is on
        if cx < frame_w * 0.4:
            self._last_seen_side = "left"
        elif cx > frame_w * 0.6:
            self._last_seen_side = "right"
        else:
            self._last_seen_side = "center"
        
        # Reference: Dynamic Framing with Headroom Safety Margin
        # Head at 15% from top, hips at 55% of frame height
        head_y = by  # Top of head
        hip_y = by + bh * 0.55  # Hip level (lower body center)
        
        # Headroom error: head should be at 15% from top
        desired_head_y = frame_h * self._headroom_target
        head_error = (head_y - desired_head_y) / (frame_h / 2.0)
        
        # Hip error: hips should be at 55% of frame height
        hip_error = (hip_y - (frame_h * 0.55)) / (frame_h / 2.0)
        
        # Combined vertical error (weighted blend)
        error_y = 0.55 * head_error + 0.45 * hip_error
        
        # Horizontal error
        error_x = (cx - frame_w / 2.0) / (frame_w / 2.0)
        
        # Reference: Tapered Gain Controller (anti-oscillation)
        # Large offset → full gain for fast snap
        # Small offset → reduced gain for gentle settling
        if abs(error_x) > 0.05 or abs(error_y) > 0.05:
            pan_scale = self._gain_floor + (1.0 - self._gain_floor) * min(1.0, abs(error_x) / self._taper_start)
            tilt_scale = self._gain_floor + (1.0 - self._gain_floor) * min(1.0, abs(error_y) / self._taper_start)
            
            target_pan_step = error_x * self._pan_gain * pan_scale
            target_tilt_step = error_y * self._tilt_gain * tilt_scale
            
            # Reference: EMA damping (0.55 new + 0.45 old)
            smooth_p = 0.55 * target_pan_step + 0.45 * self._smooth_pan_step
            smooth_t = 0.55 * target_tilt_step + 0.45 * self._smooth_tilt_step
            self._smooth_pan_step = smooth_p
            self._smooth_tilt_step = smooth_t
            
            # Speed limit
            smooth_p = max(-self._max_step, min(self._max_step, smooth_p))
            smooth_t = max(-self._max_step, min(self._max_step, smooth_t))
            
            # Update pan/tilt (servo range 0-180, center=90)
            self._current_pan = max(0, min(180, self._current_pan - smooth_p))
            self._current_tilt = max(0, min(180, self._current_tilt + smooth_t))
            
            if self._set_gimbal:
                self._set_gimbal(int(self._current_pan), int(self._current_tilt))
        else:
            # Inside deadband: stop and hold position
            self._smooth_pan_step = 0.0
            self._smooth_tilt_step = 0.0

    def _search_target(self):
        """Search for target when lost."""
        now = time.time()
        
        if self._search_state == "tracking":
            # Target just lost: start searching in the last seen direction
            self._search_state = "search_direction"
            self._search_start_pan = self._current_pan
            self._search_timer = now
            if self._log:
                self._log("FOLLOW", f"[Gimbal] 車をlost → {self._last_seen_side}方向を探索")
        
        if self._search_state == "search_direction":
            # Search in the direction where target was last seen
            elapsed = now - self._search_timer
            
            if self._last_seen_side == "right":
                # Search right (decrease pan)
                pan_step = -1.0
            elif self._last_seen_side == "left":
                # Search left (increase pan)
                pan_step = 1.0
            else:
                # Center: search right first
                pan_step = -1.0
            
            self._current_pan = max(0, min(180, self._current_pan + pan_step))
            
            if self._set_gimbal:
                self._set_gimbal(int(self._current_pan), int(self._current_tilt))
            
            # If search timeout or hit servo limit, switch to spin search
            if elapsed > self._search_timeout or self._current_pan <= 5 or self._current_pan >= 175:
                self._search_state = "search_spin"
                self._search_start_pan = self._current_pan
                self._search_timer = now
                if self._log:
                    self._log("FOLLOW", "[Gimbal] 方向探索失敗 → ぐるぐる探索")
        
        if self._search_state == "search_spin":
            # Spin around to find target
            elapsed = now - self._search_timer
            
            # Alternating left-right sweep
            cycle_pos = (elapsed * 0.5) % 2.0  # 2 second cycle
            if cycle_pos < 1.0:
                pan_step = self._spin_speed
            else:
                pan_step = -self._spin_speed
            
            self._current_pan = max(0, min(180, self._current_pan + pan_step))
            
            if self._set_gimbal:
                self._set_gimbal(int(self._current_pan), int(self._current_tilt))
            
            # Limit total spin range
            if abs(self._current_pan - self._search_start_pan) > self._spin_range:
                # Reverse direction
                self._spin_speed = -self._spin_speed

    def stop(self):
        self._running = False


class ControlThread(threading.Thread):
    """ControlThread implementing reference architecture algorithm.
    
    Based on ai_tracker_reference.py 2-Tier Visual Servoing:
    - Tier 1: Gimbal visual servoing (handled by GimbalThread)
    - Tier 2: Linear PID distance + Combined heading error steering
    
    Key differences from standard approach:
    - Linear PID for distance (KP=70, KI=0.4, KD=10)
    - Combined heading: 0.15 * error_x + 0.85 * pan_error
    - Rate limiting (MAX_V_STEP = 60)
    - Occlusion guard (DIST_JUMP_LIMIT_M = 0.6)
    - Distance golden band (±0.15m → stop & hold)
    - Turn-only heading error gate (0.35)
    """
    def __init__(self, input_queue: Queue, output_queue: Queue, config: FollowConfig, log_callback=None):
        super().__init__(daemon=True)
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.config = config
        self._running = False
        self._log = log_callback
        self._count = 0
        self.state = FollowState.SEARCHING
        self.target_distance = config.follow_distance
        self._filtered_yaw = 0.0
        self._yaw_filter_alpha = 0.3
        # Chassis follow flag (set by FollowController)
        self.chassis_follow_enabled = False
        # Reference to GimbalThread for automatic camera offset
        self._gimbal_thread = None
        
        # Reference algorithm parameters
        self._kp_lin = 70.0    # Linear PID proportional
        self._ki_lin = 0.4     # Linear PID integral
        self._kd_lin = 10.0    # Linear PID derivative
        self._err_lin_i = 0.0  # Integral accumulator
        self._prev_err_lin = 0.0
        self._prev_dist_m = None
        self._last_cmd_t = 0.0
        
        # Rate limiting
        self._max_v_step = 60
        self._prev_v_cmd = 0
        
        # Occlusion guard
        self._dist_jump_limit = 0.6

    def run(self):
        self._running = True
        if self._log:
            self._log("FOLLOW", "ControlThread開始 (参照アーキテクチャ)")
        while self._running:
            try:
                detection = self.input_queue.get(timeout=0.1)
                command = self._compute_command(detection)
                try:
                    self.output_queue.put_nowait(command)
                except:
                    pass
                self._count += 1
                if self._log and self._count % 10 == 0:
                    self._log("FOLLOW", f"[ControlThread] 処理数: {self._count}")
            except queue.Empty:
                continue
            except Exception as e:
                if self._log:
                    self._log("FOLLOW", f"[ControlThread] エラー: {type(e).__name__}: {e}")
                continue

    def _compute_command(self, detection: dict) -> dict:
        """Compute motor command using reference architecture algorithm."""
        yaw_deg = detection.get("yaw_deg")
        dist_m = detection.get("dist_m")
        confidence = detection.get("confidence", 0.0)
        
        if yaw_deg is None or dist_m is None:
            return self._stop_command("データなし")
        
        # Automatically get camera yaw offset from GimbalThread
        if self._gimbal_thread:
            camera_offset = self._gimbal_thread.get_camera_yaw_offset()
        else:
            camera_offset = self.config.camera_yaw_offset
        yaw_deg = yaw_deg + camera_offset
        
        if confidence < self.config.min_confidence:
            return self._stop_command(f"信頼度不足({confidence:.2f})")
        
        if dist_m > self.config.max_distance:
            return self._stop_command(f"遠すぎ({dist_m:.2f}m)")
        
        if dist_m < self.config.stop_dist:
            return self._stop_command(f"近すぎ({dist_m:.2f}m)")
        
        # Rate limit control ticks (12.5 Hz max)
        now = time.time()
        dt = max(0.02, now - self._last_cmd_t)
        if dt < 0.080:
            return None
        self._last_cmd_t = now
        
        # Occlusion guard: hold last distance if jump is too large
        if self._prev_dist_m is not None and abs(dist_m - self._prev_dist_m) > self._dist_jump_limit:
            dist_m = self._prev_dist_m
        else:
            self._prev_dist_m = dist_m
        
        # A. Linear PID for distance control
        err_lin = dist_m - self.target_distance
        self._err_lin_i += err_lin * dt
        self._err_lin_i = max(-3.0, min(3.0, self._err_lin_i))  # anti-windup
        d_err_lin = (err_lin - self._prev_err_lin) / dt
        self._prev_err_lin = err_lin
        
        lin_v = (self._kp_lin * err_lin
                 + self._ki_lin * self._err_lin_i
                 + self._kd_lin * d_err_lin)
        
        # B. Combined heading error (reference: 0.15 * error_x + 0.85 * pan_error)
        # error_x: normalized horizontal error in frame
        error_x = yaw_deg / 45.0  # normalize yaw to -1..1 range
        # pan_error: gimbal offset from center (0.0 = centered)
        if self._gimbal_thread:
            pan_angle = self._gimbal_thread._current_pan
        else:
            pan_angle = 90.0
        pan_error = (90.0 - pan_angle) / 90.0  # positive = camera rotated left
        
        combined_heading_error = 0.15 * error_x + 0.85 * pan_error
        
        # C. Distance golden band: ±0.15m → stop & hold
        TURN_ONLY_HEADING_ERROR = 0.35
        if abs(err_lin) <= 0.15 and abs(combined_heading_error) <= 0.05:
            v_cmd = 0
            self._prev_v_cmd = 0
            self._err_lin_i = 0.0
            self._prev_err_lin = 0.0
            return self._stop_command("ホールド")
        
        # D. Steering decision
        if abs(combined_heading_error) > TURN_ONLY_HEADING_ERROR:
            # Too much heading error → turn in place
            if combined_heading_error > 0:
                command = "left"
            else:
                command = "right"
            v_cmd = 0
            speed = self.config.turn_speed
        elif err_lin > 0.15:
            # Person is far → move forward
            v_cmd = int(max(110, min(245, 140 + lin_v)))
            command = "forward"
            speed = max(150, min(255, v_cmd))
        elif err_lin < -0.20:
            # Person is close → reverse
            v_cmd = int(max(-220, min(-100, -130 + lin_v)))
            command = "backward"
            speed = max(150, min(255, abs(v_cmd)))
        else:
            # In golden band but heading needs correction
            v_cmd = 0
            if abs(combined_heading_error) > 0.05:
                command = "left" if combined_heading_error > 0 else "right"
                speed = self.config.turn_speed
            else:
                command = "stop"
                speed = 0
        
        # E. Rate limit v_cmd
        v_cmd = int(max(self._prev_v_cmd - self._max_v_step,
                        min(self._prev_v_cmd + self._max_v_step, v_cmd)))
        self._prev_v_cmd = v_cmd
        
        return {
            "type": "control",
            "command": command,
            "speed": speed,
            "log": f"heading:{combined_heading_error:+.2f} dist:{err_lin:+.2f}m {command}"
        }

    def _stop_command(self, reason: str) -> dict:
        return {
            "type": "control",
            "command": "stop",
            "speed": 0,
            "log": f"停止:{reason}"
        }

    def stop(self):
        self._running = False
        self._err_lin_i = 0.0
        self._prev_err_lin = 0.0
        self._prev_v_cmd = 0


class CommandThread(threading.Thread):
    def __init__(self, input_queue: Queue, send_command: Callable[[str], None], 
                 set_speed: Callable[[int], None], log_callback: Callable[[str, str], None]):
        super().__init__(daemon=True)
        self.input_queue = input_queue
        self.send_command = send_command
        self.set_speed = set_speed
        self.log_callback = log_callback
        self._running = False
        self._cmd_count = 0

    def run(self):
        self._running = True
        if self.log_callback:
            self.log_callback("FOLLOW", f"CommandThread開始 log_callback={self.log_callback is not None}")
        while self._running:
            try:
                command_data = self.input_queue.get(timeout=0.1)
                self._execute_command(command_data)
            except:
                continue

    def _execute_command(self, command_data: dict):
        command = command_data.get("command", "stop")
        speed = command_data.get("speed", 0)
        log = command_data.get("log", "")
        chassis_enabled = command_data.get("chassis_enabled", False)
        
        self._cmd_count += 1
        
        if self.log_callback:
            self.log_callback("FOLLOW", f"[CTRL] {log}")
        
        # Send motor command (Tier 2: only when chassis enabled)
        if chassis_enabled:
            if self.send_command:
                self.send_command(command)
            if self.set_speed and speed > 0:
                self.set_speed(speed)

    def stop(self):
        self._running = False


class FollowController:
    def __init__(self, config: FollowConfig = None, dry_run: bool = False,
                 send_command: Callable[[str], None] = None,
                 set_speed: Callable[[int], None] = None,
                 set_gimbal: Callable[[int, int], None] = None,
                 log_callback: Callable[[str, str], None] = None):
        self.config = config or FollowConfig()
        self._dry_run = dry_run
        self._log_callback = log_callback
        self._send_command = send_command
        self._set_speed = set_speed
        self._set_gimbal = set_gimbal
        
        self._detection_queue = Queue(maxsize=10)
        self._control_queue = Queue(maxsize=10)
        self._command_queue = Queue(maxsize=10)
        
        self._gimbal_thread = None
        self._detection_thread = None
        self._control_thread = None
        self._command_thread = None
        self._active = False
        
        # Chassis follow: True = gimbal + car, False = gimbal only
        self._chassis_follow_enabled = False
        
        # Low-pass filter for yaw smoothing
        self._yaw_filter_alpha = 0.3  # 0.0 = no filter, 1.0 = instant
        self._filtered_yaw = 0.0
    
    def toggle_chassis_follow(self):
        """Toggle chassis follow mode (v key)."""
        self._chassis_follow_enabled = not self._chassis_follow_enabled
        state = "有効" if self._chassis_follow_enabled else "無効"
        if self._log_callback:
            self._log_callback("FOLLOW", f"車体追従: {state}")
        if self._control_thread:
            self._control_thread.chassis_follow_enabled = self._chassis_follow_enabled
        if not self._chassis_follow_enabled:
            # Stop motors when disabling chassis follow
            if self._send_command:
                self._send_command("stop")

    def start(self):
        self._active = True
        self._filtered_yaw = 0.0
        
        # Gimbal thread (high-speed, ~20 Hz)
        self._gimbal_thread = GimbalThread(self._set_gimbal, self._log_callback)
        
        self._detection_thread = DetectionThread(
            self._detection_queue, self._control_queue, self.config, self._log_callback
        )
        self._control_thread = ControlThread(
            self._control_queue, self._command_queue, self.config, self._log_callback
        )
        # Set gimbal thread reference for automatic camera offset
        self._control_thread._gimbal_thread = self._gimbal_thread
        self._command_thread = CommandThread(
            self._command_queue, self._send_command, self._set_speed, self._log_callback
        )
        
        self._gimbal_thread.start()
        self._detection_thread.start()
        self._control_thread.start()
        self._command_thread.start()
        
        if self._log_callback:
            self._log_callback("FOLLOW", "追従制御を開始しました（4スレッド: Gimbal/Detection/Control/Command）")

    def stop(self):
        self._active = False
        
        if self._gimbal_thread:
            self._gimbal_thread.stop()
        if self._detection_thread:
            self._detection_thread.stop()
        if self._control_thread:
            self._control_thread.stop()
        if self._command_thread:
            self._command_thread.stop()
        
        if self._send_command:
            self._send_command("stop")
        
        self._log_callback("FOLLOW", "追従制御を停止しました")

    def update(self, detection: dict):
        if not self._active:
            return
        
        # Send to gimbal thread (high-speed tracking)
        if self._gimbal_thread:
            self._gimbal_thread.update_detection(
                detection.get("bbox"),
                detection.get("frame_w", 640),
                detection.get("frame_h", 480)
            )
        
        # Send to motor control pipeline
        qsize = self._detection_queue.qsize()
        try:
            self._detection_queue.put_nowait(detection)
            if self._log_callback and qsize == 0:
                yaw = detection.get("yaw_deg")
                dist = detection.get("dist_m")
                self._log_callback("FOLLOW", f"[UPDATE] yaw={yaw} dist={dist} qsize={qsize}")
        except Exception as e:
            if self._log_callback:
                self._log_callback("FOLLOW", f"[UPDATE] queue full: {e}")

    def get_status(self) -> dict:
        return {
            "active": self._active,
            "state": self._control_thread.state.value if self._control_thread else "unknown",
            "queues": {
                "detection": self._detection_queue.qsize(),
                "control": self._control_queue.qsize(),
                "command": self._command_queue.qsize()
            }
        }
