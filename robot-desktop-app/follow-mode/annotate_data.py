"""
車の向き検出 自動アノテーションツール (PyQt5)
========================================

学習済みYOLOv8-poseモデルを使い、画像フォルダ内の各画像に対して
front(前)/rear(後)のキーポイントを自動検出し、1枚ずつ確認・
ドラッグで修正しながらYOLO Pose形式のラベルファイルを保存するアプリです。

■ 必要なライブラリのインストール
    pip install PyQt5 ultralytics opencv-python numpy

■ 実行方法
    python annotate_data.py

■ 使い方
    1. 「モデルを開く」で学習済みの best.pt を選択
    2. 「画像フォルダを開く」でアノテーションしたい画像フォルダを選択
    3. 「保存先フォルダを選択」でラベル(.txt)の保存先フォルダを選択
       (画像フォルダを開いた時点で自動検出が実行されます)
    4. 緑の点(front)・赤の点(rear)が間違っていればドラッグして修正
    5. 「保存して次へ」(またはキーボードの S) で保存して次の画像へ
       車が写っていない画像は「車なし(スキップ)」で空ラベルを保存
    6. 「前へ」「次へ」(A / D キーまたは ←→キー) で自由に行き来できます
       (保存済みの画像を開き直すと、前回保存したラベルが読み込まれます)

保存されるラベル形式 (YOLOv8-Pose, 正規化済み):
    class_id x_center y_center width height  front_x front_y front_v  rear_x rear_y rear_v
"""

import sys
import os

try:
    import site
    for _sp in site.getsitepackages() if hasattr(site, 'getsitepackages') else []:
        _d = os.path.join(_sp, "torch", "lib")
        if os.path.isdir(_d):
            os.add_dll_directory(_d)
            os.environ["PATH"] = _d + os.pathsep + os.environ.get("PATH", "")
            break
except Exception:
    pass

import glob
import math

import numpy as np

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
    QFileDialog, QMessageBox
)
from PyQt5.QtGui import QPixmap, QPen, QBrush, QColor, QFont, QPainter
from PyQt5.QtCore import Qt, QRectF

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None


POINT_RADIUS = 7
FRONT_COLOR = QColor(0, 200, 0)
REAR_COLOR = QColor(220, 0, 0)
LINE_COLOR = QColor(255, 200, 0)
CONF_THRESHOLD = 0.3
INFER_IMGSZ = 960


class DraggablePoint(QGraphicsEllipseItem):
    """マウスでドラッグして位置を修正できるキーポイント。"""

    def __init__(self, x, y, color, on_move_callback, radius=POINT_RADIUS):
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        self.setPos(x, y)
        self.setBrush(QBrush(color))
        self.setPen(QPen(Qt.black, 1))
        self.setFlag(QGraphicsEllipseItem.ItemIsMovable, True)
        self.setFlag(QGraphicsEllipseItem.ItemSendsGeometryChanges, True)
        self.setZValue(10)
        self.on_move_callback = on_move_callback

    def itemChange(self, change, value):
        if change == QGraphicsEllipseItem.ItemPositionHasChanged and self.on_move_callback:
            self.on_move_callback()
        return super().itemChange(change, value)


class AnnotatorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("車の向き検出 自動アノテーションツール")
        self.resize(1150, 780)

        self.model = None
        self.image_paths = []
        self.current_index = -1
        self.labels_dir = None

        self.pixmap_item = None
        self.front_item = None
        self.rear_item = None
        self.line_item = None
        self.current_box = None  # (x1, y1, x2, y2) 画素座標

        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # --- 上部ツールバー ---
        top_bar = QHBoxLayout()
        self.btn_load_model = QPushButton("モデルを開く (.pt)")
        self.btn_load_model.clicked.connect(self.on_load_model)
        self.btn_load_folder = QPushButton("画像フォルダを開く")
        self.btn_load_folder.clicked.connect(self.on_load_folder)
        self.btn_load_labels_dir = QPushButton("保存先フォルダを選択")
        self.btn_load_labels_dir.clicked.connect(self.on_choose_labels_dir)
        self.lbl_model_status = QLabel("モデル: 未読み込み")

        top_bar.addWidget(self.btn_load_model)
        top_bar.addWidget(self.btn_load_folder)
        top_bar.addWidget(self.btn_load_labels_dir)
        top_bar.addStretch()
        top_bar.addWidget(self.lbl_model_status)
        main_layout.addLayout(top_bar)

        # --- 画像表示エリア ---
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setDragMode(QGraphicsView.NoDrag)
        main_layout.addWidget(self.view, stretch=1)

        # --- 情報バー ---
        info_bar = QHBoxLayout()
        self.lbl_filename = QLabel("画像: -")
        self.lbl_progress = QLabel("0 / 0")
        self.lbl_angle = QLabel("角度: -")
        angle_font = QFont()
        angle_font.setPointSize(13)
        angle_font.setBold(True)
        self.lbl_angle.setFont(angle_font)

        info_bar.addWidget(self.lbl_filename)
        info_bar.addStretch()
        info_bar.addWidget(self.lbl_progress)
        info_bar.addStretch()
        info_bar.addWidget(self.lbl_angle)
        main_layout.addLayout(info_bar)

        # --- 下部操作ボタン ---
        bottom_bar = QHBoxLayout()
        self.btn_prev = QPushButton("<< 前へ (A)")
        self.btn_prev.clicked.connect(self.show_previous)
        self.btn_redetect = QPushButton("再検出")
        self.btn_redetect.clicked.connect(self.run_auto_detect_current)
        self.btn_no_car = QPushButton("車なし(スキップ)")
        self.btn_no_car.clicked.connect(self.mark_no_car)
        self.btn_save = QPushButton("保存して次へ (S)")
        self.btn_save.clicked.connect(self.save_and_next)
        self.btn_next = QPushButton("次へ (D) >>")
        self.btn_next.clicked.connect(self.show_next)

        bottom_bar.addWidget(self.btn_prev)
        bottom_bar.addWidget(self.btn_redetect)
        bottom_bar.addWidget(self.btn_no_car)
        bottom_bar.addStretch()
        bottom_bar.addWidget(self.btn_save)
        bottom_bar.addWidget(self.btn_next)
        main_layout.addLayout(bottom_bar)

        self.statusBar().showMessage("モデルと画像フォルダを開いてください。")

    # ------------------------------------------------------------ ファイル操作
    def on_load_model(self):
        if YOLO is None:
            QMessageBox.critical(self, "エラー", "ultralytics がインストールされていません。\npip install ultralytics を実行してください。")
            return

        path, _ = QFileDialog.getOpenFileName(self, "モデルファイルを選択", "", "PyTorch Model (*.pt)")
        if not path:
            return
        try:
            self.model = YOLO(path)
            self.lbl_model_status.setText(f"モデル: {os.path.basename(path)}")
            self.statusBar().showMessage("モデルを読み込みました。")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"モデルの読み込みに失敗しました:\n{e}")

    def on_load_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "画像フォルダを選択")
        if not folder:
            return
        exts = ("*.jpg", "*.jpeg", "*.png", "*.bmp")
        paths = []
        for ext in exts:
            paths.extend(glob.glob(os.path.join(folder, ext)))
            paths.extend(glob.glob(os.path.join(folder, ext.upper())))
        self.image_paths = sorted(set(paths))

        if not self.image_paths:
            QMessageBox.warning(self, "警告", "画像が見つかりませんでした。")
            return

        self.current_index = 0
        self.show_image(self.current_index)

    def on_choose_labels_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "ラベル保存先フォルダを選択")
        if folder:
            self.labels_dir = folder
            self.statusBar().showMessage(f"保存先: {folder}")

    # ------------------------------------------------------------ 画像表示
    def show_image(self, index):
        if not (0 <= index < len(self.image_paths)):
            return
        self.current_index = index
        img_path = self.image_paths[index]

        self.scene.clear()
        self.front_item = None
        self.rear_item = None
        self.line_item = None
        self.current_box = None

        pixmap = QPixmap(img_path)
        if pixmap.isNull():
            self.statusBar().showMessage(f"画像を読み込めませんでした: {img_path}")
            return

        self.pixmap_item = self.scene.addPixmap(pixmap)
        self.scene.setSceneRect(QRectF(pixmap.rect()))
        self.view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

        self.lbl_filename.setText(f"画像: {os.path.basename(img_path)}")
        self.lbl_progress.setText(f"{index + 1} / {len(self.image_paths)}")

        w, h = pixmap.width(), pixmap.height()

        # 既存のラベルがあれば読み込み、なければ自動検出する
        front_xy, rear_xy = None, None
        label_path = self._label_path_for(img_path)
        if label_path and os.path.exists(label_path):
            loaded = self._load_label(label_path, w, h)
            if loaded is not None:
                front_xy, rear_xy = loaded
                self.statusBar().showMessage("既存のラベルを読み込みました。")

        if front_xy is None or rear_xy is None:
            front_xy, rear_xy, box = self._auto_detect(img_path, w, h)
            self.current_box = box

        self._place_points(front_xy, rear_xy)
        self.update_line_and_angle()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.pixmap_item is not None:
            self.view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

    # ------------------------------------------------------------ 検出処理
    def _auto_detect(self, img_path, w, h):
        """モデルで front/rear を検出。戻り値: (front_xy, rear_xy, box[x1,y1,x2,y2] or None)"""
        if self.model is None:
            return (w * 0.5, h * 0.4), (w * 0.5, h * 0.6), None

        results = self.model.predict(source=img_path, conf=CONF_THRESHOLD, imgsz=INFER_IMGSZ, verbose=False)
        r = results[0]

        if r.keypoints is None or len(r.keypoints.xy) == 0:
            self.statusBar().showMessage("車が検出されませんでした。手動で点を配置してください。")
            return (w * 0.5, h * 0.4), (w * 0.5, h * 0.6), None

        kpts_all = r.keypoints.xy.cpu().numpy()  # (num_cars, 2, 2)
        confs = r.keypoints.conf.cpu().numpy() if r.keypoints.conf is not None else None

        best_idx = 0
        if confs is not None and len(confs) > 1:
            best_idx = int(np.argmax(confs.mean(axis=1)))

        front_xy, rear_xy = kpts_all[best_idx]

        box = None
        if r.boxes is not None and len(r.boxes.xyxy) > best_idx:
            box = tuple(r.boxes.xyxy.cpu().numpy()[best_idx])

        return tuple(front_xy), tuple(rear_xy), box

    def run_auto_detect_current(self):
        if self.model is None:
            QMessageBox.warning(self, "警告", "先にモデルを読み込んでください。")
            return
        if not (0 <= self.current_index < len(self.image_paths)):
            return

        img_path = self.image_paths[self.current_index]
        pixmap = self.pixmap_item.pixmap()
        w, h = pixmap.width(), pixmap.height()

        front_xy, rear_xy, box = self._auto_detect(img_path, w, h)
        self.current_box = box

        if self.front_item is not None:
            self.scene.removeItem(self.front_item)
        if self.rear_item is not None:
            self.scene.removeItem(self.rear_item)

        self._place_points(front_xy, rear_xy)
        self.update_line_and_angle()
        self.statusBar().showMessage("再検出しました。")

    # ------------------------------------------------------------ 点・線の描画
    def _place_points(self, front_xy, rear_xy):
        self.front_item = DraggablePoint(front_xy[0], front_xy[1], FRONT_COLOR, self.update_line_and_angle)
        self.rear_item = DraggablePoint(rear_xy[0], rear_xy[1], REAR_COLOR, self.update_line_and_angle)
        self.scene.addItem(self.front_item)
        self.scene.addItem(self.rear_item)

    def update_line_and_angle(self):
        if self.front_item is None or self.rear_item is None:
            return

        fx, fy = self.front_item.pos().x(), self.front_item.pos().y()
        rx, ry = self.rear_item.pos().x(), self.rear_item.pos().y()

        if self.line_item is not None:
            self.scene.removeItem(self.line_item)
        self.line_item = self.scene.addLine(fx, fy, rx, ry, QPen(LINE_COLOR, 2))
        self.line_item.setZValue(5)

        dx = fx - rx
        dy = -(fy - ry)  # 画像y軸は下向きのため反転
        angle = math.degrees(math.atan2(dy, dx)) % 360
        self.lbl_angle.setText(f"角度: {angle:.1f} 度")

    # ------------------------------------------------------------ 保存・読み込み
    def _label_path_for(self, img_path):
        if not self.labels_dir:
            return None
        base = os.path.splitext(os.path.basename(img_path))[0]
        return os.path.join(self.labels_dir, base + ".txt")

    def _load_label(self, path, w, h):
        with open(path, "r", encoding="utf-8") as f:
            line = f.readline().strip()
        if not line:
            return None

        vals = list(map(float, line.split()))
        if len(vals) < 11:
            return None

        _cls, xc, yc, bw, bh = vals[:5]
        kpts = vals[5:]

        x1 = (xc - bw / 2) * w
        y1 = (yc - bh / 2) * h
        x2 = (xc + bw / 2) * w
        y2 = (yc + bh / 2) * h
        self.current_box = (x1, y1, x2, y2)

        front_xy = (kpts[0] * w, kpts[1] * h)
        rear_xy = (kpts[3] * w, kpts[4] * h)
        return front_xy, rear_xy

    def save_current(self):
        if not self.labels_dir:
            QMessageBox.warning(self, "警告", "先に保存先フォルダを選択してください。")
            return False
        if self.front_item is None or self.rear_item is None:
            return False

        img_path = self.image_paths[self.current_index]
        pixmap = self.pixmap_item.pixmap()
        w, h = pixmap.width(), pixmap.height()

        fx, fy = self.front_item.pos().x(), self.front_item.pos().y()
        rx, ry = self.rear_item.pos().x(), self.rear_item.pos().y()

        if self.current_box is not None:
            x1, y1, x2, y2 = self.current_box
        else:
            # 検出ボックスがない場合、2点から余白付きでバウンディングボックスを推定
            pad = 0.4
            min_x, max_x = min(fx, rx), max(fx, rx)
            min_y, max_y = min(fy, ry), max(fy, ry)
            box_w = max(max_x - min_x, w * 0.1)
            box_h = max(max_y - min_y, h * 0.1)
            x1 = max(0.0, min_x - box_w * pad)
            y1 = max(0.0, min_y - box_h * pad)
            x2 = min(float(w), max_x + box_w * pad)
            y2 = min(float(h), max_y + box_h * pad)

        xc, yc = ((x1 + x2) / 2) / w, ((y1 + y2) / 2) / h
        bw, bh = (x2 - x1) / w, (y2 - y1) / h
        fxn, fyn = fx / w, fy / h
        rxn, ryn = rx / w, ry / h

        line = (
            f"0 {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f} "
            f"{fxn:.6f} {fyn:.6f} 2 {rxn:.6f} {ryn:.6f} 2\n"
        )

        label_path = self._label_path_for(img_path)
        with open(label_path, "w", encoding="utf-8") as f:
            f.write(line)

        self.statusBar().showMessage(f"保存しました: {label_path}")
        return True

    def save_and_next(self):
        if self.save_current():
            self.show_next()

    def mark_no_car(self):
        if not self.labels_dir:
            QMessageBox.warning(self, "警告", "先に保存先フォルダを選択してください。")
            return
        img_path = self.image_paths[self.current_index]
        label_path = self._label_path_for(img_path)
        open(label_path, "w", encoding="utf-8").close()  # 空ファイル = 車なし
        self.statusBar().showMessage("車なしとして記録しました。")
        self.show_next()

    # ------------------------------------------------------------ ナビゲーション
    def show_next(self):
        if self.current_index < len(self.image_paths) - 1:
            self.show_image(self.current_index + 1)
        else:
            QMessageBox.information(self, "完了", "最後の画像です。")

    def show_previous(self):
        if self.current_index > 0:
            self.show_image(self.current_index - 1)

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key_Right, Qt.Key_D):
            self.show_next()
        elif key in (Qt.Key_Left, Qt.Key_A):
            self.show_previous()
        elif key == Qt.Key_S:
            self.save_and_next()
        else:
            super().keyPressEvent(event)


def main():
    app = QApplication(sys.argv)
    window = AnnotatorWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()