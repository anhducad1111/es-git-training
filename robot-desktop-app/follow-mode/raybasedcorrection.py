"""
光線幾何(レイキャスティング)によるパースペクティブ補正
==========================================================

カメラの「位置」が分からなくても、以下の2つだけで補正が可能な方法です。
  1. カメラのレンズ内部パラメータ(焦点距離・主点) -> 1回だけ測ればOK(以後不変)
  2. 撮影時のtilt角度(地面に対する見下ろし角)、必要なら絶対角度用にpan角度

■ 原理(要点)
front/rearの各キーポイント(画像上のピクセル座標)を、カメラを頂点とする
「3D方向の光線」に変換し、その光線が地面(水平面)と交わる点を計算します。
2点の交点を結んだベクトルの"向き"は、実はカメラの高さに依存しません
(高さが変わっても、2点とも比例してスケールするだけで方向は変わらないため)。
そのため、カメラの位置(XYZ)を一切知らなくても、tilt角度とレンズパラメータだけで
正しい向きが計算できます。

■ 必要なライブラリ
    pip install opencv-python numpy

■ 使い方
    1. calibrate_intrinsics() で1回だけレンズの内部パラメータを測定する
       (チェッカーボードを様々な角度から10枚前後撮影して使う、標準的な手順)
    2. tilt角度の基準を合わせる(calibrate_tilt_zero, 下記参照)
    3. 以降は、front/rearの画素座標 + その時のtilt(・必要ならpan)を
       estimate_yaw_from_rays() に渡すだけで、位置に依存しない角度が得られる
"""

import math

import cv2
import numpy as np


# ============================================================
# 1. レンズの内部パラメータ(内部キャリブレーション、1回だけでOK)
# ============================================================

