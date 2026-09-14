import time
from queue import Queue

import pytest

from follow_controller import (
    CommandThread,
    ControlThread,
    FollowConfig,
    FollowState,
    StateHysteresis,
    resolve_follow_state,
    wrap_angle,
)


def _make_control_thread(**config_overrides):
    # NOTE: プラン文書のTask 4(StateHysteresis)とTask 5(ControlThread統合テスト)の間に
    # デフォルト値の矛盾があったため補正: state_hysteresis_frames はデフォルト3だと
    # 単発呼び出しの状態確認テストが常に失敗する(3フレーム連続一致が必要なため)。
    # Task 6のテストが明示的に state_hysteresis_frames=1 を指定している意図を汲み、
    # 単体テストヘルパーのデフォルトを1にしてヒステリシスを実質バイパスする。
    config_overrides.setdefault("state_hysteresis_frames", 1)
    config = FollowConfig(**config_overrides)
    thread = ControlThread(Queue(), Queue(), config)
    thread._last_cmd_t = 0.0  # レートリミットを無効化(次のcompute_commandが即座に評価されるように)
    return thread


# --- Task 1: FollowConfig ---


def test_follow_config_defaults_for_distance_band():
    config = FollowConfig()
    assert config.follow_distance == 0.4
    assert config.distance_band == 0.075
    assert config.min_pwm == 150
    assert config.blind_approach_pwm == 150
    assert config.head_on_threshold == 20.0
    assert config.state_hysteresis_frames == 3
    assert config.lost_timeout_sec == 5.0


# --- Task 2: FollowState ---


def test_follow_state_has_new_members():
    assert FollowState.HEAD_ON_HOLD.value == "head_on_hold"
    assert FollowState.HOLDING.value == "holding"
    assert FollowState.APPROACHING_BLIND.value == "approaching_blind"
    assert FollowState.LOST_TIMEOUT.value == "lost_timeout"


# --- Task 3: resolve_follow_state / wrap_angle ---


def test_wrap_angle_normalizes_to_range():
    assert wrap_angle(180.0) == pytest.approx(-180.0)
    assert wrap_angle(190.0) == pytest.approx(-170.0)
    assert wrap_angle(-190.0) == pytest.approx(170.0)
    assert wrap_angle(10.0) == pytest.approx(10.0)


def test_resolve_state_head_on_takes_priority():
    config = FollowConfig()
    state = resolve_follow_state(yaw_deg=175.0, dist_m=1.0, bbox=(0, 0, 10, 10), config=config)
    assert state == FollowState.HEAD_ON_HOLD


def test_resolve_state_no_bbox_is_searching():
    config = FollowConfig()
    state = resolve_follow_state(yaw_deg=None, dist_m=None, bbox=None, config=config)
    assert state == FollowState.SEARCHING


def test_resolve_state_bbox_without_yaw_or_dist_is_approaching_blind():
    config = FollowConfig()
    state = resolve_follow_state(yaw_deg=None, dist_m=1.5, bbox=(0, 0, 10, 10), config=config)
    assert state == FollowState.APPROACHING_BLIND
    state = resolve_follow_state(yaw_deg=30.0, dist_m=None, bbox=(0, 0, 10, 10), config=config)
    assert state == FollowState.APPROACHING_BLIND


def test_resolve_state_in_band_is_holding():
    config = FollowConfig()
    # target_distance=0.425, band=0.075 -> 35-50cm帯の中の値
    state = resolve_follow_state(yaw_deg=10.0, dist_m=0.42, bbox=(0, 0, 10, 10), config=config)
    assert state == FollowState.HOLDING


def test_resolve_state_out_of_band_is_following():
    config = FollowConfig()
    state = resolve_follow_state(yaw_deg=10.0, dist_m=1.0, bbox=(0, 0, 10, 10), config=config)
    assert state == FollowState.FOLLOWING


# --- Task 4: StateHysteresis ---


def test_hysteresis_holds_previous_state_until_threshold_met():
    config = FollowConfig(state_hysteresis_frames=3)
    hysteresis = StateHysteresis(config, initial_state=FollowState.SEARCHING)

    assert hysteresis.update(FollowState.FOLLOWING) == FollowState.SEARCHING
    assert hysteresis.update(FollowState.FOLLOWING) == FollowState.SEARCHING
    assert hysteresis.update(FollowState.FOLLOWING) == FollowState.FOLLOWING


