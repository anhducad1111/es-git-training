import math
import queue
import time
import threading
from dataclasses import dataclass
from enum import Enum
from queue import Queue
from typing import Optional, Callable

from rho_alpha_beta_control import RhoAlphaBetaController, RhoAlphaBetaConfig


class FollowState(Enum):
    FOLLOWING = "following"
    TURNING = "turning"
    WAITING = "waiting"
    SEARCHING = "searching"
    HEAD_ON_HOLD = "head_on_hold"
    HOLDING = "holding"
    APPROACHING_BLIND = "approaching_blind"
    LOST_TIMEOUT = "lost_timeout"
    REPOSITIONING = "repositioning"


@dataclass
class FollowConfig:
    """Configuration for follow mode controller."""
    yaw_deadband: float = 5.0
    yaw_max: float = 45.0
    min_distance: float = 0.3
    max_distance: float = 2.0
    follow_distance: float = 0.5
    distance_band: float = 0.15
    base_speed: int = 150
    turn_speed: int = 160
    control_rate_hz: float = 10.0
    min_confidence: float = 0.3
    turn_start_dist: float = 1.0
    stop_dist: float = 0.7
    turn_complete_yaw: float = 30.0
    follow_max_yaw: float = 60.0
    camera_yaw_offset: float = 0.0
    min_pwm: int = 150
    blind_approach_pwm: int = 150
    head_on_threshold: float = 20.0
    state_hysteresis_frames: int = 3
    lost_timeout_sec: float = 5.0
    reposition_yaw_threshold: float = 45.0
    k_rho: float = 0.6
    k_alpha: float = 1.5
    k_beta: float = -0.6


def wrap_angle(deg: float) -> float:
    """Normalize an angle in degrees to [-180, 180)."""
    return (deg + 180.0) % 360.0 - 180.0


def resolve_follow_state(
    yaw_deg: float | None,
    dist_m: float | None,
    bbox: tuple | None,
    config: FollowConfig,
    bearing_deg: float | None = None,
    repositioning_enabled: bool = True,
) -> FollowState:
    """Single-frame state resolution (no hysteresis). Priority: head-on > repositioning > bbox visibility > yaw/dist availability > distance band."""
    if yaw_deg is not None:
        wrapped = wrap_angle(yaw_deg)
        if abs(wrapped) >= 180.0 - config.head_on_threshold:
            return FollowState.HEAD_ON_HOLD

    if (
        repositioning_enabled
        and yaw_deg is not None
        and bearing_deg is not None
        and dist_m is not None
        and bbox is not None
        and abs(wrap_angle(yaw_deg)) > config.reposition_yaw_threshold
    ):
        return FollowState.REPOSITIONING

    if bbox is None:
        return FollowState.SEARCHING

    if yaw_deg is None or dist_m is None:
        return FollowState.APPROACHING_BLIND

    lower = config.follow_distance - config.distance_band
    upper = config.follow_distance + config.distance_band
    if lower <= dist_m <= upper:
        return FollowState.HOLDING

    return FollowState.FOLLOWING


def compute_goal_pose(
    bearing_deg: float,
    dist_m: float,
    yaw_deg: float,
    follow_distance: float,
) -> tuple[float, float, float]:
    """Compute polar (rho, alpha, beta) goal for tail repositioning.

    Returns (rho_goal, alpha_goal, beta_goal) in ego frame.
    """
    bearing_rad = math.radians(bearing_deg)
    yaw_rad = math.radians(yaw_deg)

    target_x = dist_m * math.sin(bearing_rad)
    target_z = dist_m * math.cos(bearing_rad)

    fwd_x = math.sin(yaw_rad)
    fwd_z = math.cos(yaw_rad)

    goal_x = target_x - follow_distance * fwd_x
    goal_z = target_z - follow_distance * fwd_z

    rho_goal = math.hypot(goal_x, goal_z)
    alpha_goal = math.degrees(math.atan2(goal_x, goal_z)) if rho_goal > 1e-6 else 0.0
    beta_goal = wrap_angle(yaw_deg - alpha_goal)

    return rho_goal, alpha_goal, beta_goal


