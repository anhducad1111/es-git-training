import os
import time
import math
import threading

from PyQt6.QtCore import QThread, pyqtSignal

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"


def constrain(val, min_val, max_val):
    return max(min_val, min(max_val, val))


class AiTrackerV2(QThread):
    detections_ready = pyqtSignal(list)
    drive_command = pyqtSignal(str)
    gimbal_command = pyqtSignal(int, int)
    speed_command = pyqtSignal(int)

    # ── PID Gains ─────────────────────────────────────────────────────────────
    KP_LIN, KI_LIN, KD_LIN = 70.0, 0.4, 10.0

    # ── Gyro-closed-loop pulse-turn tuning ─────────────────────────────────────
    TURN_PULSE_PWM = 130
    TURN_PULSE_MAX_S = 0.25
    TURN_COAST_S = 0.20
    TURN_DEADBAND_DEG = 8.0
    TURN_TRIGGER_ERROR = 0.25

    # ── Gimbal visual-servo gain ───────────────────────────────────────────────
    PAN_GAIN = 0.15

    # ── Distance thresholds ────────────────────────────────────────────────────
    TARGET_DISTANCE = 0.5
    FAR_DISTANCE = 1.5

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False

        # Detection data
        self._yaw_deg = None
        self._dist_m = None
        self._bbox = None
        self._frame_w = 640
        self._frame_h = 480
        self._detection_lock = threading.Lock()

        # PID states
        self._err_lin_i = 0.0
        self._prev_err_lin = 0.0
        self._prev_dist_m = None
        self._prev_v_cmd = 0
        self._last_cmd_t = 0.0

        # IMU feedback
        self._yaw_rate_dps = 0.0
        self._heading_deg = 0.0
        self._last_yaw_integrate_t = None

        # Gyro-closed-loop pulse-turn state machine
        self._turn_state = 'idle'
        self._turn_start_heading = 0.0
        self._turn_target_delta = 0.0
        self._turn_sign = 0
        self._turn_pulse_deadline = 0.0
        self._turn_coast_deadline = 0.0

        # Gimbal state
        self._current_pan = 90.0
        self._smooth_pan_step = 0.0

    def start_tracking(self):
        self._running = True
        self._err_lin_i = 0.0
        self._prev_err_lin = 0.0
        self._prev_dist_m = None
        self._prev_v_cmd = 0
        self._turn_state = 'idle'
        self._heading_deg = 0.0
        self._last_yaw_integrate_t = None
        self._current_pan = 90.0
        self._smooth_pan_step = 0.0
        self._yaw_deg = None
        self._dist_m = None
        self._bbox = None
        if not self.isRunning():
            self.start()

    def stop_tracking(self):
        self._running = False
        self.wait(1500)

    def set_detection(self, yaw_deg, dist_m, bbox, frame_w=640, frame_h=480):
        with self._detection_lock:
            self._yaw_deg = yaw_deg
            self._dist_m = dist_m
            self._bbox = bbox
            self._frame_w = frame_w
            self._frame_h = frame_h

    def on_yaw_rate(self, rate_dps: float):
        now = time.time()
        if self._last_yaw_integrate_t is not None:
            dt = now - self._last_yaw_integrate_t
            if 0.0 < dt < 0.5:
                self._heading_deg += rate_dps * dt
        self._last_yaw_integrate_t = now
        self._yaw_rate_dps = rate_dps

    def run(self):
        while self._running:
            with self._detection_lock:
                yaw_deg = self._yaw_deg
                dist_m = self._dist_m
                bbox = self._bbox
                frame_w = self._frame_w
                frame_h = self._frame_h

            if bbox is None or yaw_deg is None or dist_m is None:
                if self._turn_state != 'idle':
                    self._turn_state = 'idle'
                self._prev_v_cmd = 0
                self.drive_command.emit("stop")
                time.sleep(0.05)
                continue

            self._control_loop(yaw_deg, dist_m, bbox, frame_w, frame_h)
            time.sleep(0.03)

    def _control_loop(self, yaw_deg, dist_m, bbox, frame_w, frame_h):
        now = time.time()
        dt = max(0.02, now - self._last_cmd_t)
        if dt < 0.080:
            return
        self._last_cmd_t = now

        # ── Occlusion guard ────────────────────────────────────────────────────
        DIST_JUMP_LIMIT_M = 0.6
        if self._prev_dist_m is not None and abs(dist_m - self._prev_dist_m) > DIST_JUMP_LIMIT_M:
            dist_m = self._prev_dist_m
        else:
            self._prev_dist_m = dist_m

        # ── Gimbal control: always track using yaw_deg ─────────────────────────
        yaw_normalized = max(-45.0, min(45.0, yaw_deg))
        if abs(yaw_normalized) < 5.0:
            self._smooth_pan_step = 0.0
        else:
            raw_step = yaw_normalized * self.PAN_GAIN * 0.1
            smooth_step = 0.25 * raw_step + 0.75 * self._smooth_pan_step
            self._smooth_pan_step = smooth_step
            new_pan = self._current_pan - smooth_step
            new_pan = max(0.0, min(170.0, new_pan))
            self._current_pan = new_pan
            self.gimbal_command.emit(int(new_pan), 75)

        # ── Car control: only when close enough ────────────────────────────────
        if dist_m > self.FAR_DISTANCE:
            # Far away: stop car, gimbal only
            if self._turn_state != 'idle':
                self._turn_state = 'idle'
            self._prev_v_cmd = 0
            self._err_lin_i = 0.0
            self._prev_err_lin = 0.0
            self.drive_command.emit("stop")
            self.speed_command.emit(150)
            return

        # ── Linear PID: error = dist_m - TARGET_DISTANCE ───────────────────────
        err_lin = dist_m - self.TARGET_DISTANCE
        self._err_lin_i += err_lin * dt
        self._err_lin_i = max(-3.0, min(3.0, self._err_lin_i))
        d_err_lin = (err_lin - self._prev_err_lin) / dt
        self._prev_err_lin = err_lin

        lin_v = (self.KP_LIN * err_lin
                 + self.KI_LIN * self._err_lin_i
                 + self.KD_LIN * d_err_lin)

        # ── Heading error from yaw_deg ─────────────────────────────────────────
        heading_error = yaw_deg / 45.0

        # ── Gyro-closed-loop pulse turning ─────────────────────────────────────
        now_t = time.time()
        if self._turn_state == 'coasting':
            if now_t >= self._turn_coast_deadline:
                self._turn_state = 'idle'
        elif self._turn_state == 'pulsing':
            turned_so_far = self._heading_deg - self._turn_start_heading
            reached = abs(turned_so_far) >= abs(self._turn_target_delta) - self.TURN_DEADBAND_DEG
            if reached or now_t >= self._turn_pulse_deadline:
                self._turn_state = 'coasting'
                self._turn_coast_deadline = now_t + self.TURN_COAST_S
        else:  # 'idle'
            if abs(heading_error) > self.TURN_TRIGGER_ERROR:
                self._turn_target_delta = yaw_deg
                self._turn_sign = 1 if self._turn_target_delta > 0 else -1
                self._turn_start_heading = self._heading_deg
                self._turn_pulse_deadline = now_t + self.TURN_PULSE_MAX_S
                self._turn_state = 'pulsing'

        # ── Decide v_cmd and w_cmd ─────────────────────────────────────────────
        if self._turn_state == 'pulsing':
            w_cmd = int(self._turn_sign * self.TURN_PULSE_PWM)
            v_cmd = 0
        elif self._turn_state == 'coasting':
            w_cmd = 0
            v_cmd = 0
        else:  # idle
            if abs(heading_error) > 0.5:
                w_cmd = 0
                v_cmd = 0
            elif err_lin > 0.15:
                v_cmd = int(constrain(140 + lin_v, 110, 245))
                w_cmd = 0
            elif err_lin < -0.20:
                v_cmd = int(constrain(-130 + lin_v, -220, -100))
                w_cmd = 0
            else:
                v_cmd = 0
                w_cmd = 0

        # ── Rate-limit v_cmd ───────────────────────────────────────────────────
        MAX_V_STEP = 60
        v_cmd = int(constrain(v_cmd, self._prev_v_cmd - MAX_V_STEP, self._prev_v_cmd + MAX_V_STEP))
        self._prev_v_cmd = v_cmd

        # ── Send commands ──────────────────────────────────────────────────────
        if v_cmd > 0 and w_cmd == 0:
            self.drive_command.emit("forward")
        elif v_cmd < 0 and w_cmd == 0:
            self.drive_command.emit("backward")
        elif w_cmd > 0:
            self.drive_command.emit("right")
        elif w_cmd < 0:
            self.drive_command.emit("left")
        else:
            self.drive_command.emit("stop")