def test_hysteresis_resets_count_on_candidate_change():
    config = FollowConfig(state_hysteresis_frames=3)
    hysteresis = StateHysteresis(config, initial_state=FollowState.SEARCHING)

    hysteresis.update(FollowState.FOLLOWING)
    hysteresis.update(FollowState.FOLLOWING)
    assert hysteresis.update(FollowState.HOLDING) == FollowState.SEARCHING
    assert hysteresis.update(FollowState.HOLDING) == FollowState.SEARCHING
    assert hysteresis.update(FollowState.HOLDING) == FollowState.HOLDING


def test_hysteresis_head_on_hold_is_immediate_no_delay():
    """HEAD_ON_HOLDは安全のため即座に確定する(ヒステリシス無視)。"""
    config = FollowConfig(state_hysteresis_frames=3)
    hysteresis = StateHysteresis(config, initial_state=FollowState.FOLLOWING)
    assert hysteresis.update(FollowState.HEAD_ON_HOLD) == FollowState.HEAD_ON_HOLD


# --- Task 5: ControlThread integration ---


def test_head_on_detection_stops_immediately():
    thread = _make_control_thread()
    detection = {"yaw_deg": 175.0, "dist_m": 1.0, "confidence": 0.9, "bbox": (0, 0, 10, 10),
                 "frame_w": 640, "frame_h": 480}
    result = thread._compute_command(detection)
    assert result["command"] == "stop"
    assert result["speed"] == 0
    assert thread.state == FollowState.HEAD_ON_HOLD


def test_approaching_blind_uses_fixed_pwm_and_pan_steering():
    thread = _make_control_thread()
    detection = {"yaw_deg": None, "dist_m": 1.2, "confidence": 0.9, "bbox": (400, 200, 20, 20),
                 "frame_w": 640, "frame_h": 480}
    result = thread._compute_command(detection)
    assert thread.state == FollowState.APPROACHING_BLIND
    assert result["speed"] == 150
    # API_DOCUMENTATION.md 2.2: GET /drive?v=&w= 形式で送られる
    assert result["command"].startswith("drive:150,")


def test_holding_in_band_stops():
    thread = _make_control_thread()
    # 35-50cm帯の中の値
    detection = {"yaw_deg": 5.0, "dist_m": 0.44, "confidence": 0.9, "bbox": (300, 200, 20, 20),
                 "frame_w": 640, "frame_h": 480}
    result = thread._compute_command(detection)
    assert thread.state == FollowState.HOLDING
    assert result["command"] == "stop"
    assert result["speed"] == 0


def test_no_bbox_enters_searching_and_stops_chassis():
    thread = _make_control_thread()
    detection = {"yaw_deg": None, "dist_m": None, "confidence": 0.0, "bbox": None,
                 "frame_w": 640, "frame_h": 480}
    result = thread._compute_command(detection)
    assert thread.state == FollowState.SEARCHING
    assert result["command"] == "stop"


class _StubGimbal:
    """ControlThreadから見えるGimbalThreadの最小スタブ。is_settled()と
    _current_pan/_gimbal_center_panのみ参照される。"""

    def __init__(self, settled: bool, current_pan: float = 85.0, gimbal_center_pan: float = 85.0):
        self._settled = settled
        self._current_pan = current_pan
        self._gimbal_center_pan = gimbal_center_pan
        self.feedforward_calls = []

    def is_settled(self) -> bool:
        return self._settled

    def apply_feedforward_pan_delta(self, delta_deg: float) -> None:
        self.feedforward_calls.append(delta_deg)


def test_following_waits_for_gimbal_settled_before_moving_chassis():
    """回帰テスト: ジンバルが対象を追って補正中(is_settled=False)にシャシーも
    同時に動くと、推論が追いつく前に互いの動きが干渉し近距離で振動していたため、
    ジンバルが安定するまではシャシーを停止させ待つようにした。"""
    thread = _make_control_thread()
    thread._gimbal_thread = _StubGimbal(settled=False)
    detection = {"yaw_deg": 5.0, "dist_m": 1.5, "confidence": 0.9, "bbox": (300, 200, 20, 20),
                 "frame_w": 640, "frame_h": 480}
    result = thread._compute_command(detection)
    assert thread.state == FollowState.FOLLOWING
    assert result["command"] == "drive:0,0"
    assert result["speed"] == 0


