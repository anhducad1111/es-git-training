# rccar_pose_inference

車の姿勢（yaw角・距離）推定モジュール。追従制御アプリ（`follow_controller.py`）と同一プロセス内で動く、独立してimportできるPythonパッケージ。**プロセス分離・HTTP/WebSocket API化はしていない** — このディレクトリを丸ごとコピーするかPythonパスに追加して`import`するだけで使える。

## これは何か / 何のためにあるか

`app2/detectors.py`の`RcCarPoseDetector`（YOLOv8-poseキーポイント→床平面射影→yaw/距離）を土台に、以下を追加したもの:

1. **カルマンフィルタによる時系列平滑化**（`pose_kalman.py`） — フレーム単独ではなく、直前の速度・向きを使って滑らかに推定。観測が一時的に取れなくても`max_coast_sec`（既定1.0秒）まで予測のみで補間
2. **ArUco距離の信頼度重み付け融合**（`pose_fusion.py`） — Ground射影とArUcoの単純上書きではなく、実測誤差(MAE)ベースの重み付け平均
3. **ジンバル（pan/tilt）補正**（`gimbal_transform.py`） — カメラが追従のために回転しても、車体基準の座標系で安定した推定を保つための座標変換とゲーティング

全体の統合は`pose_inference.py`の`PoseInference`クラスが行う。

## 元になった設計文書

- `docs/superpowers/specs/2026-09-11-pose-inference-service-handoff.md` — モジュール切り出しの契約（`DetectionResult`の形式、呼び出し側との連携）
- `docs/superpowers/plans/2026-09-11-pose-inference-module.md` — カルマンフィルタ・ArUco融合のプラン
- `docs/superpowers/specs/2026-09-11-gimbal-pose-compensation-design.md` — ジンバル補正の設計
- `docs/superpowers/plans/2026-09-11-gimbal-pose-compensation.md` — ジンバル補正のプラン（**この`rccar_pose_inference/`は、そのプランのTask 1・2・4・5・7を実装したもの**。Task 3・6は本体アプリのライブコード変更を伴うため未実装 — 下記「実装者が行う残作業」参照）

いずれも4文書とも読んでから統合作業に入ることを推奨する。特にジンバル補正の**符号規約（パンの正負とカメラの回転方向の対応）はコードだけでは確定できない**ため、gimbal-pose-compensation-designの「符号規約の注意」と、下記「実装者が行う残作業」のステップ4は必読。

## 公開インターフェース

```python
from rccar_pose_inference import PoseInference, DetectionResult

detector = PoseInference(
    model_dir=Path("rccar_pose_model"),   # config.json + weights/best.pt を含むディレクトリ
    weights_path=Path("rccar_pose_model/weights/best.pt"),
    confidence=0.35,
    gimbal_provider=None,  # 下記「ジンバル補正を有効にする」参照。Noneなら無効（据え置きカメラと同じ挙動）
)

result: DetectionResult = detector.infer(frame)  # frame: np.ndarray (BGR, cv2形式)
```

```python
@dataclass(frozen=True)
class DetectionResult:
    yaw_deg: float | None       # 車の向き（度）。欠測時はNone
    dist_m: float | None        # 距離（m）。欠測時はNone
    confidence: float           # YOLO検出スコア（coast中は減衰した値）
    bbox: tuple[int, int, int, int] | None  # (x, y, w, h)、画像座標
    frame_w: int
    frame_h: int
    timestamp: float            # time.time()
```

`infer()`はブロッキングでよい（呼び出し側がスレッド/タイマーで~10Hz呼び出す想定）。**`bbox`の有無と`yaw_deg`/`dist_m`の有無は独立**: 遠距離で`bbox`はあるが`yaw_deg`/`dist_m`がNoneというケースは正常（`APPROACHING_BLIND`状態が前提とする挙動）。

## ジンバル補正を有効にする

`gimbal_provider`に、呼ぶと`(pan_deg, tilt_deg, is_settled)`を返す関数を渡す:

```python
detector = PoseInference(
    model_dir=..., weights_path=...,
    gimbal_provider=gimbal_thread.get_pan_tilt_state,  # 下記Task 3参照、まだ存在しない
)
```

- `pan_deg` / `tilt_deg`: ジンバルへの**コマンド値**（サーボの実角度フィードバックではない。理由は`gimbal-pose-compensation-design.md`参照）
- `is_settled`: サーボが目標角にほぼ到達している（動作中でない）かどうか

`gimbal_provider=None`（デフォルト）なら座標変換・チルトゲーティング・信頼度スケーリングは一切行われず、据え置きカメラとして今まで通り動く。

## `config.json`の設定項目

