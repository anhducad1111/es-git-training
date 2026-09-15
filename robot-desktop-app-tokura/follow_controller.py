import math
import queue
import time
import threading
from dataclasses import dataclass
from enum import Enum
from queue import Queue
from typing import Optional, Callable

# Unified angle calculation constants
# Vehicle front (12 o'clock) = 0 degrees
# Right (3 o'clock) = +90 degrees
# Left (9 o'clock) = -90 degrees
PAN_CENTER = 85  # Servo center position = 0 degrees
PAN_RANGE_HALF = 85  # Half of servo range (0-170)
PHYSICAL_RANGE_HALF = 90.0  # Half of physical angle range (-90 to +90)
HORIZONTAL_FOV_DEG = 60.0  # Camera horizontal field of view
DEFAULT_FRAME_WIDTH = 640.0


def pan_cmd_to_deg(pan_cmd: int) -> float:
    """Convert servo command to physical angle (degrees).
    
    pan_cmd = 85 -> 0 degrees (vehicle front)
    pan_cmd = 170 -> +90 degrees (right)
    pan_cmd = 0 -> -90 degrees (left)
    """
    return (pan_cmd - PAN_CENTER) * (PHYSICAL_RANGE_HALF / PAN_RANGE_HALF)


class FollowState(Enum):
    FOLLOWING = "following"
    TURNING = "turning"
    WAITING = "waiting"
    SEARCHING = "searching"
    HEAD_ON_HOLD = "head_on_hold"
    HOLDING = "holding"
    APPROACHING_BLIND = "approaching_blind"
    LOST_TIMEOUT = "lost_timeout"


@dataclass
class FollowConfig:
    """Configuration for follow mode controller."""
    yaw_deadband: float = 5.0
    yaw_max: float = 45.0
    min_distance: float = 0.3
    max_distance: float = 2.0
    follow_distance: float = 0.4  # 目標距離0.4m（32.5-47.5cm帯の中心、distance_bandは維持）
    distance_band: float = 0.075    # ±距離帯幅（32.5-47.5cm実現）
    base_speed: int = 180
    turn_speed: int = 190  # 150だとパワー不足で動きが悪いことが実機で確認された
    control_rate_hz: float = 10.0
    min_confidence: float = 0.3
    turn_start_dist: float = 1.0
    stop_dist: float = 0.4
    turn_complete_yaw: float = 30.0
    follow_max_yaw: float = 60.0
    # Camera mounting offset relative to car chassis (degrees)
    # Positive = camera rotated right, Negative = camera rotated left
    camera_yaw_offset: float = 0.0
    min_pwm: int = 180
    blind_approach_pwm: int = 150
    head_on_threshold: float = 20.0
    state_hysteresis_frames: int = 3
    lost_timeout_sec: float = 5.0
    # FOLLOWING時の前進/後退PWM上限。実機で速すぎて衝突したため255から引き下げ、
    # 距離帯(32.5-47.5cm)に近づくほどmin_pwm(180)寄りまで減速する（下のapproach_slowdown_dist参照）
    max_follow_pwm: int = 200
    # この距離(m)だけ距離帯の外側にいると、まだmax_follow_pwmまで加速してよい。
    # 距離帯に近づくにつれて比例的にmin_pwmまで減速する
    approach_slowdown_dist: float = 1.0  # 0.5だと近距離(0.6-0.7m)でもPWM160台と速すぎたため拡大
    # API_DOCUMENTATION.md 2.2の GET /drive?v=&w= における旋回成分wの最大値
    # (Left_PWM=v+w, Right_PWM=v-w)。v(前進速度)を旋回で潰しすぎないよう、
    # max_follow_pwmより小さい値にする
    max_steering_w: int = 80
    # 実機のAPI仕様(API_DOCUMENTATION.md 2.1/2.6)によると、WSの"forward"/"backward"
    # (REST /forward)はESP32側のMPU-6050ジャイロ直進PID補正を経由するが、
    # 2.2のdrive:v,w(差動PWM直接指定)は経由しない(「subject to ultrasonic
    # auto-brake」としか明記されていない)。実機で「WASD操作(forward)は直進が
    # 安定するのに、follow modeのdrive:v,wは安定しない」と報告されたのはこのため。
    # ヘディング補正量|w|がこの閾値以下(=ほぼ直進でよい)のときはforward/backward+
    # speed:Nを使ってジャイロPIDの恩恵を受け、大きく操舵が必要なときのみ
    # drive:v,wの差動制御を使う。
    straight_command_w_threshold: int = 10
    # GimbalThreadが参照できない場合(テスト等)のパン中央値フォールバック。
    # GimbalThread._gimbal_center_pan(既定85.0)と揃えること
    gimbal_center_pan_deg: float = 85.0
    # ジンバルのpanがこの角度(度)以上、中央からずれている場合は、距離が離れて
    # いても接近より先に旋回してpanを正面へ戻すことを優先する
    pan_priority_threshold_deg: float = 15.0
    # 片輪のみの緩旋回はトルク不足で車体が動かないことが実機で確認されたため
    # 廃止し、両輪逆回転の超信地旋回に戻した。その代わり、パルス駆動
    # (on/offを繰り返す)で平均回転角速度を落とす。turn_speed(150)そのものは
    # 各パルスのON区間で使う(両輪ともmin_pwmを満たすのでトルクは足りる)。
    # 実機で「角度補正が連続して右左に旋回を繰り返す」振動が報告された:
    # 1回のON区間(0.15秒)でturn_speed(190)のまま回りすぎ、次の新しい検出が
    # 届く頃には反対側へ行き過ぎて逆方向の補正が入る、を繰り返していた。
    # ON時間を短縮し、1回あたりの回転量を減らして様子を見る。
    spin_pulse_on_sec: float = 0.08
    spin_pulse_off_sec: float = 0.2
    # pan角度優先補正(pan_offsetが大きい時)で、常時旋回し続けるのではなく
    # pan_priority_burst_sec秒だけ旋回してから、pan_priority_pause_sec秒
    # 完全停止して検出が安定するのを待ち、改めてpan_offsetを確認する
    # (実機で連続旋回が速すぎてカメラがブレ対象を見失ったと報告された)。
    #
    # バースト中は_spin_drive_commandを毎tick直接呼んで連続旋回する(高速
    # パルスとの二重間引きで固まる不具合の修正、下のコメント参照)ため、
    # 1バーストあたりの回転量は概算body_deg_per_sec_per_pwm×turn_speed×
    # pan_priority_burst_secになる。0.3秒のままだと0.5×190×0.3≈28.5°と
    # pan_priority_threshold_deg(15°)の約2倍にもなり、毎回オーバーシュート
    # して逆方向の補正が入る振動が実機ログで確認された。0.1秒(≈9.5°/バースト、
    # 閾値の半分程度)に短縮し、複数バーストにわけて滑らかに収束させる。
    pan_priority_burst_sec: float = 0.1
    pan_priority_pause_sec: float = 0.6
    # 推論精度が低いと、悪い距離/yaw推定のまま前進/後退し続けて対象を見失う
    # ことがあるため、直進駆動(FOLLOWING距離PID・APPROACHING_BLIND遠距離追従)
    # もpan角度優先補正と同じ「短いバースト走行→完全停止して検出が安定する
    # のを待つ」方式にする。値はpan_priority_burst_sec/pause_secと同じにして
    # ある(実車調整で見直してよい)。
    drive_burst_sec: float = 0.3
    drive_pause_sec: float = 0.6
    # 遠距離では実機で「動きが細切れで遅すぎる」と報告されたが、その後
    # 「連続前進のままだと向き・位置がずれていく」とも報告されたため、
    # 完全連続駆動ではなく、遠距離ではバースト時間を長く(drive_burst_far_sec)
    # して約1秒ごとに短く止めて追従状況を確認・補正する方式にする。
    # 近距離(この距離(m)以下)ではdrive_burst_secのまま(頻繁に確認)。
    # 停止時間(drive_pause_sec)は近距離・遠距離で共通。
    drive_pulse_near_dist_m: float = 1.0
    drive_burst_far_sec: float = 1.0
    # 旋回中、車体の回転によってカメラの絶対的な向きがどれだけズレるかを
    # 見越して、ジンバルのpanを先読みで補正する(フィードフォワード)。
    # body_deg_per_sec_per_pwm: PWM1あたり・1秒あたりの推定回転角度(度)。
    # 実機のギア比・車重に依存する未校正の初期値であり、実車で調整が必要。
    feedforward_enabled: bool = True
    body_deg_per_sec_per_pwm: float = 0.5
    # フィードフォワード補正の符号。ジンバルのパン正負とカメラ回転方向の
    # 対応が実機で未検証のため(gimbal-pose-compensation-design.md参照)、
    # 逆に補正されている場合はこれを-1に反転すること
    # 実機ログで、符号+1だと補正のたびにpan_offsetが拡大し(17°→55.8°)対象を
    # 見失うことが確認された(車体自体は正しい向きに回転できていたので、
    # ジンバル側の符号だけが逆だった)。-1に反転して中央へ寄せる方向にする
    feedforward_pan_sign: int = -1
    # FOLLOWING時の距離PID(ControlThread._compute_command参照)のゲイン。
    # UIのkp/ki/kdスライダー(views/sidebar.py)からここへ書き込まれる。
    kp_lin: float = 70.0
    ki_lin: float = 0.4
    kd_lin: float = 10.0