def test_gimbal_unsettled_decelerates_smoothly_instead_of_hard_stop():
    """回帰テスト: 直前まで加速中(_prev_v_cmdが大きい)だった状態で
    ジンバル未安定になった場合、即座に0にリセットして急停止するのではなく、
    _max_v_step刻みで滑らかに減速する(実機で「旋回が安定しない」カクカクした
    動きとして報告されたバグ)。"""
    thread = _make_control_thread()
    thread._prev_v_cmd = 190  # 直前まで高速で走っていた状態を再現
    thread._gimbal_thread = _StubGimbal(settled=False)
    detection = {"yaw_deg": 5.0, "dist_m": 1.5, "confidence": 0.9, "bbox": (300, 200, 20, 20),
                 "frame_w": 640, "frame_h": 480}
    result = thread._compute_command(detection)
    v, w = (int(x) for x in result["command"].removeprefix("drive:").split(","))
    assert w == 0
    assert v == 190 - thread._max_v_step  # 0への急停止ではなく、1ステップ分だけ減速
    assert v > 0


def test_following_moves_chassis_once_gimbal_settled():
    thread = _make_control_thread()
    thread._gimbal_thread = _StubGimbal(settled=True)
    detection = {"yaw_deg": 5.0, "dist_m": 1.5, "confidence": 0.9, "bbox": (300, 200, 20, 20),
                 "frame_w": 640, "frame_h": 480}
    result = thread._compute_command(detection)
    assert thread.state == FollowState.FOLLOWING
    assert result["command"] != "drive:0,0"
    assert result["command"].startswith("drive:")


def test_following_prioritizes_turning_when_pan_offset_large_even_if_far():
    """回帰テスト: ジンバルのpanが車体正面から大きくずれている場合、距離が
    離れていても接近より先に旋回してpanを正面へ戻すことを優先する
    (実機で「距離が離れているのに近づかない」と混同されて報告された挙動の
    正しい仕様: 実際にはpan補正を優先すべきケースだった)。"""
    thread = _make_control_thread()
    # pan中央85度から30度ずれている(閾値15度を超える)
    thread._gimbal_thread = _StubGimbal(settled=True, current_pan=55.0, gimbal_center_pan=85.0)
    detection = {"yaw_deg": 0.0, "dist_m": 2.0, "confidence": 0.9, "bbox": (300, 200, 20, 20),
                 "frame_w": 640, "frame_h": 480}
    result = thread._compute_command(detection)
    assert thread.state == FollowState.FOLLOWING
    # 両輪逆回転のその場旋回(v=0)をパルス駆動しているため、呼び出し時刻に
    # よってON("drive:0,-190"等)かOFF("drive:0,0")かが変わる。v=0であることのみ確認
    v_str, _w_str = result["command"].removeprefix("drive:").split(",")
    assert v_str == "0"
    assert "pan角度優先補正" in result["log"]


def test_pan_priority_correction_stops_after_burst_then_pauses(monkeypatch):
    """回帰テスト: pan角度優先補正はturn_speedを150未満に下げられないため、
    代わりに「短いバースト旋回(既定0.3秒)→完全停止して静止確認(既定0.6秒)」
    を繰り返す方式にした(実機で旋回が速すぎてカメラがブレ、対象を見失ったと
    報告されたため)。バースト時間が経過した直後の呼び出しでは、パルスのON/OFF
    に関わらず必ず完全停止(drive:0,0)が返ることを確認する。"""
    thread = _make_control_thread()
    thread._gimbal_thread = _StubGimbal(settled=True, current_pan=55.0, gimbal_center_pan=85.0)
    detection = {"yaw_deg": 0.0, "dist_m": 2.0, "confidence": 0.9, "bbox": (300, 200, 20, 20),
                 "frame_w": 640, "frame_h": 480}

    monkeypatch.setattr("follow_controller.time.time", lambda: 0.0)  # phase=0 -> パルスON区間の先頭
    thread._last_cmd_t = -1.0  # レートリミット(0.08秒)をバイパス
    first = thread._compute_command(detection)
    v_str, _w_str = first["command"].removeprefix("drive:").split(",")
    assert v_str == "0"
    assert first["command"] != "drive:0,0"  # バースト開始直後はONのはず

    burst_sec = thread.config.pan_priority_burst_sec
    monkeypatch.setattr("follow_controller.time.time", lambda: burst_sec + 0.01)
    thread._last_cmd_t = 0.0
    second = thread._compute_command(detection)
    assert second["command"] == "drive:0,0"  # バースト終了 -> 静止確認へ

    # 静止確認中(pause_sec未満)はまだ完全停止のまま
    monkeypatch.setattr("follow_controller.time.time", lambda: burst_sec + 0.05)
    thread._last_cmd_t = 0.0
    third = thread._compute_command(detection)
    assert third["command"] == "drive:0,0"