def calibrate_intrinsics(checkerboard_images, pattern_size=(9, 6), square_size_cm=2.5):
    """
    複数枚のチェッカーボード画像から、カメラの内部パラメータ(fx, fy, cx, cy, 歪み係数)を計算する。
    checkerboard_images: 画像パスのリスト(色々な角度・距離から10枚前後推奨)
    pattern_size: チェッカーボードの内側の交点数 (横, 縦)
    square_size_cm: マス目1つの実寸(cm)

    このキャリブレーションは「カメラ(レンズ)固有の値」を求めるものなので、
    実際に運用する場所やカメラの位置・向きとは無関係に、1回だけ行えばOKです。
    """
    objp = np.zeros((pattern_size[0] * pattern_size[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:pattern_size[0], 0:pattern_size[1]].T.reshape(-1, 2)
    objp *= square_size_cm

    objpoints, imgpoints = [], []
    img_shape = None

    for path in checkerboard_images:
        img = cv2.imread(path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img_shape = gray.shape[::-1]

        found, corners = cv2.findChessboardCorners(gray, pattern_size)
        if found:
            objpoints.append(objp)
            imgpoints.append(corners)
        else:
            print(f"チェッカーボードが検出できませんでした: {path}")

    if len(objpoints) < 5:
        raise RuntimeError("有効な画像が少なすぎます。5枚以上のチェッカーボード画像を用意してください。")

    ret, K, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, img_shape, None, None)

    print("キャリブレーション完了")
    print("K (内部パラメータ行列):\n", K)
    print("歪み係数:\n", dist)

    np.savez("camera_intrinsics.npz", K=K, dist=dist)
    return K, dist


def load_intrinsics(path="camera_intrinsics.npz"):
    data = np.load(path)
    return data["K"], data["dist"]


# ============================================================
# 2. tilt角度の基準合わせ(サーボの値 <-> 実際の物理角度)
# ============================================================
"""
サーボの「tilt085」のような値が、実際に「水平から何度下を向いているか」と
一致しているとは限りません(サーボの取り付け角度のオフセットがあるため)。

簡単な基準合わせの方法:
1. カメラを手や治具で「完全に水平(地面と平行)」にした状態で、その時のtilt値を記録する
   -> これが TILT_ZERO_OFFSET になる
2. 実際の物理tilt角度 = (tilt_servo_value - TILT_ZERO_OFFSET) * (適切な係数)
   ※ サーボの値が度数と1:1で対応している場合は係数=1でOK。
     対応していない場合は、既知の角度2点で記録して比例係数を求めてください。
"""

TILT_ZERO_OFFSET = 90  # 例: tilt=90のときに水平になるサーボの場合。実測して書き換えてください
TILT_DEG_PER_UNIT = 1.0  # サーボの値と度数が1:1対応でない場合はここを調整


def servo_tilt_to_degrees(tilt_servo_value):
    return (tilt_servo_value - TILT_ZERO_OFFSET) * TILT_DEG_PER_UNIT


PAN_ZERO_OFFSET = 90  # pan=90のときを基準(0度)とする場合。用途に応じて調整
PAN_DEG_PER_UNIT = 1.0


def servo_pan_to_degrees(pan_servo_value):
    return (pan_servo_value - PAN_ZERO_OFFSET) * PAN_DEG_PER_UNIT


# ============================================================
# 3. 光線幾何による角度計算(本体)
# ============================================================

def pixel_to_ray(u, v, K):
    """画素座標(u,v)を、カメラ座標系での方向ベクトル(正規化前)に変換する。"""
    fx, fy = K[0, 0], K[1, 1]
    cx, cy = K[0, 2], K[1, 2]
    x = (u - cx) / fx
    y = (v - cy) / fy
    return np.array([x, y, 1.0])


def ground_plane_normal(tilt_deg):
    """
    カメラ座標系(x:右, y:下, z:前方)における、地面(水平面)の法線ベクトル。
    tilt_deg: 水平から下向きに何度カメラが傾いているか(下向きが正)。
    tilt=0(水平)のとき、法線は真下(カメラのy軸正方向)を向く。
    """
    theta = math.radians(tilt_deg)
    # カメラが下を向くほど、法線はz方向(前方)に傾く
    n = np.array([0.0, math.cos(theta), math.sin(theta)])
    return n / np.linalg.norm(n)


def ray_ground_point_direction(ray, normal):
    """
    光線(ray)と地面(法線normal, 原点からの距離は任意=方向にしか影響しないので無視)の
    交点を、スケール任意で計算する(方向だけが欲しいので高さの絶対値は不要)。
    """
    denom = np.dot(normal, ray)
    if abs(denom) < 1e-8:
        # 光線が地面とほぼ平行(地平線付近)。計算不可。
        return None
    t = 1.0 / denom  # 高さ(d)を1として計算。方向だけが目的なのでdの値は結果の向きに影響しない
    return t * ray


def estimate_yaw_from_rays(front_uv, rear_uv, K, tilt_deg, pan_deg=None):
    """
    front/rearの画素座標から、カメラの位置に依存しない角度を計算する。

    front_uv, rear_uv: (u, v) 画素座標
    K: カメラの内部パラメータ行列 (calibrate_intrinsics / load_intrinsics で取得)
    tilt_deg: 撮影時の物理tilt角度(度数。servo_tilt_to_degrees()で変換したもの)
    pan_deg: 撮影時の物理pan角度(度数)。Noneの場合はカメラ基準のローカル角度を返す。
             値を渡すと、その分だけ回転させた「絶対角度」を返す。

    戻り値: 角度(度数)
    """
    r_front = pixel_to_ray(front_uv[0], front_uv[1], K)
    r_rear = pixel_to_ray(rear_uv[0], rear_uv[1], K)

    n = ground_plane_normal(tilt_deg)

    p_front = ray_ground_point_direction(r_front, n)
    p_rear = ray_ground_point_direction(r_rear, n)

    if p_front is None or p_rear is None:
        raise ValueError("光線が地平線付近のため計算できません(tilt角度や検出点を確認してください)。")

    # 地面上でのベクトル(カメラのローカル座標系: x=右, z=前方)
    dx = p_front[0] - p_rear[0]
    dz = p_front[2] - p_rear[2]

    # カメラのローカル基準での角度(カメラの正面方向=0度、反時計回りに増加)
    angle_local = math.degrees(math.atan2(dx, dz))

    if pan_deg is not None:
        angle_world = (angle_local + pan_deg) % 360
        return angle_world

    return angle_local % 360


# ============================================================
# 4. 既存パイプラインへの組み込み例
# ============================================================
"""
    K, dist = load_intrinsics()  # 起動時に1回だけ読み込み

    ...(YOLOで front_xy, rear_xy を検出。tilt_servo, pan_servo は撮影時の値)...

    tilt_deg = servo_tilt_to_degrees(tilt_servo)
    pan_deg = servo_pan_to_degrees(pan_servo)

    angle = estimate_yaw_from_rays(front_xy, rear_xy, K, tilt_deg, pan_deg)
    print(f"補正後の角度: {angle:.1f} 度")

■ 注意点・前提条件
- 地面が「平ら」であること(車がスロープなどにいる場合は誤差が出ます)
- カメラの「ロール(左右の傾き)」がないこと(斜めに傾いている場合は追加の補正が必要です)
- front/rearのキーポイントが、実質的に地面付近の高さにあると仮定しています
  (車体の上の方についたキーポイントだと、多少の誤差が出ます)
- TILT_ZERO_OFFSET / PAN_ZERO_OFFSET は、実際に測って書き換える必要があります
  (ここがズレると、計算結果全体が一定量ズレます)
"""


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="光線幾何による位置非依存の角度補正")
    sub = parser.add_subparsers(dest="command", required=True)

    p1 = sub.add_parser("calibrate", help="チェッカーボード画像からレンズ内部パラメータを計算")
    p1.add_argument("--images", nargs="+", required=True, help="チェッカーボード画像のパス(複数)")
    p1.add_argument("--pattern", nargs=2, type=int, default=[9, 6], metavar=("COLS", "ROWS"))
    p1.add_argument("--square-size", type=float, default=2.5, help="マス目1つの実寸(cm)")

    p2 = sub.add_parser("test", help="1組のfront/rear座標で角度計算をテスト")
    p2.add_argument("--front", nargs=2, type=float, required=True, metavar=("U", "V"))
    p2.add_argument("--rear", nargs=2, type=float, required=True, metavar=("U", "V"))
    p2.add_argument("--tilt-servo", type=float, required=True)
    p2.add_argument("--pan-servo", type=float, default=None)

    args = parser.parse_args()

    if args.command == "calibrate":
        calibrate_intrinsics(args.images, pattern_size=tuple(args.pattern), square_size_cm=args.square_size)

    elif args.command == "test":
        K, dist = load_intrinsics()
        tilt_deg = servo_tilt_to_degrees(args.tilt_servo)
        pan_deg = servo_pan_to_degrees(args.pan_servo) if args.pan_servo is not None else None
        angle = estimate_yaw_from_rays(tuple(args.front), tuple(args.rear), K, tilt_deg, pan_deg)
        print(f"補正後の角度: {angle:.1f} 度")