def wrap_angle(deg: float) -> float:
    """Normalize an angle in degrees to [-180, 180)."""
    return (deg + 180.0) % 360.0 - 180.0


def resolve_follow_state(
    yaw_deg,
    dist_m,
    bbox,
    config: FollowConfig,
) -> FollowState:
    """Single-frame state resolution (no hysteresis). Evaluated in priority order:
    head-on -> bbox visibility -> yaw/dist availability -> distance band."""
    if yaw_deg is not None:
        wrapped = wrap_angle(yaw_deg)
        if abs(wrapped) >= 180.0 - config.head_on_threshold:
            return FollowState.HEAD_ON_HOLD

    if bbox is None:
        return FollowState.SEARCHING

    if yaw_deg is None or dist_m is None:
        return FollowState.APPROACHING_BLIND

    lower = config.follow_distance - config.distance_band
    upper = config.follow_distance + config.distance_band
    if lower <= dist_m <= upper:
        return FollowState.HOLDING

    return FollowState.FOLLOWING


class StateHysteresis:
    """Confirms a state transition only after the same candidate state has
    been observed for `config.state_hysteresis_frames` consecutive updates.
    HEAD_ON_HOLD is safety-critical and bypasses hysteresis (confirmed immediately)."""

    def __init__(self, config: FollowConfig, initial_state: FollowState = FollowState.SEARCHING) -> None:
        self._config = config
        self._confirmed_state = initial_state
        self._pending_state = None
        self._pending_count = 0

    def update(self, candidate_state: FollowState) -> FollowState:
        if candidate_state == FollowState.HEAD_ON_HOLD:
            self._confirmed_state = FollowState.HEAD_ON_HOLD
            self._pending_state = None
            self._pending_count = 0
            return self._confirmed_state

        if candidate_state == self._pending_state:
            self._pending_count += 1
        else:
            self._pending_state = candidate_state
            self._pending_count = 1

        if self._pending_count >= self._config.state_hysteresis_frames:
            self._confirmed_state = candidate_state

        return self._confirmed_state


class DetectionThread(threading.Thread):
    def __init__(self, input_queue: Queue, output_queue: Queue, config: FollowConfig, log_callback=None):
        super().__init__(daemon=True)
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.config = config
        self._running = False
        self._log = log_callback
        self._count = 0

    def run(self):
        self._running = True
        if self._log:
            self._log("FOLLOW", "DetectionThread開始")
        while self._running:
            try:
                detection = self.input_queue.get(timeout=0.1)
                result = self._process_detection(detection)
                try:
                    self.output_queue.put_nowait(result)
                except:
                    pass
                self._count += 1
                if self._log and self._count % 10 == 0:
                    self._log("FOLLOW", f"[DetectionThread] 処理数: {self._count} qsize_in={self.input_queue.qsize()} qsize_out={self.output_queue.qsize()}")
            except:
                continue

    def _process_detection(self, detection: dict) -> dict:
        yaw_deg = detection.get("yaw_deg")
        dist_m = detection.get("dist_m")
        confidence = detection.get("confidence", 0.0)
        bbox = detection.get("bbox")
        frame_w = detection.get("frame_w", 640)
        frame_h = detection.get("frame_h", 480)
        
        valid = (yaw_deg is not None and dist_m is not None and 
                confidence >= self.config.min_confidence and
                self.config.min_distance <= dist_m <= self.config.max_distance)
        
        return {
            "valid": valid,
            "yaw_deg": yaw_deg,
            "dist_m": dist_m,
            "confidence": confidence,
            "bbox": bbox,
            "frame_w": frame_w,
            "frame_h": frame_h,
            "timestamp": time.time()
        }

    def stop(self):
        self._running = False