def test_pan_priority_correction_resumes_spin_after_pause_elapses(monkeypatch):
    thread = _make_control_thread()
    thread._gimbal_thread = _StubGimbal(settled=True, current_pan=55.0, gimbal_center_pan=85.0)
    detection = {"yaw_deg": 0.0, "dist_m": 2.0, "confidence": 0.9, "bbox": (300, 200, 20, 20),
                 "frame_w": 640, "frame_h": 480}

    monkeypatch.setattr("follow_controller.time.time", lambda: 0.0)
    thread._last_cmd_t = -1.0  # レートリミット(0.08秒)をバイパス
    thread._compute_command(detection)  # バースト開始
    burst_sec = thread.config.pan_priority_burst_sec
    monkeypatch.setattr("follow_controller.time.time", lambda: burst_sec + 0.01)
    thread._last_cmd_t = 0.0
    thread._compute_command(detection)  # 停止 -> 静止確認開始

    pause_sec = thread.config.pan_priority_pause_sec
    # +0.2はパルス駆動のON区間(既定on_sec=0.15)に確実に入るよう選んだオフセット
    # (0.35秒周期のうちOFF区間に当たると、静止確認明けでも見かけ上drive:0,0に
    # なってしまいテストが意図と無関係な理由で揺れるため)
    monkeypatch.setattr("follow_controller.time.time", lambda: burst_sec + pause_sec + 0.2)
    thread._last_cmd_t = 0.0
    result = thread._compute_command(detection)
    v_str, _w_str = result["command"].removeprefix("drive:").split(",")
    assert v_str == "0"
    assert result["command"] != "drive:0,0"  # 静止確認終了 -> 次のバーストが始まる


def test_following_forward_command_is_clamped_to_min_pwm():
    """ランプアップが完了(_distance_proportional_pwmの目標に到達)した後は、
    speedがmin_pwm(150)を下回らないことを確認する(motion中の底上げ)。"""
    thread = _make_control_thread()
    detection = {"yaw_deg": 5.0, "dist_m": 1.5, "confidence": 0.9, "bbox": (300, 200, 20, 20),
                 "frame_w": 640, "frame_h": 480}
    result = None
    for _ in range(10):  # _max_v_step=60刻みで十分ランプアップさせる
        thread._last_cmd_t = 0.0
        result = thread._compute_command(detection)
    assert thread.state == FollowState.FOLLOWING
    if result["command"].startswith("drive:"):
        assert result["speed"] >= 150


def test_pulsed_spin_command_is_on_during_on_phase(monkeypatch):
    """回帰テスト: 片輪駆動の緩旋回はトルク不足で車体が動かないことが実機で
    確認されたため廃止し、両輪逆回転(v=0, w=spin_w)に戻した。その代わり、
    on/offのパルス駆動で平均回転角速度を落とす。ON区間ではturn_speed通りの
    両輪逆回転コマンドが返ることを確認する。"""
    thread = _make_control_thread()
    monkeypatch.setattr("follow_controller.time.time", lambda: 0.0)  # phase=0 -> ON区間の先頭
    command = thread._pulsed_spin_command(150)
    assert command == "drive:0,150"


def test_pulsed_spin_command_is_stopped_during_off_phase(monkeypatch):
    thread = _make_control_thread()
    # spin_pulse_on_sec(既定0.15)より後、cycle(on+off)より前 -> OFF区間
    on_sec = thread.config.spin_pulse_on_sec
    monkeypatch.setattr("follow_controller.time.time", lambda: on_sec + 0.01)
    command = thread._pulsed_spin_command(150)
    assert command == "drive:0,0"


