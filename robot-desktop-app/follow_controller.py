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


class PIDController:
    def __init__(self, kp: float = 1.0, ki: float = 0.0, kd: float = 0.1) -> None:
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self._prev_error = 0.0
        self._integral = 0.0

    def compute(self, error: float, dt: float = 0.1) -> float:
        self._integral += error * dt
        derivative = (error - self._prev_error) / dt if dt > 0 else 0.0
        self._prev_error = error
        return self.kp * error + self.ki * self._integral + self.kd * derivative

    def reset(self) -> None:
        self._prev_error = 0.0
        self._integral = 0.0


class StanleyController:
    def __init__(self, k: float = 0.5, max_steer: float = 30.0) -> None:
        self.k = k
        self.max_steer = max_steer

    def control(self, yaw_deg: float, dist_m: float, speed: float) -> float:
        psi = math.radians(yaw_deg)
        e = dist_m * math.sin(psi)
        if speed > 0.1:
            delta = psi + math.atan2(self.k * e, speed)
        else:
            delta = psi
        delta_deg = max(-self.max_steer, min(self.max_steer, math.degrees(delta)))
        return delta_deg


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
    """High-speed gimbal tracking thread (~20 Hz, independent of motor control)."""
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
        self._pan_gain = 3.0
        self._tilt_gain = 2.5
        self._smooth_pan_step = 0.0
        self._smooth_tilt_step = 0.0
        self._max_step = 2.0
        # Search state
        self._search_state = "tracking"  # tracking / search_direction / search_spin
        self._last_seen_side = "center"  # left / right / center
        self._search_start_pan = 90.0
        self._search_timer = 0.0
        self._search_timeout = 3.0
        self._spin_speed = 1.5
        self._spin_range = 60.0
        # Camera connection state
        self._camera_connected = False
        self._camera_stable_since = 0.0
        self._camera_stable_delay = 2.0  # seconds to wait after reconnection

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

    def run(self):
        self._running = True
        if self._log:
            self._log("FOLLOW", "GimbalThread開始 (~20Hz)")
        while self._running:
            try:
                # Wait for camera to be stable after reconnection
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
        """Compute and send gimbal command to center target."""
        bx, by, bw, bh = bbox
        cx = bx + bw / 2.0
        cy = by + bh / 2.0
        
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
        
        # Normalized error (-1 to 1)
        error_x = (cx - frame_w / 2.0) / (frame_w / 2.0)
        error_y = (cy - frame_h / 2.0) / (frame_h / 2.0)
        
        # Only move if target is significantly off-center
        if abs(error_x) > 0.15 or abs(error_y) > 0.15:
            target_pan_step = error_x * self._pan_gain
            target_tilt_step = error_y * self._tilt_gain
            
            # Heavy EMA damping
            smooth_p = 0.40 * target_pan_step + 0.60 * self._smooth_pan_step
            smooth_t = 0.40 * target_tilt_step + 0.60 * self._smooth_tilt_step
            self._smooth_pan_step = smooth_p
            self._smooth_tilt_step = smooth_t
            
            # Speed limit
            smooth_p = max(-self._max_step, min(self._max_step, smooth_p))
            smooth_t = max(-self._max_step, min(self._max_step, smooth_t))
            
            # Update pan/tilt
            self._current_pan = max(0, min(180, self._current_pan - smooth_p))
            self._current_tilt = max(0, min(180, self._current_tilt + smooth_t))
            
            if self._set_gimbal:
                self._set_gimbal(int(self._current_pan), int(self._current_tilt))
        else:
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
    def __init__(self, input_queue: Queue, output_queue: Queue, config: FollowConfig, log_callback=None):
        super().__init__(daemon=True)
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.config = config
        self._running = False
        self._log = log_callback
        self._count = 0
        self.state = FollowState.SEARCHING
        self.pid_distance = PIDController(kp=1.0, ki=0.0, kd=0.1)
        self.stanley = StanleyController(k=0.5, max_steer=30.0)
        self.target_distance = config.follow_distance
        self._filtered_yaw = 0.0
        self._yaw_filter_alpha = 0.3
        # Chassis follow flag (set by FollowController)
        self.chassis_follow_enabled = False

    def run(self):
        self._running = True
        if self._log:
            self._log("FOLLOW", "ControlThread開始")
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
        yaw_deg = detection.get("yaw_deg")
        dist_m = detection.get("dist_m")
        confidence = detection.get("confidence", 0.0)
        
        if yaw_deg is None or dist_m is None:
            return self._stop_command("データなし")
        
        if confidence < self.config.min_confidence:
            return self._stop_command(f"信頼度不足({confidence:.2f})")
        
        if dist_m > self.config.max_distance:
            return self._stop_command(f"遠すぎ({dist_m:.2f}m)")
        
        if dist_m < self.config.stop_dist:
            return self._stop_command(f"近すぎ({dist_m:.2f}m)")
        
        self._check_transitions(yaw_deg, dist_m)
        
        # Always compute following command for logging
        following_result = self._following_command(yaw_deg, dist_m)
        
        if self.state == FollowState.FOLLOWING:
            result = following_result
        elif self.state == FollowState.TURNING:
            result = self._turning_command(yaw_deg)
        elif self.state == FollowState.WAITING:
            result = self._waiting_command()
        else:
            result = self._searching_command()
        
        result["chassis_enabled"] = self.chassis_follow_enabled
        return result
    
    def _check_transitions(self, yaw_deg: float, dist_m: float) -> None:
        old_state = self.state
        if self.state == FollowState.FOLLOWING:
            if dist_m < self.config.stop_dist:
                self.state = FollowState.WAITING
        elif self.state == FollowState.TURNING:
            if abs(yaw_deg) < self.config.turn_complete_yaw:
                self.state = FollowState.FOLLOWING
            elif dist_m < self.config.stop_dist:
                self.state = FollowState.WAITING
        elif self.state == FollowState.WAITING:
            if abs(yaw_deg) < self.config.turn_complete_yaw:
                self.state = FollowState.FOLLOWING
        elif self.state == FollowState.SEARCHING:
            if abs(yaw_deg) < self.config.follow_max_yaw:
                self.state = FollowState.FOLLOWING
            elif yaw_deg != 0:
                self.state = FollowState.TURNING
        
        if old_state != self.state:
            return {
                "type": "transition",
                "from": old_state.value,
                "to": self.state.value,
                "yaw": yaw_deg,
                "dist": dist_m
            }
        return None

    def _following_command(self, yaw_deg: float, dist_m: float) -> dict:
        # Apply low-pass filter to smooth yaw
        self._filtered_yaw = self._yaw_filter_alpha * yaw_deg + (1 - self._yaw_filter_alpha) * self._filtered_yaw
        
        # Apply deadband
        if abs(self._filtered_yaw) < self.config.yaw_deadband:
            steering = 0.0
            steer_method = "deadband"
        else:
            # For large yaw angles, use a simpler proportional control
            if abs(self._filtered_yaw) > 90:
                # Car is behind or to the side - turn towards it
                steering = self.config.max_steer if self._filtered_yaw > 0 else -self.config.max_steer
                steer_method = "max"
            else:
                steering = self.stanley.control(self._filtered_yaw, dist_m, self.config.base_speed / 100.0)
                steer_method = "Stanley"
        
        dist_error = dist_m - self.target_distance
        throttle = self.pid_distance.compute(dist_error)
        
        # When yaw is small (deadband) and far from target, move forward aggressively
        if abs(self._filtered_yaw) < self.config.yaw_deadband and dist_error > 0.05:
            throttle = max(0.3, min(1.0, throttle))
        else:
            throttle = max(0.0, min(1.0, throttle))
        
        if abs(steering) < 5:
            command = "forward"
        elif steering > 0:
            command = "right"
        else:
            command = "left"
            
        speed = int(throttle * self.config.base_speed)
        if command != "stop":
            speed = max(150, speed)
        
        return {
            "type": "control",
            "command": command,
            "speed": speed,
            "log": f"旋回:{steer_method}({steering:+.1f}°) 速度:PID({speed}) {command}"
        }

    def _turning_command(self, yaw_deg: float) -> dict:
        command = "right" if yaw_deg > 0 else "left"
        return {
            "type": "control",
            "command": command,
            "speed": 80,
            "log": f"旋回:直接 yaw:{yaw_deg:+.1f}° 速度:固定(80)"
        }

    def _waiting_command(self) -> dict:
        return {
            "type": "control",
            "command": "stop",
            "speed": 0,
            "log": "停止:待機中"
        }

    def _searching_command(self) -> dict:
        return {
            "type": "control",
            "command": "forward",
            "speed": 50,
            "log": "探索:前進 速度:固定(50)"
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
        self.pid_distance.reset()


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
