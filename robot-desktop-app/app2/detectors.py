from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from .calibration import CalibrationData, load_calibration
from .marker_tracking import MarkerPose, marker_pose_from_corners
from .rccar_pose_model.geometry import Aruco as RcCarAruco
from .rccar_pose_model.geometry import Ground as RcCarGround

# Self-contained inference bundle (trained weights + calibration config) for
# RcCarPoseDetector, copied out of the separate captures/rccar_pose training
# project so this app can run/ship without depending on it. To refresh after
# retraining, copy that project's config.json and
# runs/rccar_pose/weights/best.pt over the files in this directory.
RCCAR_POSE_MODEL_DIR = Path(__file__).parent / "rccar_pose_model"


@dataclass(frozen=True)
class Detection:
    boxes: list[tuple[int, int, int, int]]
    labels: list[str]
    scores: list[float]
    poses: list[MarkerPose | None] = field(default_factory=list)
    yaw_deg: float | None = None
    dist_m: float | None = None


class Detector:
    def detect(self, frame: np.ndarray) -> Detection:
        raise NotImplementedError


class NullDetector(Detector):
    def detect(self, frame: np.ndarray) -> Detection:
        return Detection([], [], [])


class HogDetector(Detector):
    def __init__(self) -> None:
        self._hog = cv2.HOGDescriptor()
        self._hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def detect(self, frame: np.ndarray) -> Detection:
        boxes, weights = self._hog.detectMultiScale(
            frame, winStride=(8, 8), padding=(8, 8), scale=1.05
        )
        return Detection(
            [tuple(int(v) for v in box) for box in boxes],
            ["person"] * len(boxes),
            [float(weight) for weight in weights],
        )


class ArucoDetector(Detector):
    def __init__(self, marker_size_m: float = 0.05, calibration: CalibrationData | None = None) -> None:
        dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self._detector = cv2.aruco.ArucoDetector(dictionary, cv2.aruco.DetectorParameters())
        self._marker_size = marker_size_m
        self._calibration = calibration

    def detect(self, frame: np.ndarray) -> Detection:
        corners, ids, _ = self._detector.detectMarkers(frame)
        if ids is None:
            return Detection([], [], [])
        boxes: list[tuple[int, int, int, int]] = []
        labels: list[str] = []
        scores: list[float] = []
        poses: list[MarkerPose | None] = []
        for marker_corners, marker_id in zip(corners, ids.reshape(-1)):
            points = marker_corners.reshape(4, 2)
            x, y = points.min(axis=0).astype(int)
            right, bottom = points.max(axis=0).astype(int)
            pose = None
            if self._calibration is not None:
                pose = marker_pose_from_corners(
                    points,
                    self._marker_size,
                    self._calibration.camera_matrix,
                    self._calibration.distortion,
                )
            boxes.append((int(x), int(y), int(right - x), int(bottom - y)))
            labels.append(f"marker {int(marker_id)}")
            scores.append(1.0)
            poses.append(pose)
        return Detection(boxes, labels, scores, poses)


class UltralyticsDetector(Detector):
    def __init__(self, model_name: str = "yolo11n.pt", confidence: float = 0.35) -> None:
        from ultralytics import YOLO

        self._model = YOLO(model_name)
        self._confidence = confidence

    def detect(self, frame: np.ndarray) -> Detection:
        result = self._model.predict(frame, conf=self._confidence, verbose=False)[0]
        boxes = result.boxes.xyxy.cpu().numpy().astype(int).tolist()
        xywh = [(x1, y1, x2 - x1, y2 - y1) for x1, y1, x2, y2 in boxes]
        labels = [result.names[int(v)] for v in result.boxes.cls.cpu().numpy()]
        scores = [float(v) for v in result.boxes.conf.cpu().numpy()]
        return Detection(xywh, labels, scores)


class RcCarPoseDetector(Detector):
    """Hybrid RC-car pose detector: YOLOv8-pose keypoints (L/R wheel + front
    ground contact) -> calibrated floor-plane model -> yaw/distance, refined
    with ArUco distance when a marker is visible. Trained/calibrated by the
    separate captures/rccar_pose project; see its README for details.
    """

    def __init__(self, model_dir: Path = RCCAR_POSE_MODEL_DIR, confidence: float = 0.35) -> None:
        model_dir = Path(model_dir)
        weights = model_dir / "weights" / "best.pt"
        if not weights.is_file():
            raise FileNotFoundError(f"trained rccar_pose model not found: {weights}")

        config_path = model_dir / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.is_file() else {}

        self._ground = RcCarGround(config["ground"]) if "ground" in config else None
        self._aruco = RcCarAruco(config)
        self._use_aruco_dist = bool(config.get("use_aruco_dist", True))

        from ultralytics import YOLO

        self._model = YOLO(str(weights))
        self._confidence = confidence

    def detect(self, frame: np.ndarray) -> Detection:
        result = self._model.predict(frame, conf=self._confidence, verbose=False)[0]
        if not len(result.boxes):
            return Detection([], [], [])

        best = int(result.boxes.conf.argmax())
        x1, y1, x2, y2 = result.boxes.xyxy[best].tolist()
        score = float(result.boxes.conf[best])

        keypoints = None
        if result.keypoints is not None:
            candidate = result.keypoints.xy[best].cpu().numpy()
            if candidate.shape[0] >= 3 and candidate[:, 0].max() > 0:
                keypoints = candidate[:3]

        yaw_deg = dist_m = None
        if keypoints is not None and self._ground is not None:
            pose = self._ground.pose(keypoints[0], keypoints[1], keypoints[2])
            if pose is not None:
                yaw_deg, dist_m = pose["yaw_deg"], pose["dist_m"]

        marker = self._aruco(frame)
        if marker is not None and self._use_aruco_dist:
            dist_m = marker["dist_m"]

        label_parts = ["car"]
        if yaw_deg is not None:
            label_parts.append(f"yaw{yaw_deg:+.0f}")
        if dist_m is not None:
            label_parts.append(f"d{dist_m:.2f}m")

        box = (int(x1), int(y1), int(x2 - x1), int(y2 - y1))
        return Detection([box], [" ".join(label_parts)], [score], yaw_deg=yaw_deg, dist_m=dist_m)


def create_detector(kind: str, confidence: float = 0.35, marker_size_m: float = 0.05, calibration_path: str = "camera_calibration.json") -> Detector:
    if kind == "none":
        return NullDetector()
    if kind == "hog":
        return HogDetector()
    if kind == "aruco":
        try:
            calibration = load_calibration(calibration_path)
        except FileNotFoundError:
            calibration = None
        return ArucoDetector(marker_size_m, calibration)
    if kind == "yolo":
        return UltralyticsDetector(confidence=confidence)
    if kind == "rccar":
        return RcCarPoseDetector(confidence=confidence)
    raise ValueError(f"unknown detector: {kind}")