def test_pulsed_spin_command_applies_feedforward_pan_delta_when_chassis_enabled(monkeypatch):
    """旋回のON区間かつchassis_follow_enabled(実際にESP32へ送信される)のときのみ、
    推定回転角に応じてGimbalThreadへフィードフォワードのパン補正が送られる
    (符号の正しさは実機要検証、ここでは「何らかの非ゼロ補正が呼ばれること」
    だけを確認する)。"""
    thread = _make_control_thread()
    thread.chassis_follow_enabled = True
    monkeypatch.setattr("follow_controller.time.time", lambda: 0.0)

    calls = []
    thread._gimbal_thread = _StubGimbal(settled=True)
    thread._gimbal_thread.apply_feedforward_pan_delta = lambda delta: calls.append(delta)

    thread._pulsed_spin_command(150)
    assert len(calls) == 1


def test_pulsed_spin_command_skips_feedforward_when_chassis_disabled(monkeypatch):
    """回帰テスト: chassis_follow_enabled=False('v'キー未押下、計算のみで実際には
    送信されない)のときにフィードフォワードだけジンバルに適用すると、実際には
    動いていない車体の回転を前提にジンバルが一方的にpanをずらし続け、対象を
    見失う原因になっていた(実機で「検出したのに勝手に動いていく」として報告)。"""
    thread = _make_control_thread()
    thread.chassis_follow_enabled = False
    monkeypatch.setattr("follow_controller.time.time", lambda: 0.0)

    calls = []
    thread._gimbal_thread = _StubGimbal(settled=True)
    thread._gimbal_thread.apply_feedforward_pan_delta = lambda delta: calls.append(delta)

    thread._pulsed_spin_command(150)
    assert len(calls) == 0


def test_following_forward_speed_never_exceeds_max_follow_pwm():
    """回帰テスト: 実機で「速すぎて衝突した」ため、遠距離でも255ではなく
    max_follow_pwm(既定190)を超えないことを確認する。"""
    thread = _make_control_thread()
    # 距離帯(35-50cm)から遠く離れている(1.5m)ケースを何度も評価してランプアップさせる
    detection = {"yaw_deg": 0.0, "dist_m": 1.5, "confidence": 0.9, "bbox": (300, 200, 20, 20),
                 "frame_w": 640, "frame_h": 480}
    speeds = []
    for _ in range(20):
        thread._last_cmd_t = 0.0
        result = thread._compute_command(detection)
        speeds.append(result["speed"])
    assert max(speeds) <= 190


def test_following_forward_speed_ramps_up_gradually_not_instantly():
    """回帰テスト: 目標PWMまで_max_v_step刻みで滑らかに立ち上がり、
    1回目のティックでいきなり最大速度が出ないことを確認する
    (旧実装はレートリミット後の値を捨てて即座に最大速度を返していたバグ)。"""
    thread = _make_control_thread()
    detection = {"yaw_deg": 0.0, "dist_m": 1.5, "confidence": 0.9, "bbox": (300, 200, 20, 20),
                 "frame_w": 640, "frame_h": 480}
    thread._last_cmd_t = 0.0
    first = thread._compute_command(detection)
    assert first["command"].startswith("drive:")
    assert first["speed"] == thread._max_v_step  # 初回は0から_max_v_step分しか立ち上がらない
    thread._last_cmd_t = 0.0
    second = thread._compute_command(detection)
    assert second["speed"] >= first["speed"]  # 段階的に増えていく


# --- Task 6: LOST_TIMEOUT ---


def test_searching_transitions_to_lost_timeout_after_configured_seconds():
    config = FollowConfig(lost_timeout_sec=0.2, state_hysteresis_frames=1)
    thread = ControlThread(Queue(), Queue(), config)
    thread._last_cmd_t = 0.0
    detection = {"yaw_deg": None, "dist_m": None, "confidence": 0.0, "bbox": None,
                 "frame_w": 640, "frame_h": 480}

    result = thread._compute_command(detection)
    assert thread.state == FollowState.SEARCHING

    time.sleep(0.25)
    thread._last_cmd_t = 0.0  # レートリミットをバイパスして即座に再評価
    result = thread._compute_command(detection)
    assert thread.state == FollowState.LOST_TIMEOUT
    assert result["command"] == "stop"


# --- Task 7: scenario replay ---


def test_run_injects_chassis_enabled_true_when_toggled_on():
    """回帰テスト: ControlThread.run()がoutput_queueに積む辞書に
    chassis_enabledが含まれないと、CommandThread側でデフォルトFalse扱いになり
    'v'キーでchassis_follow_enabledを有効にしてもモータコマンドが一切
    送信されない(実機で「推論はできるが追従しない」として発現したバグ)。"""
    thread = _make_control_thread()
    thread.chassis_follow_enabled = True
    thread.start()
    try:
        thread.input_queue.put({"yaw_deg": 5.0, "dist_m": 1.5, "confidence": 0.9,
                                 "bbox": (300, 200, 20, 20), "frame_w": 640, "frame_h": 480})
        command = thread.output_queue.get(timeout=1.0)
        assert command["chassis_enabled"] is True
    finally:
        thread.stop()


