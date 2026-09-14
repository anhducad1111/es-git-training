from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np


@dataclass
class CalibrationData:
    camera_matrix: np.ndarray
    distortion: np.ndarray
    image_size: tuple[int, int]
    reprojection_error: float


def save_calibration(path: str | Path, data: CalibrationData) -> None:
    payload = calibration_to_dict(data)
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def calibration_to_dict(data: CalibrationData) -> dict:
    return {
        "camera_matrix": np.asarray(data.camera_matrix).tolist(),
        "distortion": np.asarray(data.distortion).reshape(-1).tolist(),
        "image_size": list(data.image_size),
        "reprojection_error": float(data.reprojection_error),
    }


def append_calibration_history(path: str | Path, data: CalibrationData, extra: dict | None = None) -> None:
    """Append a calibration run to a JSON list file, keeping past results alongside new ones."""
    p = Path(path)
    entries = []
    if p.exists():
        try:
            entries = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            entries = []
    entry = calibration_to_dict(data)
    entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    if extra:
        entry.update(extra)
    entries.append(entry)
    p.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def load_calibration(path: str | Path) -> CalibrationData:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return calibration_from_dict(payload)


def load_calibration_history(path: str | Path) -> list[dict]:
    """Read past calibration runs written by append_calibration_history, newest last."""
    p = Path(path)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def calibration_from_dict(payload: dict) -> CalibrationData:
    return CalibrationData(
        np.asarray(payload["camera_matrix"], dtype=np.float64),
        np.asarray(payload["distortion"], dtype=np.float64),
        tuple(int(v) for v in payload["image_size"]),
        float(payload.get("reprojection_error", 0.0)),
    )


@dataclass
class CoverageSample:
    """How much of the frame one captured calibration sample used.

    area_ratio: board bounding-box area / frame area (smaller = farther away).
    center_x/center_y: board bounding-box center, normalized to 0..1 (0.5 = frame center).
    """

    area_ratio: float
    center_x: float
    center_y: float


def coverage_sample_from_corners(corners: np.ndarray, image_size: tuple[int, int]) -> CoverageSample:
    points = np.asarray(corners, dtype=np.float64).reshape(-1, 2)
    width, height = image_size
    x_min, y_min = points.min(axis=0)
    x_max, y_max = points.max(axis=0)
    area_ratio = ((x_max - x_min) * (y_max - y_min)) / (width * height)
    center_x = ((x_min + x_max) / 2) / width
    center_y = ((y_min + y_max) / 2) / height
    return CoverageSample(area_ratio=float(area_ratio), center_x=float(center_x), center_y=float(center_y))


# Area-ratio thresholds distinguishing "far" and "close" board captures,
# and how near a bounding-box center must be to a frame edge to count as
# an edge/corner shot.
_FAR_AREA_RATIO = 0.05
_CLOSE_AREA_RATIO = 0.25
_EDGE_MARGIN = 0.2


def error_quality_tier(reprojection_error: float) -> str:
    if reprojection_error < 0.5:
        return "excellent"
    if reprojection_error < 1.0:
        return "good"
    if reprojection_error < 2.0:
        return "acceptable"
    return "poor"


TIER_LABELS_JA = {"excellent": "優秀", "good": "良好", "acceptable": "許容範囲", "poor": "要再撮影"}
TIER_STATUS_LEVELS = {"excellent": "ok", "good": "ok", "acceptable": "warn", "poor": "error"}


def format_history_entry(entry: dict) -> str:
    timestamp = entry.get("timestamp", "?")
    error = entry.get("reprojection_error", 0.0)
    tier = TIER_LABELS_JA[error_quality_tier(error)]
    width, height = entry.get("image_size", (0, 0))
    quality = entry.get("quality")
    quality_part = f" quality={quality}" if quality is not None else ""
    return f"{timestamp} | {error:.3f}px ({tier}) | {width}x{height}{quality_part}"


def summarize_coverage(samples: list[CoverageSample]) -> list[str]:
    """Plain-language tips about what to capture more of, based on how the
    board's size (distance proxy) and position varied across samples."""
    if not samples:
        return []
    has_far = any(s.area_ratio < _FAR_AREA_RATIO for s in samples)
    has_close = any(s.area_ratio > _CLOSE_AREA_RATIO for s in samples)
    has_edge = any(
        s.center_x < _EDGE_MARGIN or s.center_x > 1 - _EDGE_MARGIN or s.center_y < _EDGE_MARGIN or s.center_y > 1 - _EDGE_MARGIN
        for s in samples
    )
    tips = []
    if not has_far:
        tips.append("遠い距離のショットが少ないようです。もう少し離れて撮影すると精度が安定します。")
    if not has_close:
        tips.append("近い距離のショットも追加すると良さそうです。")
    if not has_edge:
        tips.append("画面の端や四隅でも撮影すると、レンズ歪みの補正精度が上がります。")
    if not tips:
        tips.append("撮影バランス良好です。")
    return tips


def make_charuco_board(squares_x: int = 5, squares_y: int = 7, square_m: float = 0.04, marker_m: float = 0.02):
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    return cv2.aruco.CharucoBoard((squares_x, squares_y), square_m, marker_m, dictionary)


class CharucoCalibrationSession:
    def __init__(self, board=None) -> None:
        self.board = board or make_charuco_board()
        self.detector = cv2.aruco.CharucoDetector(self.board)
        self.corners: list[np.ndarray] = []
        self.ids: list[np.ndarray] = []
        self.coverage: list[CoverageSample] = []
        self.image_size: tuple[int, int] | None = None

    def add_frame(self, frame: np.ndarray) -> int:
        charuco_corners, charuco_ids, _, _ = self.detector.detectBoard(frame)
        if charuco_ids is None or len(charuco_ids) < 4:
            return 0
        height, width = frame.shape[:2]
        self.image_size = (width, height)
        self.corners.append(charuco_corners)
        self.ids.append(charuco_ids)
        self.coverage.append(coverage_sample_from_corners(charuco_corners, self.image_size))
        return len(charuco_ids)

    @property
    def frame_count(self) -> int:
        return len(self.corners)

    def calibrate(self) -> CalibrationData:
        if self.image_size is None or self.frame_count < 5:
            raise ValueError("Not enough calibration frames collected (minimum 5)")
        board_corners = np.asarray(self.board.getChessboardCorners(), dtype=np.float32)
        object_points = [board_corners[ids.reshape(-1)].reshape(-1, 3) for ids in self.ids]
        image_points = [corners.reshape(-1, 2).astype(np.float32) for corners in self.corners]
        error, camera, distortion, _, _ = cv2.calibrateCamera(
            object_points, image_points, self.image_size, None, None
        )
        return CalibrationData(camera, distortion, self.image_size, float(error))