class GimbalThread(threading.Thread):
    """High-speed gimbal tracking thread (~20 Hz, independent of motor control).
    
    Based on ai_tracker_reference.py 2-Tier Visual Servoing:
    - Tapered gain controller (anti-oscillation)
    - Headroom safety margin (keep head at 15% from top)
    - Hip centering (hips at 55% of frame height)
    """
    def __init__(self, set_gimbal: Callable[[int, int], None], log_callback=None,
                 pan_min_deg: float = 0.0, pan_max_deg: float = 170.0,
                 tilt_min_deg: float = 40.0, tilt_max_deg: float = 130.0,
                 gimbal_center_pan_deg: float = 85.0,
                 calibration_tilt_deg: float = 70.0,
                 step_deg: float = 5.0, deadband: float = 0.15,
                 tilt_deadband: float = 0.5,
                 move_cooldown_sec: float = 1.0,
                 tracking_cooldown_sec: float = 0.2,
                 search_loop_sleep: float = 0.1,
                 track_loop_sleep: float = 0.02,
                 bearing_deadband: float = 6.0,
                 max_bearing_step: float = 20.0,
                 bbox_loss_grace_sec: float = 0.5,
                 search_step_deg: float = 10.0,
                 search_step_wait_sec: float = 0.6):
        super().__init__(daemon=True)
        self._set_gimbal = set_gimbal
        self._log = log_callback
        self._running = False
        self._frame_lock = threading.Lock()
        self._bbox = None
        self._frame_w = 640
        self._frame_h = 480
        self._bearing_deg = None

        # --- 離散ステップ制御のハードウェア可動域・パラメータ ---
        # チルト: 40-130度、パン: 0-170度（実機サーボの物理可動域。超えると故障の恐れがあるため
        # 必ずクランプすること）。170が左端、0が右端という可動域の話のみで、既存の
        # get_camera_yaw_offset() docstringにあるパン正負の意味づけは実装上矛盾があり
        # 実機検証が必要なため、本実装では符号の解釈には踏み込まない。
        self.pan_min_deg = pan_min_deg
        self.pan_max_deg = pan_max_deg
        self.tilt_min_deg = tilt_min_deg
        self.tilt_max_deg = tilt_max_deg
        # パンのキャリブレーション上のニュートラル位置。可動域(0-170)の中点である85.0を
        # デフォルトとしているが、これは実機で確認されていない仮定 —— 実機で要確認。
        self._gimbal_center_pan = gimbal_center_pan_deg
        # チルトのキャリブレーション角度（推論精度が最も良い角度）。既存の70.0を維持。
        self._calibration_tilt_deg = calibration_tilt_deg
        self.step_deg = step_deg
        self.deadband = deadband
        # チルト用のデッドバンドはパン(deadband)より広く取る。車体は画面下寄りに映る
        # ことが普通にあり、その程度の縦ズレでキャリブレーション角度(70度)から
        # 追従優先モードに切り替わってしまうと、車が静止していてもチルトが
        # 復帰・追従を繰り返して動き続けてしまう（実機で報告されたバグ）。
        # 画面上下端に近づく本当に見失いそうな場合のみ追従優先にするため、広めの値にする。
        self.tilt_deadband = tilt_deadband
        # move_cooldown_sec: 探索から見つかった直後の1回だけ使う「安定待ち」クールダウン
        # (推論が安定するのに1秒程度かかることを考慮)。それ以降、連続して追従できている
        # 間はtracking_cooldown_secという短いクールダウンで素早く反応する。
        self.move_cooldown_sec = move_cooldown_sec
        self.tracking_cooldown_sec = tracking_cooldown_sec
        # 探索中はループを詰めて回さなくてよい(推論フレームレート程度で十分)が、
        # 対象を追従中は素早く反応できるようループ間隔を短くする。
        self.search_loop_sleep = search_loop_sleep
        self.track_loop_sleep = track_loop_sleep
        # 探索は毎ループ(0.1秒ごと)1度ずつ細かく動かし続けていたため、実際には
        # 常に動いている最中の画像を推論しており、同じような狭い範囲を素早く
        # 往復するだけで新しい方向をちゃんと見る前に次へ動いてしまっていた
        # (実機で「同じようなところばかり見ている」と報告された)。search_step_deg
        # 単位で一気に動かし、その後search_step_wait_sec秒は角度を保持して
        # 推論結果が出揃うのを待ってから次の一歩を出す方式に変更する。
        self.search_step_deg = search_step_deg
        self.search_step_wait_sec = search_step_wait_sec
        self._search_next_step_time = 0.0
        # bearing_deg(atan2(X,Z)による実角度)ベースのパン制御用パラメータ
        self.bearing_deadband = bearing_deadband
        self.max_bearing_step = max_bearing_step
        # 単発の検知ミス(bbox=Noneが1フレームだけ)ではすぐに探索へ切り替えず、
        # この秒数だけ今の角度を保持して様子を見る（見逃し対策）
        self.bbox_loss_grace_sec = bbox_loss_grace_sec
        self._last_bbox_seen_time = 0.0
        # 最後に角度を動かした時刻（is_settled()の判定・クールダウン管理に使用）
        self._last_move_time = 0.0
        # 直前のtickで実際に角度を動かしたか。動かした直後は、サーボが物理的に
        # 追いつくまで長いクールダウン(move_cooldown_sec)を使い、動かしていない
        # (=既に中心付近で静止)場合のみ短いクールダウン(tracking_cooldown_sec)で
        # 素早く再評価する。これを区別しないと、サーボが前回の補正を完了する前に
        # 次の補正を出してしまい、実際のカメラ角度とcommand値がズレたまま補正が
        # 積み上がって振動が増幅していく現象が起きる（実機で報告されたバグ）。
        self._last_move_had_delta = False
        # 起動直後、まだ一度も推論結果(update_detection)が届いていない間は、
        # bboxがNoneでも「見失った」のではなく「まだ推論が始まっていないだけ」と
        # みなし、探索（スピン）を始めない。届いた時点でTrueになる。
        self._first_detection_received = False

        # Gimbal state（初期値はキャリブレーション位置に合わせる）
        self._current_pan = self._gimbal_center_pan
        self._current_tilt = self._calibration_tilt_deg
        # Reference parameters (from ai_tracker_reference.py) — 旧タパードゲイン制御用。
        # 離散ステップ制御に置き換わったため現在は未使用だが、他コード互換のため残す。
        self._pan_gain = 7.0
        self._tilt_gain = 5.5
        self._smooth_pan_step = 0.0
        self._smooth_tilt_step = 0.0
        self._max_step = 3.0
        # Tapered gain parameters (reference: TAPER_START=0.30, GAIN_FLOOR=0.35)
        self._taper_start = 0.30
        self._gain_floor = 0.35
        # Headroom safety: keep head at 15% from top
        self._headroom_target = 0.15
        # Search state
        self._search_state = "tracking"
        self._last_seen_side = "center"
        self._search_start_pan = 90.0
        self._search_timer = 0.0
        self._search_timeout = 3.0
        self._spin_speed = 1.5
        # Camera connection state
        self._camera_connected = False
        self._camera_stable_since = 0.0
        self._camera_stable_delay = 2.0

    def update_detection(self, bbox, frame_w: int, frame_h: int, bearing_deg: float | None = None):
        """Update detection data (thread-safe, called from main thread)。

        bearing_deg: rccar_pose_inference.DetectionResult.bearing_deg。カメラ視点の
        atan2(X, Z)による正確な角度誤差(度)。Noneなら_track_target側が従来の
        ピクセル比率ベースのデッドバンド+固定ステップにフォールバックする。
        """
        with self._frame_lock:
            self._bbox = bbox
            self._frame_w = frame_w
            self._frame_h = frame_h
            self._bearing_deg = bearing_deg
            # bboxがNoneの結果でも、推論パイプライン自体は実際に動いて結果を
            # 返してきているので「起動直後でまだ何も来ていない」状態とは区別する
            self._first_detection_received = True

    def on_camera_connected(self):
        """Called when camera stream connects."""
        self._camera_connected = True
        self._camera_stable_since = time.time()
        if self._log:
            self._log("FOLLOW", "[Gimbal] Camera connected - waiting for stabilization")

    def on_camera_disconnected(self):
        """Called when camera stream disconnects."""
        self._camera_connected = False
        self._search_state = "tracking"
        self._smooth_pan_step = 0.0
        self._smooth_tilt_step = 0.0
        self._first_detection_received = False
        self._last_bbox_seen_time = 0.0
        if self._log:
            self._log("FOLLOW", "[Gimbal] カメラ切断 - 停止")

    def _within_bbox_loss_grace(self, now: float) -> bool:
        """直近でbboxが見えていた時刻からbbox_loss_grace_sec以内かどうか。
        Trueの間は、単発の検知ミスとみなしてスピン探索を始めない。"""
        return now - self._last_bbox_seen_time < self.bbox_loss_grace_sec

    def get_camera_yaw_offset(self) -> float:
        """Get camera yaw offset based on current gimbal pan angle.
        
        Returns offset in degrees:
        - Positive: camera rotated right from center
        - Negative: camera rotated left from center
        - 0: camera facing forward (gimbal at center)
        """
        return self._current_pan - self._gimbal_center_pan

    def apply_feedforward_pan_delta(self, delta_deg: float) -> None:
        """車体が旋回している間、ビジョンフィードバック(bearing_deg)を待たずに
        パンを先読みで補正する。ControlThread側が「これから車体をこれだけ
        回転させる」という計算結果から呼び出す。通常の_track_target()による
        追従（クールダウン・デッドバンド管理）とは別経路で、即座に反映する。"""
        with self._frame_lock:
            new_pan = max(self.pan_min_deg, min(self.pan_max_deg, self._current_pan + delta_deg))
            self._current_pan = new_pan
        self._send_gimbal()

    def _send_gimbal(self) -> None:
        """実機で「探索中にサーボが逆方向へ動く」ことが確認された: このクラスの
        追従・探索ロジック全体(_track_target/_search_target/get_camera_yaw_offset/
        PoseInference._apply_gimbal_compensation)は「pan値が大きいほどカメラが
        左を向く」という一貫した内部モデルの上に組まれており、それ自体は自己
        整合的だが、実際のサーボの向きはこれと逆だった。ロジック側を全箇所
        直すのではなく、サーボへ実際に送る値だけを中心角(_gimbal_center_pan)
        周りで鏡像反転させ、このメソッド1箇所に閉じ込める
        (_current_panは内部モデルのままなので追従計算・探索方向判定・
        get_camera_yaw_offset()・gimbal_provider経由のPoseInference補正は
        一切変更不要)。"""
        if not self._set_gimbal:
            return
        physical_pan = 2 * self._gimbal_center_pan - self._current_pan
        physical_pan = max(self.pan_min_deg, min(self.pan_max_deg, physical_pan))
        self._set_gimbal(int(physical_pan), int(self._current_tilt))

    def run(self):
        self._running = True
        if self._log:
            self._log("FOLLOW", "GimbalThread開始 (~20Hz)")
        while self._running:
            try:
                if not self._camera_connected:
                    time.sleep(0.1)
                    continue
                
                elapsed_since_connect = time.time() - self._camera_stable_since
                if elapsed_since_connect < self._camera_stable_delay:
                    time.sleep(0.1)
                    continue

                with self._frame_lock:
                    bbox = self._bbox
                    frame_w = self._frame_w
                    frame_h = self._frame_h
                    bearing_deg = self._bearing_deg
                    first_detection_received = self._first_detection_received

                if not first_detection_received:
                    # 起動直後、推論がまだ一度も結果を返していない間は探索(スピン)を
                    # 始めない。最初の推論結果を待つ。
                    time.sleep(0.1)
                    continue

                now = time.time()
                if bbox is not None:
                    self._last_bbox_seen_time = now
                    self._track_target(bbox, frame_w, frame_h, bearing_deg)
                    time.sleep(self.track_loop_sleep)  # 対象追従中は素早く反応
                elif self._within_bbox_loss_grace(now):
                    # 単発の検知ミス(1フレームだけbbox=None)で即座にスピン探索へ
                    # 移ってしまうと、実際にはまだ画面内にいる対象からジンバルが
                    # 離れていき、本当に見失ってしまう（実機で「せっかく検知した
                    # のに見逃す」として報告された悪循環）。短い猶予期間は今の
                    # 角度を保持し、対象が本当にいなくなったかを見極める。
                    time.sleep(self.track_loop_sleep)
                else:
                    self._search_target()
                    time.sleep(self.search_loop_sleep)  # 探索中は推論フレームレート程度で十分
            except Exception as e:
                if self._log:
                    self._log("FOLLOW", f"[Gimbal] エラー: {e}")
                time.sleep(0.05)

    def _compute_discrete_step(self, error: float, deadband: float, step_deg: float) -> float:
        """誤差がデッドバンド内なら0、そうでなければ誤差を減らす方向の±step_degを返す。
        パン・チルト両方で共通利用するシンプルな離散ステップ関数。"""
        if abs(error) < deadband:
            return 0.0
        return step_deg if error > 0 else -step_deg

    def _compute_bearing_pan_delta(self, bearing_deg: float) -> float:
        """distとXから三平方の定理(atan2)で計算された実角度(bearing_deg)を使い、
        固定5度ステップではなく必要な分だけ正確にパンを動かす。角度誤差が小さい
        (bearing_deadband未満)なら動かさず、外れ値対策として1回の移動量は
        max_bearing_stepでクランプする。"""
        if abs(bearing_deg) < self.bearing_deadband:
            return 0.0
        return max(-self.max_bearing_step, min(self.max_bearing_step, bearing_deg))

    def is_settled(self) -> bool:
        """最後に角度を動かしてからtracking_cooldown_sec以上経過していればTrue。

        以前は常に長い方のmove_cooldown_sec(既定1秒、探索から見つかった直後の
        安定待ち専用)を基準にしていたため、追従中の短いクールダウン
        (tracking_cooldown_sec、既定0.2秒)で微補正が入るたびに、その後1秒間ずっと
        「未安定」判定になっていた。これによりシャシーが「ジンバル安定待ち」で
        ほとんど動けず、距離が離れていても近づかない問題が実機で報告された。
        「今まさに補正動作中か」を見るための閾値なので、追従中の短いクールダウンを
        基準にする方が実態に合っている。"""
        return (time.time() - self._last_move_time) >= self.tracking_cooldown_sec

    def get_pan_tilt_state(self) -> tuple:
        """PoseInference(rccar_pose_inference)のgimbal_providerとして渡すための状態取得。

        (pan_deg, tilt_deg, is_settled) を返す。pan/tiltはサーボへのコマンド値であり
        実角度フィードバックではない（is_settled()と同じくクールダウンベースの近似）。
        """
        return (self._current_pan, self._current_tilt, self.is_settled())

    def _track_target(self, bbox, frame_w: int, frame_h: int, bearing_deg: float | None = None):
        """パン/チルトを対象に追従させる。

        - パン: bearing_deg（rccar_pose_inferenceがatan2(X, Z)で計算した実角度）が
          あればその角度分だけ正確に動かす。固定5度ステップでは実際に必要な角度と
          ズレて中心付近で行ったり来たり振動していたため、これで解消する
          （bearing_degがNone、つまりGround.pose()が届かない遠距離では、従来の
          ピクセル比率ベースのデッドバンド+固定ステップにフォールバックする）
        - チルト: 対象がデッドバンド内(画面中心付近)ならキャリブレーション角度(70度)へ
          5度ステップで復帰。デッドバンドを超えていれば見失い防止のため追従方向へ
          5度ステップで動かす（bearing_degには垂直成分がないためチルトは従来通り）
        - 推論の安定化のため、一度角度を動かしたらクールダウン秒は次の変更を発行しない
        """
        bx, by, bw, bh = bbox
        cx = bx + bw / 2.0
        cy = by + bh / 2.0

        # Reset search state when target is found. 探索から見つかった直後の
        # 1回だけ、推論が安定するのを待つ長めのクールダウン(move_cooldown_sec)を
        # 使う。それ以降、連続して追従できている間は短いクールダウン
        # (tracking_cooldown_sec)で素早く反応する。
        just_reacquired = self._search_state != "tracking"
        if just_reacquired:
            self._search_state = "tracking"

        # Remember which side the target is on (used by _search_target fallback)
        if cx < frame_w * 0.4:
            self._last_seen_side = "left"
        elif cx > frame_w * 0.6:
            self._last_seen_side = "right"
        else:
            self._last_seen_side = "center"

        now = time.time()
        # 直前に実際に角度を動かした場合は、サーボが物理的に追いつくまで長い
        # クールダウンを使う。既に中心付近で止まっている場合のみ短いクールダウンで
        # 素早く再評価してよい。
        effective_cooldown = (self.move_cooldown_sec
                               if (just_reacquired or self._last_move_had_delta)
                               else self.tracking_cooldown_sec)
        if now - self._last_move_time < effective_cooldown:
            # クールダウン中: 角度変更を保留し、今の角度を保持する
            return

        # 正規化誤差 (bbox中心 vs 画面中心)
        error_x = (cx - frame_w / 2.0) / (frame_w / 2.0)
        error_y = (cy - frame_h / 2.0) / (frame_h / 2.0)

        # --- パン: bearing_degがあれば実角度で正確に、なければ従来のピクセル固定ステップ ---
        # 符号は実機で確認済み: ローバーから見て左に対象を置くと、以前は
        # (self._current_pan - pan_delta)でカメラが右へ動いてしまっていた
        # (逆方向)。+pan_deltaに反転して正しい方向へ追従するようにする。
        if bearing_deg is not None:
            pan_delta = self._compute_bearing_pan_delta(bearing_deg)
        else:
            pan_delta = self._compute_discrete_step(error_x, self.deadband, self.step_deg)
        new_pan = self._current_pan + pan_delta
        new_pan = max(self.pan_min_deg, min(self.pan_max_deg, new_pan))

        # --- チルト: デッドバンド内ならキャリブレーション角度へ復帰、外れていれば追従優先 ---
        # (パンより広いtilt_deadbandを使う。車体が画面下寄りに映る程度の通常の縦ズレでは
        # 追従優先モードに入らず、70度付近を維持する)
        if abs(error_y) < self.tilt_deadband:
            tilt_diff = self._calibration_tilt_deg - self._current_tilt
            if abs(tilt_diff) < 1e-9:
                new_tilt = self._current_tilt
            else:
                tilt_step = self.step_deg if tilt_diff > 0 else -self.step_deg
                if abs(tilt_step) > abs(tilt_diff):
                    tilt_step = tilt_diff
                new_tilt = self._current_tilt + tilt_step
        else:
            tilt_delta = self._compute_discrete_step(error_y, self.tilt_deadband, self.step_deg)
            new_tilt = self._current_tilt + tilt_delta
        new_tilt = max(self.tilt_min_deg, min(self.tilt_max_deg, new_tilt))

        moved = (new_pan != self._current_pan) or (new_tilt != self._current_tilt)
        self._current_pan = new_pan
        self._current_tilt = new_tilt
        self._last_move_had_delta = moved

        if moved:
            self._last_move_time = now
            self._send_gimbal()

    def _search_target(self):
        """Search for target when lost.

        Moves in search_step_deg(既定10度)刻みの離散ジャンプにして、動かした
        直後はsearch_step_wait_sec(既定0.6秒)だけ角度を保持する。以前は毎ループ
        (0.1秒ごと)1度ずつ動かし続けており、常に動いている最中のフレームで
        推論していたため実質的に新しい方向をちゃんと見る前に次へ動いてしまい、
        結果として同じ狭い範囲を素早く往復するだけになっていた(実機で「同じ
        ようなところばかり見ている」と報告された)。
        """
        now = time.time()

        if self._search_state == "tracking":
            # Target just lost: start searching in the last seen direction
            self._search_state = "search_direction"
            self._search_start_pan = self._current_pan
            self._search_timer = now
            self._search_next_step_time = 0.0
            if self._log:
                self._log("FOLLOW", f"[Gimbal] 車をlost → {self._last_seen_side}方向を探索")

        if self._search_state == "search_direction":
            if now < self._search_next_step_time:
                return
            # Search in the direction where target was last seen
            elapsed = now - self._search_timer

            if self._last_seen_side == "right":
                pan_step = -self.search_step_deg
            elif self._last_seen_side == "left":
                pan_step = self.search_step_deg
            else:
                # Center: search right first
                pan_step = -self.search_step_deg

            self._current_pan = max(self.pan_min_deg, min(self.pan_max_deg, self._current_pan + pan_step))

            self._send_gimbal()
            self._search_next_step_time = now + self.search_step_wait_sec

            # If search timeout or hit servo limit, switch to spin search
            if (elapsed > self._search_timeout
                    or self._current_pan <= self.pan_min_deg + 5
                    or self._current_pan >= self.pan_max_deg - 5):
                self._search_state = "search_spin"
                self._search_timer = now
                self._search_next_step_time = 0.0
                if self._log:
                    self._log("FOLLOW", "[Gimbal] 方向探索失敗 → ぐるぐる探索")

        if self._search_state == "search_spin":
            if now < self._search_next_step_time:
                return
            # Sweep the FULL pan range end-to-end, reversing only at the
            # physical limits (pan_min_deg/pan_max_deg). Previously this
            # bounced back and forth inside a fixed 60-degree window around
            # wherever search_direction happened to stop, so most of the
            # pan range was never actually scanned - reported on hardware
            # as "the search keeps looking at the same places".
            pan_step = self.search_step_deg if self._spin_speed > 0 else -self.search_step_deg
            self._current_pan = max(self.pan_min_deg, min(self.pan_max_deg, self._current_pan + pan_step))

            self._send_gimbal()
            self._search_next_step_time = now + self.search_step_wait_sec

            if self._current_pan <= self.pan_min_deg or self._current_pan >= self.pan_max_deg:
                self._spin_speed = -self._spin_speed

    def stop(self):
        self._running = False


