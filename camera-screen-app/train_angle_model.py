"""
角度推定MLPの学習スクリプト
===========================
YOLOで検出したfront/rearキーポイント座標 + ファイル名から得たyaw角度を学習し、
画像座標から車の向き角度を直接予測するニューラルネットワークを学習する。

■ 使い方
    python train_angle_model.py --images_dir F:\\captures --model last.pt --output angle_mlp.pth

■ 入力特徴量(正規化済み)
    [front_x, front_y, rear_x, rear_y, dist, img_w_norm, img_h_norm]
    - front/rear: 画素座標を画像サイズで正規化(0~1)
    - dist: front-rear間の正規化距離
    - img_w_norm, img_h_norm: 画像サイズ(相対値)

■ 出力
    yaw角度(度数, -180~180)
"""

import re
import os
import glob
import math
import argparse

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

try:
    from ultralytics import YOLO
except ImportError:
    raise ImportError("ultralytics が必要です: pip install ultralytics")


# ============================================================
# ファイル名パース
# ============================================================

FILENAME_PATTERN = re.compile(
    r"d([\-0-9.]+)_yaw([\-+][\-0-9.]+)_pan([\-0-9.]+)_tilt([\-0-9.]+)",
    re.IGNORECASE,
)


def parse_filename(filename):
    """
    ファイル名から距離・yaw・pan・tiltを抽出。
    例: capture_0002_d0.042_yaw+0.0_pan090_tilt085.jpg
    """
    m = FILENAME_PATTERN.search(filename)
    if m is None:
        return None
    return {
        "distance": float(m.group(1)),
        "yaw": float(m.group(2)),
        "pan": float(m.group(3)),
        "tilt": float(m.group(4)),
    }


# ============================================================
# YOLO推論でfront/rear座標を取得
# ============================================================

def extract_keypoints(model, image_paths):
    """
    各画像でYOLO推論を実行し、front/rearのキーポイント座標を返す。
    戻り値: list of (front_x, front_y, rear_x, rear_y, img_w, img_h) or None(検出失敗時)
    """
    results_list = model.predict(
        source=image_paths,
        conf=0.3,
        imgsz=960,
        verbose=False,
    )

    keypoints_data = []
    for result in results_list:
        if result.keypoints is None or len(result.keypoints.xy) == 0:
            keypoints_data.append(None)
            continue

        kpts = result.keypoints.xy.cpu().numpy()  # (num, 2, 2)
        confs = result.keypoints.conf.cpu().numpy() if result.keypoints.conf is not None else None

        best_idx = 0
        if confs is not None and len(confs) > 1:
            best_idx = int(np.argmax(confs.mean(axis=1)))

        front_xy = kpts[best_idx][0]  # [u, v]
        rear_xy = kpts[best_idx][1]   # [u, v]

        img_h, img_w = result.orig_shape
        keypoints_data.append((front_xy[0], front_xy[1], rear_xy[0], rear_xy[1], img_w, img_h))

    return keypoints_data


# ============================================================
# データセット
# ============================================================

class AngleDataset(Dataset):
    def __init__(self, features, angles):
        self.features = torch.tensor(features, dtype=torch.float32)
        self.angles = torch.tensor(angles, dtype=torch.float32)

    def __len__(self):
        return len(self.angles)

    def __getitem__(self, idx):
        return self.features[idx], self.angles[idx]


def build_features(front_x, front_y, rear_x, rear_y, img_w, img_h):
    """画素座標から正規化された特徴量ベクトルを生成。"""
    fx = front_x / img_w
    fy = front_y / img_h
    rx = rear_x / img_w
    ry = rear_y / img_h
    dist = math.sqrt((fx - rx) ** 2 + (fy - ry) ** 2)
    return [fx, fy, rx, ry, dist, img_w / 1000.0, img_h / 1000.0]


# ============================================================
# MLPモデル
# ============================================================

