"""Floor-plane pose geometry and ArUco distance refinement for the RC-car
pose detector. Extracted from the captures/rccar_pose training project's
infer.py so this app can run inference without depending on that separate
(training-only) project. See that project's README for how config.json's
"ground"/ArUco constants were calibrated.
"""
from __future__ import annotations

import math

import cv2
import numpy as np


class Ground:
    """Maps an image ground-contact point (u, v) to floor coordinates
    (X right, Z forward) [m], and derives an RC-car's position/yaw from
    three such points (L/R wheel contacts + a front reference point)."""

    def __init__(self, g: dict) -> None:
        self.A, self.v0, self.fx, self.cu = g["A"], g["v0"], g["fx"], g["cu"]
        self.sign, self.off = g.get("yaw_sign", 1.0), g.get("yaw_offset", 0.0)
        # When F is a body marking rather than a ground-contact point, its
        # height above the floor shrinks the effective A; A_front captures that.
        self.A_front = g.get("A_front", self.A)
        # Calibration-fitted blend weight between the two yaw estimates below
        # (e.g. w_front≈0 when the front point isn't reliable enough to use).
        self.w_axle = g.get("w_axle", 0.5)
        self.w_front = g.get("w_front", 0.5)

    def point(self, u: float, v: float, A: float | None = None) -> tuple[float, float] | None:
        t = v - self.v0
        if t <= 1e-3:
            return None
        Z = (self.A if A is None else A) / t
        return (u - self.cu) * Z / self.fx, Z

    def pose(self, L, R, F) -> dict | None:
        """L (left wheel), R (right wheel), F (front) image ground points ->
        position and heading."""
        pl, pr = self.point(*L), self.point(*R)
        pf = self.point(F[0], F[1], self.A_front)
        if pl is None or pr is None or pf is None:
            return None
        Xl, Zl = pl
        Xr, Zr = pr
        Xf, Zf = pf
        Xm, Zm = (Xl + Xr) / 2, (Zl + Zr) / 2

        # Forward direction perpendicular to the L->R axle.
        ux, uz = Xr - Xl, Zr - Zl
        n1 = math.hypot(ux, uz) + 1e-9
        h1 = (-uz / n1, ux / n1)
        # Axle-midpoint -> F direction.
        gx, gz = Xf - Xm, Zf - Zm
        n2 = math.hypot(gx, gz) + 1e-9
        h2 = (gx / n2, gz / n2)
        w1, w2 = self.w_axle, self.w_front
        hx = h1[0] * w1 + h2[0] * w2
        hz = h1[1] * w1 + h2[1] * w2
        n = math.hypot(hx, hz) + 1e-9
        hx, hz = hx / n, hz / n

        wrap = lambda d: (d + 180) % 360 - 180
        yaw = lambda h: wrap(self.sign * math.degrees(math.atan2(h[0], h[1])) + self.off)
        return {
            "X": Xm,
            "Z": Zm,
            "dist_m": math.hypot(Xm, Zm),
            "yaw_deg": yaw((hx, hz)),
            "yaw_axle": yaw(h1),
            "yaw_front": yaw(h2),
            "track_m": math.hypot(ux, uz),
            "front_m": math.hypot(gx, gz),
        }


class Aruco:
    """Detects the calibration ArUco marker and converts its apparent edge
    length to a distance estimate (config.json's aruco_K), used to refine
    the floor-plane distance when the marker is visible."""

    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, cfg.get("aruco_dict", "DICT_4X4_50")))
        params = cv2.aruco.DetectorParameters()
        params.adaptiveThreshWinSizeMin, params.adaptiveThreshWinSizeMax, params.adaptiveThreshWinSizeStep = 3, 33, 4
        params.minMarkerPerimeterRate = 0.01
        try:
            params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        except Exception:
            pass
        self._detector = cv2.aruco.ArucoDetector(dictionary, params)

    def __call__(self, bgr: np.ndarray) -> dict | None:
        corners, ids, _ = self._detector.detectMarkers(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY))
        if ids is None or len(ids) == 0:
            return None
        quad = np.asarray(corners[0]).reshape(-1, 2).astype(float)
        edge = float(np.mean([np.linalg.norm(quad[i] - quad[(i + 1) % 4]) for i in range(4)]))
        if edge < self.cfg.get("min_marker_edge_px", 8.0):
            return None
        return {
            "id": int(np.ravel(ids)[0]),
            "corners": quad,
            "edge_px": edge,
            "dist_m": self.cfg.get("aruco_K", 11.4) / edge,
        }