class ControlThread(threading.Thread):
    """ControlThread implementing reference architecture algorithm.
    
    Based on ai_tracker_reference.py 2-Tier Visual Servoing:
    - Tier 1: Gimbal visual servoing (handled by GimbalThread)
    - Tier 2: Linear PID distance + Combined heading error steering
    
    Key differences from standard approach:
    - Linear PID for distance (KP=70, KI=0.4, KD=10)
    - Combined heading: 0.15 * error_x + 0.85 * pan_error
    - Rate limiting (MAX_V_STEP = 60)
    - Occlusion guard (DIST_JUMP_LIMIT_M = 0.6)
    - Distance golden band (±0.15m → stop & hold)
    - Turn-only heading error gate (0.35)
    """
    def __init__(self, input_queue: Queue, output_queue: Queue, config: FollowConfig, log_callback=None):
        super().__init__(daemon=True)
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.config = config
        self._running = False
        self._log = log_callback
        self._count = 0
        self._hysteresis = StateHysteresis(config, initial_state=FollowState.SEARCHING)
        self.state = FollowState.SEARCHING
        self.target_distance = config.follow_distance
        self._filtered_yaw = 0.0
        self._yaw_filter_alpha = 0.3
        # Chassis follow flag (set by FollowController)
        self.chassis_follow_enabled = False
        # Reference to GimbalThread for automatic camera offset
        self._gimbal_thread = None

        # Reference algorithm parameters: config.kp_lin/ki_lin/kd_lin
        # (UIのkp/ki/kdスライダーから設定可能。follow mode実行中の変更を
        # 反映するため、_compute_command()内でその都度self.configから読む。
        # 以前はここにハードコードされておりconfigの値を無視していた)
        self._err_lin_i = 0.0  # Integral accumulator
        self._prev_err_lin = 0.0
        self._prev_dist_m = None
        self._last_cmd_t = 0.0

        # Rate limiting
        self._max_v_step = 60
        self._prev_v_cmd = 0

        # Occlusion guard
        self._dist_jump_limit = 0.6
        self._searching_since = None

        # パン角度優先補正(pan_offsetが大きい時の旋回)用の状態。turn_speed
        # (既定190)自体は150未満に下げるとトルク不足で車体が動かなくなる
        # ため下げられない。代わりに、常時パルス駆動し続けるのではなく
        # 「短いバースト旋回→完全停止して検出が安定するのを待つ→pan_offset
        # を確認して必要なら次のバースト」という段階的な方式にする(実機で
        # 旋回が速すぎてカメラがブレ対象を見失ったと報告されたため)。
        self._pan_priority_burst_start = None
        self._pan_priority_pause_until = 0.0

        # 直進駆動(前進/後退)のバースト→停止確認用の状態(pan優先旋回と同型)。
        self._drive_burst_start = None
        self._drive_pause_until = 0.0

    def run(self):
        self._running = True
        if self._log:
            self._log("FOLLOW", "ControlThread開始 (参照アーキテクチャ)")
        while self._running:
            try:
                detection = self.input_queue.get(timeout=0.1)
                command = self._compute_command(detection)
                if command is None:
                    # レートリミット中(12.5Hz超過)は_compute_command()がNoneを
                    # 返す。以前はここでNoneをそのままキューに積んでおり、
                    # CommandThread側で command_data.get(...) がAttributeErrorに
                    # なって(bare exceptで)握りつぶされていた（デバッグログが
                    # 一部欠落していた原因）。Noneは積まずスキップする。
                    continue
                # _compute_command()の各分岐はchassis_enabledを含めないため、
                # ここで注入する。含めないとCommandThread側でデフォルトのFalse
                # 扱いになり、'v'キーでchassis_follow_enabledを有効にしても
                # モータコマンドが一切送信されない（既知バグ、ここで修正）。
                command["chassis_enabled"] = self.chassis_follow_enabled
                try:
                    self.output_queue.put_nowait(command)
                except:
                    pass
                self._count += 1
                if self._log and self._count % 10 == 0:
                    self._log("FOLLOW", f"[ControlThread] 処理数: {self._count}")
            except queue.Empty:
                continue
            except Exception as e:
                if self._log:
                    self._log("FOLLOW", f"[ControlThread] エラー: {type(e).__name__}: {e}")
                continue

    def _compute_command(self, detection: dict):
        """Compute motor command using the distance-band state machine."""
        yaw_deg = detection.get("yaw_deg")
        dist_m = detection.get("dist_m")
        dist_m_predicted = detection.get("dist_m_predicted")
        bbox = detection.get("bbox")
        confidence = detection.get("confidence", 0.0)
        frame_w = detection.get("frame_w", DEFAULT_FRAME_WIDTH)

        # Body-relative target angle (vehicle front = 0 degrees)
        # pan_deg: gimbal servo angle in physical degrees
        if self._gimbal_thread:
            current_pan_cmd = self._gimbal_thread._current_pan
        else:
            current_pan_cmd = PAN_CENTER
        pan_deg = pan_cmd_to_deg(current_pan_cmd)

        # cam_yaw_deg: target offset from camera center
        if bbox:
            bx, by, bw, bh = bbox
            bbox_x_center = bx + bw / 2
            cam_yaw_deg = ((bbox_x_center - (frame_w / 2.0)) / frame_w) * HORIZONTAL_FOV_DEG
        else:
            cam_yaw_deg = 0.0

        # body_target_angle: combined angle from vehicle front
        body_target_angle = pan_deg + cam_yaw_deg

        # Use body_target_angle for state resolution and heading control
        yaw_deg_offset = body_target_angle

        candidate_state = resolve_follow_state(yaw_deg_offset, dist_m, bbox, self.config)
        self.state = self._hysteresis.update(candidate_state)

        # Rate limit control ticks (12.5 Hz max)
        now = time.time()
        dt = max(0.02, now - self._last_cmd_t)
        if dt < 0.080:
            return None
        self._last_cmd_t = now

        if self.state == FollowState.HEAD_ON_HOLD:
            self._reset_drive_pulse()
            return self._handle_head_on(yaw_deg_offset, dist_m)

        if self.state == FollowState.SEARCHING:
            self._reset_drive_pulse()
            self._searching_since = self._searching_since or now
            if now - self._searching_since >= self.config.lost_timeout_sec:
                self.state = FollowState.LOST_TIMEOUT
                return self._stop_command("ロストタイムアウト")
            return self._stop_command("探索中(bbox未検出)")

        if self.state == FollowState.LOST_TIMEOUT:
            self._reset_drive_pulse()
            return self._stop_command("ロストタイムアウト")

        self._searching_since = None

        if self.state == FollowState.APPROACHING_BLIND:
            return self._handle_approaching_blind(bbox, detection.get("frame_w", 640))

        if self.state == FollowState.HOLDING:
            self._err_lin_i = 0.0
            self._prev_err_lin = 0.0
            self._prev_v_cmd = 0
            self._reset_drive_pulse()
            return self._stop_command("ホールド(32.5-47.5cm帯)")

        if confidence < self.config.min_confidence:
            self._reset_drive_pulse()
            return self._stop_command(f"信頼度不足({confidence:.2f})")

        # ジンバルが対象を追って補正中(is_settled()==False)はシャシーを減速して待つ。
        # 推論(~10Hz)が追いつく前にジンバルとシャシーが同時に動くと、互いの動きが
        # 干渉して近距離での振動につながっていたため、ジンバルが安定してから
        # そのpan偏差・距離で改めてdrive:v,wを計算する段階的な制御にする。
        # ただし_prev_v_cmdを即座に0にリセットすると、直前まで加速中だった場合に
        # 急停止→次tickでまた0から再加速、というカクカクした動きになっていた
        # (実機で「旋回が安定しない」として報告)。_ramp_speed_signed(0)で
        # _max_v_step刻みに滑らかに減速させ、再開時も自然に繋がるようにする。
        if self._gimbal_thread and not self._gimbal_thread.is_settled():
            v = self._ramp_speed_signed(0)
            return {
                "type": "control",
                "command": f"drive:{v},0",
                "speed": abs(v),
                "log": f"ジンバル安定待ち(is_settled=False)のため減速: drive:{v},0",
            }

        # FOLLOWING: 距離PID + ヘディング項ブレンドによる連続速度制御。
        # (Stanleyの数式は使っていない。真のStanleyControllerはapp2/にのみ存在)
        if self._prev_dist_m is not None and abs(dist_m - self._prev_dist_m) > self._dist_jump_limit:
            dist_m = self._prev_dist_m
            # 生のdist_mが外れ値だった場合、そこから計算された予測距離も
            # 信用しない(直前の正常値ベースの現在距離にフォールバック)
            dist_m_predicted = None
        else:
            self._prev_dist_m = dist_m

        # Phase 6(未来位置予測): 距離PIDの入力には、速度ベースでprediction_time_sec
        # 先まで投影した予測距離(あれば)を使い、急な接近/離脱への追従遅れを減らす。
        # ただしSEARCHING等の状態遷移判定・安全停止判定(resolve_follow_state)は
        # 引き続き実測のdist_mのみを使う(予測値を安全判定に使わない)
        dist_m_for_pid = dist_m_predicted if dist_m_predicted is not None else dist_m
        err_lin = dist_m_for_pid - self.target_distance
        self._err_lin_i += err_lin * dt
        self._err_lin_i = max(-3.0, min(3.0, self._err_lin_i))  # anti-windup
        d_err_lin = (err_lin - self._prev_err_lin) / dt
        self._prev_err_lin = err_lin
        # config.kp_lin/ki_lin/kd_linはUIスライダーからfollow mode実行中でも
        # 更新される(views/sidebar.py _on_follow_param_change)ため、self.config
        # から都度読む(self._kp_lin等は__init__時点のスナップショットで固定)
        lin_v = (self.config.kp_lin * err_lin + self.config.ki_lin * self._err_lin_i
                 + self.config.kd_lin * d_err_lin)

        # Unified heading error using body_target_angle (vehicle front = 0 degrees)
        combined_heading_error = yaw_deg_offset / self.config.yaw_max

        # API_DOCUMENTATION.md 2.2: GET /drive?v=&w= (Left_PWM=v+w, Right_PWM=v-w)。
        # w: 負=左旋回、正=右旋回。combined_heading_error>0は「左に曲がる必要がある」
        # の意味なので、w = -combined_heading_error * max_steering_w とする。
        w = int(max(-self.config.max_steering_w,
                     min(self.config.max_steering_w, -combined_heading_error * self.config.max_steering_w)))

        # ジンバルのpanが車体正面から大きくずれている場合(=車体自体は対象の方を
        # 向いていない)は、距離が離れていても接近より先に旋回してpan角度を
        # 正面(pan_center)へ戻すことを優先する。
        pan_offset_deg = abs(body_target_angle)
        if pan_offset_deg > self.config.pan_priority_threshold_deg:
            self._prev_v_cmd = 0
            self._reset_drive_pulse()  # 旋回優先中は直進駆動のバースト/停止確認を持ち越さない
            now = time.time()

            if now < self._pan_priority_pause_until:
                # バースト後の静止確認中: 完全停止してカメラのブレが収まり
                # 検出が安定するのを待つ(この間もpan_offsetは毎フレーム
                # 再評価されるので、対象を見失っていれば別の分岐に移る)
                return {
                    "type": "control",
                    "command": "drive:0,0",
                    "speed": 0,
                    "log": f"pan角度優先補正: 静止確認中 pan_offset={pan_offset_deg:.1f}°",
                }

            if self._pan_priority_burst_start is None:
                self._pan_priority_burst_start = now
            elif now - self._pan_priority_burst_start >= self.config.pan_priority_burst_sec:
                # バースト時間経過: 次は停止して確認する番。
                # ここでpause_untilを更新するだけでは、このtick自体はまだ
                # 下のpulsed_spin_commandに進んでしまい、パルス位相がたまたま
                # ON区間と重なると旋回コマンドが漏れてしまう(spin_pulse_on_sec
                # を0.15→0.08に短縮した際に表面化した回帰: 位相の偶然一致に
                # 依存していた)。バースト終了はこのtickから即座に完全停止とする。
                self._pan_priority_pause_until = now + self.config.pan_priority_pause_sec
                self._pan_priority_burst_start = None
                return {
                    "type": "control",
                    "command": "drive:0,0",
                    "speed": 0,
                    "log": f"pan角度優先補正: 静止確認中 pan_offset={pan_offset_deg:.1f}°",
                }

            spin_w = self.config.turn_speed if combined_heading_error <= 0 else -self.config.turn_speed
            # ここは_pulsed_spin_commandの高速on/offパルスを使わず、バースト窓
            # (pan_priority_burst_sec)の間は毎tick連続で旋回する。バースト→
            # 完全停止のマクロな繰り返し自体が速度を抑える役割を果たしている
            # ため、その内側でさらに高速パルス(spin_pulse_on/off_sec)を重ねると、
            # 両者の周期がたまたま噛み合わない場合にバースト窓内で一度もON区間が
            # 来ず、pan_offsetが何秒も補正されず固まることが実機ログで確認された
            # (実車で「対象が視野端に流れていくのに補正されない」として報告)。
            command = self._spin_drive_command(spin_w)
            return {
                "type": "control",
                "command": command,
                "speed": self.config.turn_speed,
                "log": f"pan角度優先補正: pan_offset={pan_offset_deg:.1f}° {command}",
            }

        # pan角度優先補正の対象外になった(pan_offsetが閾値以下に収まった) ->
        # 次に大きくずれた時のために、バースト/停止確認の状態をリセットする
        self._pan_priority_burst_start = None
        self._pan_priority_pause_until = 0.0

        TURN_ONLY_HEADING_ERROR = 0.35
        if abs(combined_heading_error) > TURN_ONLY_HEADING_ERROR:
            # 見失いそうなほど旋回が必要 -> 両輪逆回転の超信地旋回(v=0)。
            # 片輪駆動はトルク不足で車体が動かないことが実機で確認されたため、
            # 両輪駆動に戻し、代わりにパルス駆動(on/off)で平均回転角速度を抑える
            self._prev_v_cmd = 0
            self._reset_drive_pulse()
            spin_w = self.config.turn_speed if combined_heading_error <= 0 else -self.config.turn_speed
            command = self._pulsed_spin_command(spin_w)
        elif err_lin > self.config.distance_band:
            v = self._ramp_speed_signed(self._distance_proportional_pwm(err_lin))
            burst_sec = self.config.drive_burst_sec if dist_m <= self.config.drive_pulse_near_dist_m else self.config.drive_burst_far_sec
            command = self._pulsed_drive_command(v, w, burst_sec=burst_sec)
        elif err_lin < -self.config.distance_band:
            v = self._ramp_speed_signed(-self._distance_proportional_pwm(abs(err_lin)))
            burst_sec = self.config.drive_burst_sec if dist_m <= self.config.drive_pulse_near_dist_m else self.config.drive_burst_far_sec
            command = self._pulsed_drive_command(v, w, burst_sec=burst_sec)
        else:
            # 距離帯には収まっているが向きの補正が必要 -> その場で軽く旋回
            self._prev_v_cmd = 0
            self._reset_drive_pulse()
            spin_w = self.config.turn_speed if combined_heading_error <= 0 else -self.config.turn_speed
            command = self._pulsed_spin_command(spin_w)

        return {
            "type": "control",
            "command": command,
            "speed": abs(self._prev_v_cmd),
            "log": f"heading:{combined_heading_error:+.2f} dist:{err_lin:+.2f}m {command}",
        }

    def _reset_drive_pulse(self) -> None:
        """直進駆動(前進/後退)のバースト→停止確認の状態をリセットする。
        駆動以外の分岐(旋回・停止系の状態)に移った時に呼び、次に直進駆動へ
        戻った際は必ず新しいバーストから始まるようにする。"""
        self._drive_burst_start = None
        self._drive_pause_until = 0.0

    def _pulsed_drive_command(self, v: int, w: int, burst_sec: float | None = None) -> str:
        """前進/後退の直進駆動を「短いバースト走行→完全停止して検出が安定
        するのを待つ(既定drive_pause_sec=0.6秒)」の繰り返しにする。推論精度が
        低い状況で連続走行すると、悪い距離/yaw推定のまま走り続けて対象を
        見失ったり、車体の向き・位置が少しずつずれていくことがあるため、
        pan角度優先補正(_pan_priority_burst_start等)と同じ考え方を直進駆動
        にも適用する。

        burst_sec省略時はconfig.drive_burst_sec(既定0.3秒、近距離用)を使う。
        遠距離(config.drive_pulse_near_dist_mより遠い)では、実機で「頻繁に
        止まると細切れ過ぎて遅い」と報告される一方、「連続前進のままだと
        ずれていく」とも報告されたため、呼び出し側がconfig.drive_burst_far_sec
        (既定1.0秒)を渡し、バースト自体は続けつつ間隔を長くする。

        停止(バースト終了・静止確認中)の間はself._prev_v_cmdも0にリセットし、
        バースト再開時に0から滑らかにランプアップし直す(急発進を避ける)。"""
        effective_burst_sec = self.config.drive_burst_sec if burst_sec is None else burst_sec
        now = time.time()
        if now < self._drive_pause_until:
            self._prev_v_cmd = 0
            return "drive:0,0"

        if self._drive_burst_start is None:
            self._drive_burst_start = now
        elif now - self._drive_burst_start >= effective_burst_sec:
            self._drive_pause_until = now + self.config.drive_pause_sec
            self._drive_burst_start = None
            self._prev_v_cmd = 0
            return "drive:0,0"

        return self._forward_or_drive_command(v, w)

    def _spin_drive_command(self, spin_w: int) -> str:
        """両輪逆回転の超信地旋回(v=0, w=spin_w)の駆動コマンドを1つ返す
        (呼び出された分だけ実際に旋回する連続旋回)。旋回によって生じる
        カメラ絶対方向のズレをジンバルのフィードフォワード補正で打ち消す
        よう、GimbalThreadにも同時にパン移動を指示する(feedforward_enabled時)。

        速度を抑えたい場合は、呼び出し側でon/off間引き(_pulsed_spin_command)
        やバースト→停止のマクロな繰り返し(pan角度優先補正)を行うこと。
        両方を同時に重ねると、周期の噛み合わせによってはON区間が長時間
        一度も来ず旋回が完全に固まることが実機ログで確認された(pan角度優先
        補正では1つのバースト窓の中で本メソッドを毎tick直接呼ぶことで、
        この二重間引きを避けている)。"""
        # chassis_follow_enabledがFalse('v'キー未押下)のときは、この旋回コマンドは
        # CommandThread側で実際にはESP32へ送信されない(計算のみ)。にもかかわらず
        # フィードフォワードだけジンバルに適用すると、実際には動いていない車体の
        # 回転を前提にジンバルが一方的にpanをずらし続け、対象を見失う原因になる
        # (実機で「検出したのに勝手に動いていく」として報告されたバグ)。
        if self.config.feedforward_enabled and self._gimbal_thread and self.chassis_follow_enabled:
            # このON区間で車体が回転するであろう角度を見積もり、ジンバルの
            # パンを先読みで補正する。符号(feedforward_pan_sign)は実機で
            # 未検証のため、逆に補正される場合は設定で反転すること。
            dt_on = min(0.08, self.config.spin_pulse_on_sec)  # 制御ループの最小間隔(12.5Hz)相当
            estimated_body_rotation_deg = self.config.body_deg_per_sec_per_pwm * abs(spin_w) * dt_on
            direction_sign = 1 if spin_w > 0 else -1
            delta = self.config.feedforward_pan_sign * direction_sign * estimated_body_rotation_deg
            self._gimbal_thread.apply_feedforward_pan_delta(delta)
            if self._log:
                self._log("FOLLOW", f"[FF] 旋回フィードフォワード: spin_w={spin_w} delta_pan={delta:+.2f}°")

        return f"drive:0,{spin_w}"

    def _pulsed_spin_command(self, spin_w: int) -> str:
        """両輪逆回転の超信地旋回(v=0, w=spin_w)を、on/offのパルス駆動にして
        平均回転角速度を落とす。片輪のみ駆動する緩旋回はトルク不足で車体が
        動かないことが実機で確認されたため、両輪駆動(turn_speed、min_pwmを
        満たすのでトルクは足りる)に戻し、代わりに時間軸でON/OFFを繰り返す
        ことで実効的な旋回速度を抑える。

        壁時計時刻を`spin_pulse_on_sec + spin_pulse_off_sec`の周期で割った位置
        だけで判定するステートレスな実装（呼び出し側で状態を持つ必要がない）。
        このパルスをさらに外側のバースト機構と重ねると固まることがあるため、
        _spin_drive_commandのdocstring参照。"""
        cycle = self.config.spin_pulse_on_sec + self.config.spin_pulse_off_sec
        phase = time.time() % cycle
        is_on = phase < self.config.spin_pulse_on_sec
        if is_on:
            return self._spin_drive_command(spin_w)
        return "drive:0,0"

    def _forward_or_drive_command(self, v: int, w: int) -> str:
        """API_DOCUMENTATION.md 2.1/2.6: WSの"forward"/"backward"はESP32側の
        MPU-6050ジャイロ直進PID補正を経由するが、2.2のdrive:v,w(差動PWM直接指定)
        は経由しない。ヘディング補正がほぼ不要(|w|が閾値以下)なときはforward/
        backwardを使ってジャイロPIDの恩恵を受け、実際に操舵が必要なときのみ
        drive:v,wの差動制御にフォールバックする(config.straight_command_w_threshold
        参照)。speed(PWM)はCommandThread側がforward/backward送信時にのみ
        speed:Nとして送るため、ここではコマンド文字列だけ決めればよい。

        v==0(_ramp_speed_signedがまだ0からランプアップし切っていない等)のときは
        forward/backwardを返さない。CommandThreadはspeed>0のときしかspeed:Nを
        送らないため、v==0で"forward"を返すとspeedが送られずESP32側に残っている
        古い速度のまま動いてしまう(実機で報告されたバグ)。"""
        if v == 0:
            return "drive:0,0"
        if abs(w) <= self.config.straight_command_w_threshold:
            return "forward" if v >= 0 else "backward"
        return f"drive:{v},{w}"

    def _distance_proportional_pwm(self, dist_error_m: float) -> int:
        """距離帯(32.5-47.5cm)からどれだけ離れているかに比例してPWMを決める。
        距離帯のすぐ外側ではmin_pwm(180)寄りの低速、approach_slowdown_dist(既定1.0m)
        以上離れていればmax_follow_pwm(既定200)まで出す。実機で「速すぎて衝突した」
        ため、固定でmin_pwmに加算していた旧ロジックから距離比例の減速に変更した。"""
        overshoot = max(0.0, dist_error_m - self.config.distance_band)
        ratio = min(1.0, overshoot / self.config.approach_slowdown_dist)
        pwm_range = self.config.max_follow_pwm - self.config.min_pwm
        return int(self.config.min_pwm + ratio * pwm_range)

    def _ramp_speed_signed(self, target_signed_pwm: int) -> int:
        """符号付き目標PWM(前進+/後退-)へ_max_v_step刻みで滑らかに近づけ、
        API_DOCUMENTATION.md 2.2の GET /drive?v=&w= に渡すvとして使う値を返す。
        旧実装はレートリミット後の値を捨てて目標PWMをそのまま返していたため、
        _max_v_stepによる加速抑制が実質効いておらず、速度が一気に立ち上がって
        衝突する一因になっていた（実機で報告されたバグ）。min_pwm未満の区間は
        モータが物理的に反応しないだけで実害はないため、そのまま通す
        （0を跨いで前進<->後退が切り替わる際も連続的にランプする）。"""
        v_cmd = int(max(self._prev_v_cmd - self._max_v_step,
                         min(self._prev_v_cmd + self._max_v_step, target_signed_pwm)))
        self._prev_v_cmd = v_cmd
        return v_cmd

    def _handle_head_on(self, yaw_deg, dist_m) -> dict:
        """正対時の処理。現状は停止のみ。
        将来: 車の背後(yaw≈0付近)に回り込む軌道生成ロジックに置き換える拡張ポイント。"""
        return self._stop_command("正対検知(yaw≈180°) - 現状は停止のみ")

    def _handle_approaching_blind(self, bbox, frame_w: int) -> dict:
        """スペックでは「ジンバルpan偏差のみ」とあるが、ControlThreadはGimbalThreadの
        内部状態に直接依存させず疎結合を保つため、bbox中心のピクセル誤差を代理指標として使う。
        これは実質的にジンバルが対象を中央に捉えていればpan偏差と同義になる。
        実車テストでこの近似が不十分と分かった場合はself._gimbal_thread._current_panを
        直接参照する形に変更する。

        API_DOCUMENTATION.md 2.2のGET /drive?v=&w=で送る（w: 正=右旋回、
        pixel_error_x>0=対象が右寄りなのでそのままの符号で使える）。"""
        bx, bw = bbox[0], bbox[2]
        cx = bx + bw / 2.0
        pixel_error_x = (cx - frame_w / 2.0) / (frame_w / 2.0)
        w = int(max(-self.config.max_steering_w,
                     min(self.config.max_steering_w, pixel_error_x * self.config.max_steering_w)))
        v = self.config.blind_approach_pwm
        # yaw/distが取れていない(=推論が弱い)状態での前進のため、他の直進駆動
        # 同様にバースト→停止確認方式にする(_pulsed_drive_command参照)。
        command = self._pulsed_drive_command(v, w)
        return {
            "type": "control",
            "command": command,
            "speed": v if command != "drive:0,0" else 0,
            "log": f"[遠距離追従] pan誤差:{pixel_error_x:+.2f} {command}",
        }

    def _stop_command(self, reason: str) -> dict:
        return {
            "type": "control",
            "command": "stop",
            "speed": 0,
            "log": f"停止:{reason}"
        }

    def stop(self):
        self._running = False
        self._err_lin_i = 0.0
        self._prev_err_lin = 0.0
        self._prev_v_cmd = 0