class StateHysteresis:
    """Confirms a state transition only after the same candidate state has
    been observed for `config.state_hysteresis_frames` consecutive updates.
    HEAD_ON_HOLD is safety-critical and bypasses hysteresis (confirmed immediately)."""

    def __init__(self, config: FollowConfig, initial_state: FollowState = FollowState.SEARCHING) -> None:
        self._config = config
        self._confirmed_state = initial_state
        self._pending_state: FollowState | None = None
        self._pending_count = 0

    def update(self, candidate_state: FollowState) -> FollowState:
        if candidate_state == FollowState.HEAD_ON_HOLD:
            self._confirmed_state = FollowState.HEAD_ON_HOLD
            self._pending_state = None
            self._pending_count = 0
            return self._confirmed_state

        if candidate_state == self._pending_state:
            self._pending_count += 1
        else:
            self._pending_state = candidate_state
            self._pending_count = 1

        if self._pending_count >= self._config.state_hysteresis_frames:
            self._confirmed_state = candidate_state

        return self._confirmed_state


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
            "timestamp": time.time(),
            "bearing_deg": detection.get("bearing_deg"),
            "theta_deg": detection.get("theta_deg"),
            "gimbal_pan_deg": detection.get("gimbal_pan_deg"),
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
        self._current_tilt = 75.0
        # Gimbal center position (degrees)
        self._gimbal_center_pan = 90.0
        # Reference parameters (from ai_tracker_reference.py)
        self._pan_gain = 1.8
        self._tilt_gain = 5.5
        self._smooth_pan_step = 0.0
        self._smooth_tilt_step = 0.0
        self._max_step = 1.2
        self._gimbal_cmd_count = 0
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
        self._search_step_timer = 0.0
        self._search_timeout = 3.0
        self._spin_speed = 1.5
        self._spin_range = 60.0
        self._spin_direction = 1
        # Camera connection state
        self._camera_connected = False
        self._camera_stable_since = 0.0
        self._camera_stable_delay = 2.0
        # Calibration / tilt return
        self._calibration_tilt = 75.0
        self._tilt_deadband = 0.15
        self._tilt_return_gain = 0.05
        self._tilt_return_max_step = 1.0
        # Pan yaw blend
        self._pan_pixel_weight = 0.7
        self._yaw_max = 45.0
        self._last_yaw_deg: float | None = None
        self._rho_active = False

    def update_detection(self, bbox, frame_w: int, frame_h: int, yaw_deg: float | None = None):
        """Update detection data (thread-safe, called from main thread)."""
        with self._frame_lock:
            self._bbox = bbox
            self._frame_w = frame_w
            self._frame_h = frame_h
            self._last_yaw_deg = yaw_deg

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

    def is_settled(self, threshold_deg_per_tick: float = 0.3) -> bool:
        """True if the last _track_target() tick computed only a tiny step
        (i.e. servos have essentially caught up / are holding position).
        Used to gate how much a fresh pose observation should be trusted
        while the gimbal is actively moving.
        """
        return abs(self._smooth_pan_step) < threshold_deg_per_tick and abs(self._smooth_tilt_step) < threshold_deg_per_tick

    def get_pan_tilt_state(self) -> tuple:
        """(pan_deg, tilt_deg, is_settled) using GimbalThread's own commanded
        angles -- not real servo feedback (none is available)."""
        return self._current_pan, self._current_tilt, self.is_settled()

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
                    rho_active = self._rho_active
                
                if rho_active:
                    # During simple follow: gimbal always tracks target
                    if bbox is not None:
                        self._track_target(bbox, frame_w, frame_h)
                    time.sleep(0.05)
                    continue
                
                if bbox is not None:
                    self._track_target(bbox, frame_w, frame_h)
                else:
                    self._search_target()
                
                time.sleep(0.05)  # ~20 Hz
            except Exception as e:
                if self._log:
                    self._log("FOLLOW", f"[Gimbal] エラー: {e}")
                time.sleep(0.05)

    def _compute_tilt_step(self, error_y: float) -> float:
        """Return tilt step for one tick. When error_y is within the deadband,
        gradually return toward calibration_tilt; otherwise track the target.
        Always returns toward calibration if tilt is far outside the range."""
        tilt_diff = self._calibration_tilt - self._current_tilt
        if abs(error_y) < self._tilt_deadband or abs(tilt_diff) > 15.0:
            return max(-self._tilt_return_max_step,
                       min(self._tilt_return_max_step, tilt_diff * self._tilt_return_gain))
        return self._compute_tracking_tilt_step(error_y)

    def _compute_tracking_tilt_step(self, error_y: float) -> float:
        """Tapered-gain tilt tracking (anti-oscillation)."""
        tilt_scale = self._gain_floor + (1.0 - self._gain_floor) * min(1.0, abs(error_y) / self._taper_start)
        target_tilt_step = error_y * self._tilt_gain * tilt_scale
        smooth_t = 0.55 * target_tilt_step + 0.45 * self._smooth_tilt_step
        self._smooth_tilt_step = smooth_t
        return max(-self._max_step, min(self._max_step, smooth_t))

    def _compute_combined_error_x(self, pixel_error_x: float, yaw_deg: float | None) -> float:
        """Blend pixel-based horizontal error with yaw_deg for pan control."""
        if yaw_deg is None:
            return pixel_error_x
        yaw_error_x = yaw_deg / self._yaw_max
        return self._pan_pixel_weight * pixel_error_x + (1 - self._pan_pixel_weight) * yaw_error_x

    def _track_target(self, bbox, frame_w: int, frame_h: int):
        """Track target when visible. Moves pan to center the target."""
        bx, by, bw, bh = bbox
        cx = bx + bw / 2.0

        if self._search_state != "tracking":
            self._search_state = "tracking"

        if cx < frame_w * 0.4:
            self._last_seen_side = "left"
        elif cx > frame_w * 0.6:
            self._last_seen_side = "right"
        else:
            self._last_seen_side = "center"

        pixel_error_x = (cx - frame_w / 2.0) / (frame_w / 2.0)

        if abs(pixel_error_x) > 0.05:
            pan_scale = self._gain_floor + (1.0 - self._gain_floor) * min(1.0, abs(pixel_error_x) / self._taper_start)
            target_pan_step = pixel_error_x * self._pan_gain * pan_scale
            smooth_p = 0.5 * target_pan_step + 0.5 * self._smooth_pan_step
            self._smooth_pan_step = smooth_p
            smooth_p = max(-self._max_step, min(self._max_step, smooth_p))
            self._current_pan = max(0, min(170, self._current_pan - smooth_p))

            if self._set_gimbal:
                self._set_gimbal(int(self._current_pan), int(self._current_tilt))
        else:
            self._smooth_pan_step = 0.0

        self._gimbal_cmd_count += 1

    def _search_target(self):
        """Search for target when lost. Steps 10 degrees, waits 3 seconds, repeats.
        Pan range: 0 (right) - 170 (left)."""
        now = time.time()
        
        if self._search_state == "tracking":
            self._search_state = "search_direction"
            self._search_start_pan = self._current_pan
            self._search_timer = now
            self._search_step_timer = now
            if self._log:
                self._log("FOLLOW", f"[Gimbal] 車をlost → {self._last_seen_side}方向を探索")
        
        if self._search_state == "search_direction":
            elapsed = now - self._search_timer
            step_elapsed = now - self._search_step_timer
            
            if step_elapsed >= 3.0:
                if self._last_seen_side == "right":
                    pan_step = -10.0
                elif self._last_seen_side == "left":
                    pan_step = 10.0
                else:
                    pan_step = -10.0
                
                self._current_pan = max(0, min(170, self._current_pan + pan_step))
                self._search_step_timer = now
                
                if self._set_gimbal:
                    self._set_gimbal(int(self._current_pan), int(self._current_tilt))
                if self._log:
                    self._log("FOLLOW", f"[Gimbal] 探索 pan={int(self._current_pan)}")
            
            if elapsed > self._search_timeout or self._current_pan <= 5 or self._current_pan >= 165:
                self._search_state = "search_spin"
                self._search_start_pan = self._current_pan
                self._search_timer = now
                self._search_step_timer = now
                self._spin_direction = 1
                if self._log:
                    self._log("FOLLOW", "[Gimbal] 方向探索失敗 → ぐるぐる探索")
        
        if self._search_state == "search_spin":
            step_elapsed = now - self._search_step_timer
            
            if step_elapsed >= 3.0:
                pan_step = 10.0 * self._spin_direction
                self._current_pan = max(0, min(170, self._current_pan + pan_step))
                self._search_step_timer = now
                
                if self._current_pan >= 165 or self._current_pan <= 5:
                    self._spin_direction = -self._spin_direction
                
                if self._set_gimbal:
                    self._set_gimbal(int(self._current_pan), int(self._current_tilt))
                if self._log:
                    self._log("FOLLOW", f"[Gimbal] 探索 pan={int(self._current_pan)}")

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
    - Distance golden band (30-45cm hold)
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
        self._hysteresis = StateHysteresis(config, initial_state=FollowState.SEARCHING)
        self.state = FollowState.SEARCHING
        self.target_distance = config.follow_distance
        self.chassis_follow_enabled = False
        self.heading_follow_enabled = False
        self.rho_alpha_beta_enabled = False
        self.repositioning_enabled = False
        self._rho_alpha_beta_ctrl = None
        self._gimbal_thread = None

        self._kp_lin = 70.0
        self._ki_lin = 0.4
        self._kd_lin = 10.0
        self._err_lin_i = 0.0
        self._prev_err_lin = 0.0
        self._prev_dist_m = None
        self._last_cmd_t = 0.0
        self._max_v_step = 60
        self._prev_v_cmd = 0
        self._dist_jump_limit = 0.6
        self._searching_since: float | None = None
        # Simple follow state: centering → driving → stopped
        self._rho_phase = "centering"  # "centering" | "driving" | "stopped"
        self._rho_drive_start_t = 0.0

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
                except Exception:
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

    def _compute_command(self, detection: dict) -> dict | None:
        yaw_deg = detection.get("yaw_deg")
        dist_m = detection.get("dist_m")
        bbox = detection.get("bbox")
        confidence = detection.get("confidence", 0.0)
        bearing_deg = detection.get("bearing_deg")
        
        gimbal_pan_deg = detection.get("gimbal_pan_deg", 90.0)
        gimbal_offset = gimbal_pan_deg - 90.0

        if bearing_deg is not None:
            bearing_deg = bearing_deg + gimbal_offset
        elif yaw_deg is not None:
            bearing_deg = yaw_deg + gimbal_offset

        candidate_state = resolve_follow_state(yaw_deg, dist_m, bbox, self.config, bearing_deg=bearing_deg, repositioning_enabled=self.repositioning_enabled)
        self.state = self._hysteresis.update(candidate_state)

        now = time.time()
        dt = max(0.02, now - self._last_cmd_t)
        min_interval = 0.5 if self.state == FollowState.REPOSITIONING else 0.080
        if dt < min_interval:
            return None
        self._last_cmd_t = now

        if self._log and self._count % 10 == 0:
            self._log("FOLLOW", f"[CTRL-DBG] state={self.state.value} bearing={bearing_deg} yaw={yaw_deg} dist={dist_m} repositioning_enabled={self.repositioning_enabled}")

        if self.state == FollowState.HEAD_ON_HOLD:
            return self._handle_head_on(yaw_deg, dist_m)

        if self.state == FollowState.REPOSITIONING:
            return self._handle_repositioning(bearing_deg=bearing_deg, dist_m=dist_m, yaw_deg=yaw_deg)

        # Simple follow: move→stop→detect→correct→move
        if self.rho_alpha_beta_enabled:
            # No detection → stop, wait
            if bbox is None or dist_m is None:
                self._rho_phase = "centering"
                return {"command": "stop", "speed": 0,
                        "chassis_enabled": True, "v": 0.0, "omega": 0.0,
                        "log": "simple: 検出なし → stop"}
            # Distance sanity
            if dist_m > 10.0 or dist_m < 0.05:
                self._rho_phase = "centering"
                return {"command": "stop", "speed": 0,
                        "chassis_enabled": True, "v": 0.0, "omega": 0.0,
                        "log": f"simple: dist異常({dist_m:.1f}m) → stop"}
            # At follow distance → stop
            if dist_m <= self.config.follow_distance:
                self._rho_phase = "stopped"
                return {"command": "stop", "speed": 0,
                        "chassis_enabled": True, "v": 0.0, "omega": 0.0,
                        "log": f"simple: 到達 dist={dist_m:.2f}m"}
            # Check if target is centered via gimbal pan
            gimbal_pan = detection.get("gimbal_pan_deg", 90.0)
            gimbal_offset = abs(gimbal_pan - 90.0)
            target_centered = gimbal_offset < 5.0  # within 5° of center
            if self._log and self._count % 10 == 0:
                self._log("FOLLOW", f"[SIMPLE] phase={self._rho_phase} pan={gimbal_pan:.1f} offset={gimbal_offset:.1f} dist={dist_m:.2f}m centered={target_centered}")
            # Phase logic
            if self._rho_phase == "centering":
                if target_centered:
                    # Target centered → start moving
                    self._rho_phase = "driving"
                    self._rho_drive_start_t = now
                    return {"command": "forward", "speed": 150,
                            "chassis_enabled": True, "v": 0.0, "omega": 0.0,
                            "log": f"simple: 中央揃い → 前進開始"}
                else:
                    # Not centered → stop, let gimbal track
                    return {"command": "stop", "speed": 0,
                            "chassis_enabled": True, "v": 0.0, "omega": 0.0,
                            "log": f"simple: 中央待ち pan={gimbal_pan:.1f}"}
            elif self._rho_phase == "driving":
                elapsed = now - self._rho_drive_start_t
                if elapsed < 0.3:
                    # Still moving
                    return {"command": "forward", "speed": 150,
                            "chassis_enabled": True, "v": 0.0, "omega": 0.0,
                            "log": f"simple: 前進中({elapsed:.2f}s)"}
                else:
                    # Move done → stop, re-detect
                    self._rho_phase = "centering"
                    return {"command": "stop", "speed": 0,
                            "chassis_enabled": True, "v": 0.0, "omega": 0.0,
                            "log": f"simple: 停止 → 検出待ち"}
            else:  # stopped
                return {"command": "stop", "speed": 0,
                        "chassis_enabled": True, "v": 0.0, "omega": 0.0,
                        "log": "simple: 到達済み"}

        if self.state == FollowState.SEARCHING:
            self._searching_since = self._searching_since or now
            if now - self._searching_since >= self.config.lost_timeout_sec:
                self.state = FollowState.LOST_TIMEOUT
                return self._stop_command("ロストタイムアウト")
            return self._stop_command("探索中(bbox未検出)")

        if self.state == FollowState.LOST_TIMEOUT:
            return self._stop_command("ロストタイムアウト")

        self._searching_since = None

        if self.state == FollowState.APPROACHING_BLIND:
            return self._handle_approaching_blind(bbox, detection.get("frame_w", 640))

        if self.state == FollowState.HOLDING:
            self._err_lin_i = 0.0
            self._prev_err_lin = 0.0
            self._prev_v_cmd = 0
            return self._stop_command("ホールド(30-45cm帯)")

        if confidence < self.config.min_confidence:
            return self._stop_command(f"信頼度不足({confidence:.2f})")

        if dist_m < self.config.stop_dist:
            return self._stop_command(f"停止 dist={dist_m:.2f}m")

        # FOLLOWING: 距離に応じた速度 + 近づいたら方位に合わせて旋回
        if dist_m > 1.5:
            speed = self.config.base_speed
        elif dist_m > 1.0:
            speed = 150
        elif dist_m > 0.7:
            speed = 150
        else:
            speed = 150

        if yaw_deg is not None and self.heading_follow_enabled and abs(yaw_deg) > 15.0:
            command = "left" if yaw_deg > 0 else "right"
        else:
            command = "forward"

        return {
            "type": "control",
            "command": command,
            "speed": speed,
            "chassis_enabled": self.chassis_follow_enabled,
            "log": f"{command} dist={dist_m:.2f}m yaw={yaw_deg:+.1f}° speed={speed}",
        }

    def _handle_head_on(self, yaw_deg: float, dist_m: float) -> dict:
        """正対時の処理。現状は停止のみ。"""
        return self._stop_command("正対検知(yaw≈180°) - 現状は停止のみ")

    def _handle_repositioning(self, bearing_deg: float | None, dist_m: float | None, yaw_deg: float | None) -> dict:
        """Rho-alpha-beta tail repositioning for large yaw offsets."""
        if bearing_deg is None or dist_m is None or yaw_deg is None:
            return self._stop_command("回り込み: 情報不足")

        rho_goal, alpha_goal, beta_goal = compute_goal_pose(
            bearing_deg=bearing_deg, dist_m=dist_m, yaw_deg=yaw_deg,
            follow_distance=self.config.follow_distance,
        )

        v = self.config.k_rho * rho_goal
        omega_deg = self.config.k_alpha * alpha_goal + self.config.k_beta * beta_goal

        TURN_ONLY_ALPHA_DEG = 15.0
        if abs(alpha_goal) > TURN_ONLY_ALPHA_DEG:
            command = "left" if alpha_goal > 0 else "right"
            speed = int(max(self.config.min_pwm, min(255, self.config.turn_speed)))
        elif rho_goal > 0.05:
            v_cmd = int(max(self.config.min_pwm, min(255, self.config.min_pwm + abs(v) * 100)))
            command = "forward"
            speed = v_cmd
        else:
            command = "left" if omega_deg > 0 else "right"
            speed = self.config.turn_speed

        return {
            "type": "control",
            "command": command,
            "speed": speed,
            "chassis_enabled": self.chassis_follow_enabled,
            "log": f"[回り込み] rho:{rho_goal:.2f} alpha:{alpha_goal:+.1f} beta:{beta_goal:+.1f} {command}",
        }

    def _handle_approaching_blind(self, bbox, frame_w: int) -> dict:
        return self._stop_command("画像認識待ち(bbox未検出)")

    def _stop_command(self, reason: str) -> dict:
        return {"type": "control", "command": "stop", "speed": 0, "chassis_enabled": self.chassis_follow_enabled, "log": f"停止:{reason}"}

    def stop(self):
        self._running = False
        self._err_lin_i = 0.0
        self._prev_err_lin = 0.0
        self._prev_v_cmd = 0


