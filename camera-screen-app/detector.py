import os
import math
import queue
import numpy as np
from ultralytics import YOLO
import torch
from PyQt6.QtCore import QThread
from PyQt6.QtGui import QImage

from train_angle_model import AngleMLP, build_features

YOLO_MODEL = os.path.join(os.path.dirname(__file__), "last.pt")
MLP_MODEL = os.path.join(os.path.dirname(__file__), "angle_mlp.pth")
CONF_THRESHOLD = 0.15
INFER_IMGSZ = 960

_yolo_model = None
_mlp_model = None


def get_yolo_model():
    global _yolo_model
    if _yolo_model is None:
        _yolo_model = YOLO(YOLO_MODEL)
    return _yolo_model


def get_mlp_model():
    global _mlp_model
    if _mlp_model is None:
        if not os.path.exists(MLP_MODEL):
            return None
        checkpoint = torch.load(MLP_MODEL, map_location="cpu", weights_only=True)
        model = AngleMLP(
            input_dim=checkpoint.get("input_dim", 7),
            hidden_dim=checkpoint.get("hidden_dim", 64),
        )
        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()
        _mlp_model = model
    return _mlp_model


def qimage_to_numpy(image):
    image = image.convertToFormat(QImage.Format.Format_RGB888)
    ptr = image.bits()
    ptr.setsize(image.sizeInBytes())
    return np.array(ptr).reshape(image.height(), image.width(), 3)


def calc_angle_user_convention(front_xy, rear_xy):
    raw_angle = math.degrees(math.atan2(front_xy[1] - rear_xy[1], front_xy[0] - rear_xy[0]))
    return (90 - raw_angle + 180) % 360 - 180


class DetectionThread(QThread):
    def __init__(self):
        super().__init__()
        self._running = False
        self.input_queue = queue.Queue(maxsize=1)
        self.result_queue = queue.Queue(maxsize=1)
        self.enabled = False
        self.confidence = CONF_THRESHOLD
        self.status_bar_msg = None

    def run(self):
        self._running = True
        yolo = get_yolo_model()
        mlp = get_mlp_model()
        while self._running:
            if not self.enabled:
                self.msleep(10)
                continue
            try:
                image = self.input_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                arr = qimage_to_numpy(image)
                results = yolo.predict(source=arr, conf=self.confidence, imgsz=INFER_IMGSZ, verbose=False)
                r = results[0]

                detections = []
                if r.keypoints is not None and len(r.keypoints.xy) > 0:
                    kpts_all = r.keypoints.xy.cpu().numpy()
                    confs = r.keypoints.conf.cpu().numpy() if r.keypoints.conf is not None else None

                    best_idx = 0
                    if confs is not None and len(confs) > 1:
                        best_idx = int(np.argmax(confs.mean(axis=1)))

                    front_xy = tuple(kpts_all[best_idx][0])
                    rear_xy = tuple(kpts_all[best_idx][1])

                    img_h, img_w = r.orig_shape
                    feat = build_features(front_xy[0], front_xy[1], rear_xy[0], rear_xy[1], img_w, img_h)

                    if mlp is not None:
                        with torch.no_grad():
                            t = torch.tensor([feat], dtype=torch.float32)
                            angle = float(mlp(t).item())
                    else:
                        angle = calc_angle_user_convention(front_xy, rear_xy)

                    box = None
                    if r.boxes is not None and len(r.boxes.xyxy) > best_idx:
                        box = tuple(r.boxes.xyxy.cpu().numpy()[best_idx])

                    conf_val = float(confs[best_idx].mean()) if confs is not None else 0.0

                    detections.append({
                        "front": front_xy,
                        "rear": rear_xy,
                        "angle": angle,
                        "box": box,
                        "confidence": conf_val,
                    })
                else:
                    self.status_bar_msg = "車が検出されませんでした"

                if self.result_queue.full():
                    try:
                        self.result_queue.get_nowait()
                    except queue.Empty:
                        pass
                self.result_queue.put_nowait(detections)
            except Exception as e:
                self.status_bar_msg = f"検出エラー: {str(e)[:50]}"

    def stop(self):
        self._running = False
        self.wait()
