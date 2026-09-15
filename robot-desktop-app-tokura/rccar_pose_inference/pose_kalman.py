"""Constant-velocity Kalman filter for floor-plane car pose (X, Z, yaw).

Smooths per-frame RcCarPoseDetector-style observations over time so
yaw/distance don't jitter frame-to-frame, and lets a few missed detections
(occlusion, low-confidence keypoints) be bridged by prediction alone instead
of dropping the track immediately.

See docs/superpowers/specs/2026-09-11-pose-inference-service-handoff.md for
the original design, and
docs/superpowers/specs/2026-09-11-gimbal-pose-compensation-design.md for the
position_confidence / yaw_snap_threshold_deg additions (gimbal reversal
detection and low-trust observations while the gimbal is moving).

State vector: [X, Z, vX, vZ, yaw_deg, yaw_rate_deg_s]
"""
from __future__ import annotations

import math

import numpy as np


class PoseKalmanFilter:
    def __init__(self, process_noise_pos: float = 0.05, process_noise_yaw: float = 5.0,
                 measurement_noise: float = 0.05, yaw_snap_threshold_deg: float = 90.0) -> None:
        self._process_noise_pos = process_noise_pos
        self._process_noise_yaw = process_noise_yaw
        self._measurement_noise = measurement_noise
        # A real 180° reversal (axle L/R ambiguity) looks identical to noise
        # to a constant-velocity model. Above this threshold, snap to the
        # observation instead of blending (see update()).
        self._yaw_snap_threshold_deg = yaw_snap_threshold_deg
        self._initialized = False
        self._coast_seconds = 0.0
        self._x = np.zeros(6)  # [X, Z, vX, vZ, yaw, yaw_rate]
        self._P = np.eye(6) * 1.0

    def is_initialized(self) -> bool:
        return self._initialized

    def update(self, x: float, z: float, yaw_deg: float, position_confidence: float = 1.0) -> None:
        """position_confidence scales how much this observation is trusted
        (1.0 = normal measurement noise; smaller values inflate the
        effective measurement covariance, shrinking the Kalman gain so the
        filter leans on its predicted/propagated state instead). Used while
        the gimbal hasn't settled after a pan/tilt move -- see
        GimbalThread.is_settled() and PoseInference._apply_gimbal_compensation.
        """
        self._coast_seconds = 0.0
        if not self._initialized:
            self._x = np.array([x, z, 0.0, 0.0, yaw_deg, 0.0])
            self._P = np.eye(6) * 1.0
            self._initialized = True
            return

        yaw_residual = (yaw_deg - self._x[4] + 180.0) % 360.0 - 180.0
        if abs(yaw_residual) >= self._yaw_snap_threshold_deg:
            # Reset belief about heading (and its rate, now meaningless)
            # rather than blend, and blow out their covariance so this
            # doesn't get dragged back toward the stale pre-flip heading by
            # the ordinary update below or the next couple of frames.
            self._x[4] = (yaw_deg + 180.0) % 360.0 - 180.0
            self._x[5] = 0.0
            self._P[4, :] = 0.0
            self._P[:, 4] = 0.0
            self._P[5, :] = 0.0
            self._P[:, 5] = 0.0
            self._P[4, 4] = self._P[5, 5] = 1.0e4

        H = np.zeros((3, 6))
        H[0, 0] = 1.0  # X
        H[1, 1] = 1.0  # Z
        H[2, 4] = 1.0  # yaw
        R = np.eye(3) * (self._measurement_noise ** 2)
        R[2, 2] = 25.0  # yaw measurement noise is on a different (degree) scale
        R = R / max(position_confidence, 1e-3)  # low confidence -> inflate R -> smaller gain

        z_vec = np.array([x, z, yaw_deg])
        y = z_vec - H @ self._x
        y[2] = (y[2] + 180.0) % 360.0 - 180.0  # wrap yaw residual

        S = H @ self._P @ H.T + R
        K = self._P @ H.T @ np.linalg.inv(S)
        self._x = self._x + K @ y
        self._x[4] = (self._x[4] + 180.0) % 360.0 - 180.0
        self._P = (np.eye(6) - K @ H) @ self._P

    def predict(self, dt: float) -> None:
        if not self._initialized:
            return
        self._coast_seconds += dt

        F = np.eye(6)
        F[0, 2] = dt  # X += vX*dt
        F[1, 3] = dt  # Z += vZ*dt
        F[4, 5] = dt  # yaw += yaw_rate*dt
        self._x = F @ self._x
        self._x[4] = (self._x[4] + 180.0) % 360.0 - 180.0

        Q = np.eye(6)
        Q[0, 0] = Q[1, 1] = (self._process_noise_pos * dt) ** 2
        Q[2, 2] = Q[3, 3] = (self._process_noise_pos * dt) ** 2
        Q[4, 4] = (self._process_noise_yaw * dt) ** 2
        Q[5, 5] = (self._process_noise_yaw * dt) ** 2
        self._P = F @ self._P @ F.T + Q

    def coast_seconds(self) -> float:
        return self._coast_seconds

    def is_stale(self, max_coast_sec: float) -> bool:
        return self._coast_seconds >= max_coast_sec

    @property
    def state(self) -> dict:
        X, Z, vX, vZ, yaw_deg, yaw_rate = self._x
        return {
            "X": float(X), "Z": float(Z), "yaw_deg": float(yaw_deg),
            "dist_m": float(math.hypot(X, Z)),
            "vx_mps": float(vX), "vz_mps": float(vZ),
            "yaw_rate_deg_s": float(yaw_rate),
        }