class AngleMLP(nn.Module):
    """front/rear座標から角度を予測するシンプルなMLP。"""

    def __init__(self, input_dim=7, hidden_dim=64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.BatchNorm1d(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.BatchNorm1d(hidden_dim),
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)


# ============================================================
# 学習
# ============================================================

def train_model(model, train_loader, val_loader, epochs=200, lr=1e-3, device="cpu"):
    model.to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.SmoothL1Loss()

    best_val_loss = float("inf")
    best_state = None

    for epoch in range(1, epochs + 1):
        # --- train ---
        model.train()
        train_loss = 0.0
        for features, angles in train_loader:
            features, angles = features.to(device), angles.to(device)
            pred = model(features)
            loss = criterion(pred, angles)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * len(angles)
        train_loss /= len(train_loader.dataset)

        # --- val ---
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for features, angles in val_loader:
                features, angles = features.to(device), angles.to(device)
                pred = model(features)
                loss = criterion(pred, angles)
                val_loss += loss.item() * len(angles)
        val_loss /= len(val_loader.dataset)

        scheduler.step()

        if epoch % 20 == 0 or epoch == 1:
            print(f"Epoch {epoch:3d}/{epochs}  train_loss={train_loss:.4f}  val_loss={val_loss:.4f}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

    model.load_state_dict(best_state)
    return model


# ============================================================
# main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="角度推定MLPの学習")
    parser.add_argument("--images_dir", required=True, help="画像フォルダのパス")
    parser.add_argument("--model", required=True, help="YOLOモデルのパス(.pt)")
    parser.add_argument("--output", default="angle_mlp.pth", help="出力モデルファイル")
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--val_ratio", type=float, default=0.2)
    args = parser.parse_args()

    # 画像ファイルの収集
    exts = ("*.jpg", "*.jpeg", "*.png")
    image_paths = []
    for ext in exts:
        image_paths.extend(glob.glob(os.path.join(args.images_dir, ext)))
    image_paths = sorted(set(image_paths))

    if not image_paths:
        print("エラー: 画像が見つかりません")
        return

    print(f"画像数: {len(image_paths)}")

    # ファイル名から正解角度を取得
    valid_paths = []
    valid_yaws = []
    for p in image_paths:
        info = parse_filename(os.path.basename(p))
        if info is not None:
            valid_paths.append(p)
            valid_yaws.append(info["yaw"])

    print(f"有効な画像数: {len(valid_paths)}")
    if len(valid_paths) < 10:
        print("エラー: 有効な画像が少なすぎます(10枚以上必要)")
        return

    # yawの分布を確認
    yaw_values = sorted(set(valid_yaws))
    print(f"yaw角度の種類: {len(yaw_values)} ({[f'{y:.0f}' for y in yaw_values]})")

    # YOLOでキーポイント検出
    print("YOLO推論を実行中...")
    yolo_model = YOLO(args.model)
    kp_data = extract_keypoints(yolo_model, valid_paths)

    # 特徴量とラベルの構築(反転オーグメンテーション付き)
    features = []
    angles = []
    skipped = 0
    for i, kp in enumerate(kp_data):
        if kp is None:
            skipped += 1
            continue
        front_x, front_y, rear_x, rear_y, img_w, img_h = kp
        yaw = valid_yaws[i]

        # 元データ
        feat = build_features(front_x, front_y, rear_x, rear_y, img_w, img_h)
        features.append(feat)
        angles.append(yaw)

        # 水平反転データ: x座標を鏡写し、yawの符号を反転
        feat_flip = build_features(
            img_w - front_x, front_y,
            img_w - rear_x, rear_y,
            img_w, img_h,
        )
        features.append(feat_flip)
        angles.append(-yaw)

    print(f"検出成功: {len(kp_data) - skipped}枚 -> オーグメンテーション後: {len(features)}枚 (スキップ: {skipped}枚)")

    if len(features) < 10:
        print("エラー: 有効なデータが少なすぎます")
        return

    features = np.array(features, dtype=np.float32)
    angles = np.array(angles, dtype=np.float32)

    # データ分割
    n = len(features)
    n_val = max(1, int(n * args.val_ratio))
    indices = np.random.permutation(n)
    val_idx = indices[:n_val]
    train_idx = indices[n_val:]

    train_dataset = AngleDataset(features[train_idx], angles[train_idx])
    val_dataset = AngleDataset(features[val_idx], angles[val_idx])
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size)

    print(f"訓練: {len(train_dataset)}枚, 検証: {len(val_dataset)}枚")

    # 学習
    model = AngleMLP(input_dim=7, hidden_dim=64)
    print("学習を開始します...")
    model = train_model(model, train_loader, val_loader, epochs=args.epochs)

    # 検証結果の表示
    model.eval()
    with torch.no_grad():
        all_features = torch.tensor(features, dtype=torch.float32)
        all_preds = model(all_features).numpy()
        all_angles = angles
        errors = np.abs(all_preds - all_angles)
        print(f"\n=== 最終評価 ===")
        print(f"平均誤差: {errors.mean():.2f} 度")
        print(f"中央値誤差: {np.median(errors):.2f} 度")
        print(f"最大誤差: {errors.max():.2f} 度")
        print(f"95パーセンタイル: {np.percentile(errors, 95):.2f} 度")

    # 保存
    torch.save({
        "model_state_dict": model.state_dict(),
        "input_dim": 7,
        "hidden_dim": 64,
    }, args.output)
    print(f"\nモデルを保存しました: {args.output}")


if __name__ == "__main__":
    main()
