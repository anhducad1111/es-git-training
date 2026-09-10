"""ハイブリッド制御ベースの車追従コントローラー（PID + Stanley）"""

from __future__ import annotations

import math
from enum import Enum
from typing import Callable


class FollowState(Enum):
    FOLLOWING = "following"
    TURNING = "turning"
    WAITING = "waiting"
    SEARCHING = "searching"


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


class HybridFollowController:
    THRESHOLDS = {
        "turn_start_dist": 1.0,
        "stop_dist": 0.3,
        "turn_complete_yaw": 30,
        "follow_max_yaw": 60,
    }

    def __init__(self, send_command: Callable[[str], None]) -> None:
        self.send_command = send_command
        self.pid_distance = PIDController(kp=1.0, ki=0.0, kd=0.1)
        self.stanley = StanleyController(k=0.5, max_steer=30.0)
        self.state = FollowState.SEARCHING
        self.target_speed = 100
        self.target_distance = 0.8

    def update(self, yaw_deg: float, dist_m: float, obstacle_dist: float | None = None) -> None:
        if obstacle_dist is not None and obstacle_dist < 0.3:
            self.send_command("stop")
            return
        if dist_m < 0.2:
            self.send_command("stop")
            return

        self._check_transitions(yaw_deg, dist_m)
        if self.state == FollowState.FOLLOWING:
            self._control_following(yaw_deg, dist_m)
        elif self.state == FollowState.TURNING:
            self._control_turning(yaw_deg)
        elif self.state == FollowState.WAITING:
            self._control_waiting()
        elif self.state == FollowState.SEARCHING:
            self._control_searching()

    def _check_transitions(self, yaw_deg: float, dist_m: float) -> None:
        if self.state == FollowState.FOLLOWING:
            if abs(yaw_deg) > 90 and dist_m > self.THRESHOLDS["turn_start_dist"]:
                self.state = FollowState.TURNING
            elif abs(yaw_deg) > 90:
                self.state = FollowState.WAITING
        elif self.state == FollowState.TURNING:
            if abs(yaw_deg) < self.THRESHOLDS["turn_complete_yaw"]:
                self.state = FollowState.FOLLOWING
            elif dist_m < self.THRESHOLDS["stop_dist"]:
                self.state = FollowState.WAITING
        elif self.state == FollowState.WAITING:
            if abs(yaw_deg) < self.THRESHOLDS["turn_complete_yaw"]:
                self.state = FollowState.FOLLOWING
        elif self.state == FollowState.SEARCHING:
            if abs(yaw_deg) < self.THRESHOLDS["follow_max_yaw"]:
                self.state = FollowState.FOLLOWING
            elif yaw_deg != 0:
                self.state = FollowState.TURNING

    def _control_following(self, yaw_deg: float, dist_m: float) -> None:
        steering = self.stanley.control(yaw_deg, dist_m, self.target_speed / 100.0)
        dist_error = dist_m - self.target_distance
        throttle = self.pid_distance.compute(dist_error)
        throttle = max(0.0, min(1.0, throttle))

        if abs(steering) < 5:
            self.send_command("forward")
        elif steering > 0:
            self.send_command("right")
        else:
            self.send_command("left")
        self.send_command(f"speed:{int(throttle * self.target_speed)}")

    def _control_turning(self, yaw_deg: float) -> None:
        direction = "right" if yaw_deg > 0 else "left"
        self.send_command(direction)
        self.send_command("speed:80")

    def _control_waiting(self) -> None:
        self.send_command("stop")

    def _control_searching(self) -> None:
        self.send_command("forward")
        self.send_command("speed:50")

    def stop(self) -> None:
        self.send_command("stop")
        self.state = FollowState.SEARCHING
        self.pid_distance.reset()