```json
{
  "sigma_ground_m": 0.0162,
  "sigma_aruco_m": 0.0133,
  "max_coast_sec": 1.0,
  "yaw_snap_threshold_deg": 90.0,
  "calibration_tilt_deg": 70.0,
  "tilt_max_deviation_deg": 10.0,
  "gimbal_center_pan_deg": 90.0
}
```

- `sigma_ground_m` / `sigma_aruco_m`: Ground/ArUco距離推定の標準偏差（融合の重み。既存の実測MAE値をそのまま採用済み）
- `max_coast_sec`: 予測のみで補間する上限秒数
- `yaw_snap_threshold_deg`: この角度以上のyaw変化は「車の反転」とみなし、平滑化せず即座に反映する（既定90°）
- `calibration_tilt_deg` / `tilt_max_deviation_deg`: チルトがこの範囲外なら距離推定を信頼しない。**`GimbalThread`のチルト復帰ロジックの目標角と同じ値を使うこと**（ズレると効果が薄れる）
- `gimbal_center_pan_deg`: ジンバル中央のpan値（既定90.0、サーボ範囲0-180の中央）

## 動作確認

```bash
cd D:\robot-desktop-app
python -m pytest rccar_pose_inference/tests/ -v
```

28テスト全件パス確認済み（2026-09-11）。`ultralytics`・`cv2`・`numpy`が必要（実モデルはロードせずモック化しているテストが大半だが、`test_infer_combines_keypoint_pose_aruco_fusion_and_kalman`等は`ultralytics.YOLO`をmonkeypatchしている）。

## 実装者が行う残作業（このパッケージの外、本体アプリ側）

このパッケージ自体は完結しているが、**本体アプリに配線するまでは何も変わらない**。以下は`docs/superpowers/plans/2026-09-11-pose-inference-module.md`と`docs/superpowers/plans/2026-09-11-gimbal-pose-compensation.md`のTaskを本パッケージに合わせて読み替えたチェックリスト（詳細な理由・コード例は各プラン文書を参照）:

1. **`follow_detector.py`の切り替え**（[[pose-inference-module]] Task 6相当）: `from app2.detectors import RcCarPoseDetector`を`from rccar_pose_inference import PoseInference`に置き換え、`result.boxes`/`result.yaw_deg`のような古いDetection形式への直接アクセス（現状バグって動いていない箇所）を`DetectionResult`ベースに書き換える
2. **`GimbalThread`への状態取得追加**（gimbal-pose-compensation Task 3）: `follow_controller.py`の`GimbalThread`に`get_pan_tilt_state() -> tuple[float, float, bool]`と`is_settled()`を追加する。実装コードは`docs/superpowers/plans/2026-09-11-gimbal-pose-compensation.md`のTask 3にそのまま書いてある
3. **`PoseInference`構築時に`gimbal_provider`を渡す**（gimbal-pose-compensation Task 6 Step 1-2）: `follow_detector.py`の`FollowDetector`に`gimbal_thread`を注入できるようにし、`PoseInference(..., gimbal_provider=gimbal_thread.get_pan_tilt_state)`で構築する
4. **`ControlThread._compute_command()`の事後yaw補正を削除**（gimbal-pose-compensation Task 6 Step 3）: `yaw_deg = yaw_deg + camera_offset`の行を削除する。理由: 本パッケージの`PoseInference.infer()`が返す`yaw_deg`は既にロボット本体相対（変換済み）なので、ここで再度加算すると二重補正になる。`pan_error`を使った`combined_heading_error`の計算（操舵判断用の別機構）は削除しないこと
5. **【必須】実機での符号検証**（gimbal-pose-compensation Task 6 Step 4）: `gimbal_transform.rotate_pose_to_robot_frame`の`camera_left_rotation_deg`の符号は、`GimbalThread`のパン値増減と実際のサーボ回転方向の対応関係に依存し、**コードだけでは確定できない**（`GimbalThread.get_camera_yaw_offset()`のdocstringと実装が矛盾している既知の問題がある）。プラン文書のTask 6 Step 4の手順に従い、実機でパンを既知方向に動かして`X`の符号が直感と一致するか確認すること。逆であれば`_apply_gimbal_compensation()`内の`camera_left_rotation_deg = pan_deg - self._gimbal_center_pan_deg`の符号を反転する（`gimbal_transform.py`自体は変更不要）
6. 上記1-5が終わったら、`docs/superpowers/plans/2026-09-11-gimbal-tracking-design.md`のチルト復帰ロジック（`GimbalThread._compute_tilt_step`）も未実装であれば合わせて実装する（本パッケージの`tilt_max_deviation_deg`ゲートは「チルトが外れている間は距離を捨てる」防御であり、「チルトを戻す」制御そのものは別途必要）