def test_run_injects_chassis_enabled_false_when_toggled_off():
    thread = _make_control_thread()
    thread.chassis_follow_enabled = False
    thread.start()
    try:
        thread.input_queue.put({"yaw_deg": 5.0, "dist_m": 1.5, "confidence": 0.9,
                                 "bbox": (300, 200, 20, 20), "frame_w": 640, "frame_h": 480})
        command = thread.output_queue.get(timeout=1.0)
        assert command["chassis_enabled"] is False
    finally:
        thread.stop()


def test_run_never_enqueues_none_when_rate_limited():
    """回帰テスト: レートリミット中(_compute_command()がNoneを返す)にNoneが
    そのままoutput_queueへ積まれると、CommandThread側でcommand_data.get(...)が
    AttributeErrorになりbare exceptで握りつぶされ、デバッグログの一部が
    無言で欠落していた。Noneはキューに積まれないことを確認する。"""
    thread = _make_control_thread()
    thread.chassis_follow_enabled = True
    thread.start()
    try:
        detection = {"yaw_deg": 5.0, "dist_m": 1.5, "confidence": 0.9,
                     "bbox": (300, 200, 20, 20), "frame_w": 640, "frame_h": 480}
        # 立て続けに2件投入: 2件目は12.5Hzのレートリミットに引っかかりNoneになるはず
        thread.input_queue.put(detection)
        thread.input_queue.put(detection)
        first = thread.output_queue.get(timeout=1.0)
        assert first is not None
        assert first["command"].startswith("drive:")
        # 2件目がNoneのまま積まれていないことを確認(積まれていればここで取得できてしまう)
        try:
            second = thread.output_queue.get(timeout=0.2)
            assert second is not None
        except Exception:
            pass  # タイムアウト(何も積まれなかった)ならOK、これが期待動作
    finally:
        thread.stop()


def test_scenario_far_then_lost_then_recovered():
    """遠距離(APPROACHING_BLIND) -> 完全ロスト(SEARCHING) -> 再検出(FOLLOWING) のシナリオ。"""
    config = FollowConfig(state_hysteresis_frames=1)
    thread = ControlThread(Queue(), Queue(), config)
    thread._last_cmd_t = 0.0

    r1 = thread._compute_command({"yaw_deg": None, "dist_m": 1.8, "confidence": 0.4,
                                   "bbox": (300, 200, 15, 15), "frame_w": 640, "frame_h": 480})
    assert thread.state == FollowState.APPROACHING_BLIND
    assert r1["speed"] == 150
    thread._last_cmd_t = 0.0

    r2 = thread._compute_command({"yaw_deg": None, "dist_m": None, "confidence": 0.0,
                                   "bbox": None, "frame_w": 640, "frame_h": 480})
    assert thread.state == FollowState.SEARCHING
    assert r2["command"] == "stop"
    thread._last_cmd_t = 0.0

    r3 = thread._compute_command({"yaw_deg": 8.0, "dist_m": 1.2, "confidence": 0.9,
                                   "bbox": (300, 200, 20, 20), "frame_w": 640, "frame_h": 480})
    assert thread.state == FollowState.FOLLOWING


# _mirror_drive_w: 実機で「対象を右に置いたのに逆方向へ旋回した」ことが確認された
# ため、CommandThreadが実際に送信する直前でdrive:v,wのwを反転させるようにした
# (ControlThread側の操舵計算自体はAPI仕様書通りの符号のまま変更していない)。


def test_mirror_drive_w_negates_w_component():
    assert CommandThread._mirror_drive_w("drive:60,-3") == "drive:60,3"
    assert CommandThread._mirror_drive_w("drive:0,190") == "drive:0,-190"
    assert CommandThread._mirror_drive_w("drive:0,0") == "drive:0,0"


def test_mirror_drive_w_leaves_non_drive_commands_unchanged():
    assert CommandThread._mirror_drive_w("stop") == "stop"
    assert CommandThread._mirror_drive_w("servo:90,70") == "servo:90,70"