class CommandThread(threading.Thread):
    def __init__(self, input_queue: Queue, send_command: Callable[[str], None], 
                 set_speed: Callable[[int], None], log_callback: Callable[[str, str], None],
                 set_gimbal: Callable[[int, int], None] = None):
        super().__init__(daemon=True)
        self.input_queue = input_queue
        self.send_command = send_command
        self.set_speed = set_speed
        self.log_callback = log_callback
        self.set_gimbal = set_gimbal
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
        gimbal_center = command_data.get("gimbal_center", False)
        
        self._cmd_count += 1
        
        if self.log_callback:
            self.log_callback("FOLLOW", f"[CTRL] {log}")
        
        # Send motor command (Tier 2: only when chassis enabled)
        if chassis_enabled:
            if self.send_command:
                self.send_command(command)
            if self.set_speed and speed > 0:
                self.set_speed(speed)
        
        # Center gimbal after car movement
        if gimbal_center and self.set_gimbal:
            self.set_gimbal(90, 75)

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
        
        # Heading follow: True = steer to align behind target (B key)
        self._heading_follow_enabled = False
        
        # Rho-alpha-beta follow: True = polar coordinate feedback control (N key)
        self._rho_alpha_beta_enabled = False
        self._rho_alpha_beta_ctrl = RhoAlphaBetaController()
        
        # Repositioning: True = tail repositioning for large yaw offsets (M key)
        self.repositioning_enabled = False
        
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
            if self._send_command:
                self._send_command("stop")

    def toggle_heading_follow(self):
        """Toggle heading follow mode (b key): steer to align behind target."""
        self._heading_follow_enabled = not self._heading_follow_enabled
        state = "有効" if self._heading_follow_enabled else "無効"
        if self._log_callback:
            self._log_callback("FOLLOW", f"方位追従: {state}")
        if self._control_thread:
            self._control_thread.heading_follow_enabled = self._heading_follow_enabled
        if not self._heading_follow_enabled:
            if self._send_command:
                self._send_command("stop")

    def toggle_rho_alpha_beta(self):
        """Toggle rho-alpha-beta control (n key): polar coordinate feedback."""
        self._rho_alpha_beta_enabled = not self._rho_alpha_beta_enabled
        state = "有効" if self._rho_alpha_beta_enabled else "無効"
        if self._log_callback:
            self._log_callback("FOLLOW", f"ρ-α-β制御: {state}")
        if self._rho_alpha_beta_enabled:
            self._rho_alpha_beta_ctrl.reset()
            self._chassis_follow_enabled = True
            # Stop gimbal thread and center gimbal
            if self._gimbal_thread:
                self._gimbal_thread._rho_active = True
            if self._set_gimbal:
                self._set_gimbal(90, 75)
        else:
            if self._gimbal_thread:
                self._gimbal_thread._rho_active = False
        if self._control_thread:
            self._control_thread.rho_alpha_beta_enabled = self._rho_alpha_beta_enabled
            self._control_thread.chassis_follow_enabled = self._chassis_follow_enabled
        if not self._rho_alpha_beta_enabled:
            if self._send_command:
                self._send_command("stop")

    def toggle_repositioning(self):
        """Toggle repositioning mode (M key): tail repositioning for large yaw offsets."""
        self.repositioning_enabled = not self.repositioning_enabled
        state = "enabled" if self.repositioning_enabled else "disabled"
        if self._log_callback:
            self._log_callback("FOLLOW", f"Repositioning mode {state}")
        if self._control_thread:
            self._control_thread.repositioning_enabled = self.repositioning_enabled
        if not self.repositioning_enabled:
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
        self._control_thread._gimbal_thread = self._gimbal_thread
        self._control_thread._rho_alpha_beta_ctrl = self._rho_alpha_beta_ctrl
        self._command_thread = CommandThread(
            self._command_queue, self._send_command, self._set_speed, self._log_callback,
            set_gimbal=self._set_gimbal
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
                detection.get("frame_h", 480),
                yaw_deg=detection.get("yaw_deg"),
            )
        
        # Add gimbal pan offset to detection dict for ControlThread
        gimbal_pan_deg = self._gimbal_thread._current_pan if self._gimbal_thread else 90.0
        detection["gimbal_pan_deg"] = gimbal_pan_deg
        
        # Send to motor control pipeline
        qsize = self._detection_queue.qsize()
        try:
            self._detection_queue.put_nowait(detection)
            if self._log_callback and qsize == 0:
                yaw = detection.get("yaw_deg")
                dist = detection.get("dist_m")
                bearing = detection.get("bearing_deg")
                self._log_callback("FOLLOW", f"[UPDATE] yaw={yaw} dist={dist} bearing={bearing} gimbal_pan={gimbal_pan_deg:.1f} qsize={qsize}")
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