class CommandThread(threading.Thread):
    def __init__(self, input_queue: Queue, send_command: Callable[[str], None], 
                 set_speed: Callable[[int], None], log_callback: Callable[[str, str], None]):
        super().__init__(daemon=True)
        self.input_queue = input_queue
        self.send_command = send_command
        self.set_speed = set_speed
        self.log_callback = log_callback
        self._running = False
        self._cmd_count = 0
        # None = このCommandThreadでまだ一度もspeed:Nを送っていない(起動直後)。
        # 起動直後の1回は必ず送り、以降は値が変わった時だけ送る(無駄な再送を
        # 減らしつつ、ESP32側が起動直後は速度未設定の状態にならないようにする)。
        self._last_sent_speed = None

    def run(self):
        self._running = True
        if self.log_callback:
            self.log_callback("FOLLOW", f"CommandThread開始 log_callback={self.log_callback is not None}")
        while self._running:
            try:
                command_data = self.input_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                self._execute_command(command_data)
            except Exception as e:
                # ここを握りつぶすと、set_speed/send_command(WebSocket送信)の失敗が
                # 完全にサイレントになり、モーターへの送信が抜けたまま追従が
                # 続いてしまう。ログに出して次のコマンドへ進む。
                if self.log_callback:
                    self.log_callback("FOLLOW", f"CommandThread実行エラー: {e}")

    def _execute_command(self, command_data: dict):
        command = command_data.get("command", "stop")
        speed = command_data.get("speed", 0)
        log = command_data.get("log", "")
        chassis_enabled = command_data.get("chassis_enabled", False)

        self._cmd_count += 1

        if self.log_callback:
            # 制御判断の履歴を追えるよう、実際にESP32へ送信したか('v'キーで
            # chassis_follow_enabledがOFFなら計算はしていても送信していない)を
            # 明示する。
            sent_marker = "送信" if chassis_enabled else "計算のみ(chassis未有効)"
            self.log_callback("FOLLOW", f"[CTRL#{self._cmd_count}][{sent_marker}] {log}")

        # Send motor command (Tier 2: only when chassis enabled)
        if chassis_enabled:
            # "drive:v,w" (API_DOCUMENTATION.md 2.2)はvに速度を直接含むため、
            # 別途/speed(またはws "speed:N")を送る必要はない。二重に送ると
            # 後続の"forward"等の旧式コマンドにまで意図しない速度が残ってしまう。
            # forward/backwardの場合はESP32側にspeedを先に反映させてから
            # 移動コマンドを送る(逆順だと1tick古い速度でforward/backwardが
            # 実行されてしまう)。
            # 起動直後の1回目は必ず送信し(ESP32側に未設定のまま動かさない)、
            # 2回目以降は前回送った値からspeedが変化した時だけ送る
            # (毎tickの再送は無駄なWS送信になるため)。
            if (self.set_speed and speed > 0 and not command.startswith("drive:")
                    and speed != self._last_sent_speed):
                self.set_speed(speed)
                self._last_sent_speed = speed
            if self.send_command:
                self.send_command(self._mirror_drive_w(command))

    @staticmethod
    def _mirror_drive_w(command: str) -> str:
        """実機で確認済み: 対象をローバーの右側に置いて追従させたところ、
        計算上は正しい方向(右旋回=w正)のはずが実際には逆方向へ旋回した。
        API_DOCUMENTATION.mdのw符号規約(正=右旋回、Left_PWM=v+w,Right_PWM=v-w)
        通りに車体側モーターが結線されていない(パンサーボと同種のハード側の
        反転)と考えられるため、_send_gimbal()と同じ方針で、実際に送信する
        直前の1箇所だけでwを反転させる。上流の操舵計算(ControlThreadの
        combined_heading_error等)はAPI仕様書通りの符号のまま変更しない。"""
        if not command.startswith("drive:"):
            return command
        try:
            v_str, w_str = command[len("drive:"):].split(",", 1)
            return f"drive:{v_str},{-int(w_str)}"
        except ValueError:
            return command

    def stop(self):
        self._running = False


class FollowController:
    def __init__(self, config: FollowConfig = None, dry_run: bool = False,
                 send_command: Callable[[str], None] = None,
                 set_speed: Callable[[int], None] = None,
                 set_gimbal: Callable[[int, int], None] = None,
                 log_callback: Callable[[str, str], None] = None):
        self.config = config or FollowConfig()
        self._dry_run = dry_run
        self._log_callback = log_callback
        self._send_command = send_command
        self._set_speed = set_speed
        self._set_gimbal = set_gimbal
        
        self._detection_queue = Queue(maxsize=10)
        self._control_queue = Queue(maxsize=10)
        self._command_queue = Queue(maxsize=10)
        
        self._gimbal_thread = None
        self._detection_thread = None
        self._control_thread = None
        self._command_thread = None
        self._active = False
        
        # Chassis follow: True = gimbal + car, False = gimbal only
        self._chassis_follow_enabled = False
        
        # Low-pass filter for yaw smoothing
        self._yaw_filter_alpha = 0.3  # 0.0 = no filter, 1.0 = instant
        self._filtered_yaw = 0.0
    
    def toggle_chassis_follow(self):
        """Toggle chassis follow mode (v key)."""
        self._chassis_follow_enabled = not self._chassis_follow_enabled
        state = "有効" if self._chassis_follow_enabled else "無効"
        if self._log_callback:
            self._log_callback("FOLLOW", f"車体追従: {state}")
        if self._control_thread:
            self._control_thread.chassis_follow_enabled = self._chassis_follow_enabled
        if not self._chassis_follow_enabled:
            # Stop motors when disabling chassis follow
            if self._send_command:
                self._send_command("stop")

    def start(self):
        self._active = True
        self._filtered_yaw = 0.0
        
        # Gimbal thread (high-speed, ~20 Hz)
        self._gimbal_thread = GimbalThread(self._set_gimbal, self._log_callback)
        
        self._detection_thread = DetectionThread(
            self._detection_queue, self._control_queue, self.config, self._log_callback
        )
        self._control_thread = ControlThread(
            self._control_queue, self._command_queue, self.config, self._log_callback
        )
        # Set gimbal thread reference for automatic camera offset
        self._control_thread._gimbal_thread = self._gimbal_thread
        self._command_thread = CommandThread(
            self._command_queue, self._send_command, self._set_speed, self._log_callback
        )
        
        self._gimbal_thread.start()
        self._detection_thread.start()
        self._control_thread.start()
        self._command_thread.start()
        
        if self._log_callback:
            self._log_callback("FOLLOW", "追従制御を開始しました（4スレッド: Gimbal/Detection/Control/Command）")

    def stop(self):
        self._active = False
        
        if self._gimbal_thread:
            self._gimbal_thread.stop()
        if self._detection_thread:
            self._detection_thread.stop()
        if self._control_thread:
            self._control_thread.stop()
        if self._command_thread:
            self._command_thread.stop()
        
        if self._send_command:
            self._send_command("stop")
        
        self._log_callback("FOLLOW", "追従制御を停止しました")

    def update(self, detection: dict):
        if not self._active:
            return
        
        # Send to gimbal thread (high-speed tracking)
        if self._gimbal_thread:
            self._gimbal_thread.update_detection(
                detection.get("bbox"),
                detection.get("frame_w", 640),
                detection.get("frame_h", 480),
                bearing_deg=detection.get("bearing_deg"),
            )
        
        # Send to motor control pipeline
        qsize = self._detection_queue.qsize()
        try:
            self._detection_queue.put_nowait(detection)
            if self._log_callback and qsize == 0:
                yaw = detection.get("yaw_deg")
                dist = detection.get("dist_m")
                self._log_callback("FOLLOW", f"[UPDATE] yaw={yaw} dist={dist} qsize={qsize}")
        except Exception as e:
            if self._log_callback:
                self._log_callback("FOLLOW", f"[UPDATE] queue full: {e}")

    def get_status(self) -> dict:
        return {
            "active": self._active,
            "state": self._control_thread.state.value if self._control_thread else "unknown",
            "queues": {
                "detection": self._detection_queue.qsize(),
                "control": self._control_queue.qsize(),
                "command": self._command_queue.qsize()
            }
        }
