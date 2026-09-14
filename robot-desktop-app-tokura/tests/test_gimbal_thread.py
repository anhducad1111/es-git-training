import time

from follow_controller import GimbalThread


def _make_gimbal(**overrides):
    calls = []

    def _set_gimbal(pan, tilt):
        calls.append((pan, tilt))

    thread = GimbalThread(_set_gimbal, **overrides)
    thread._calls = calls
    return thread


# 1. パン/チルトが範囲外にクランプされる (0-170, 40-130)


def test_pan_is_clamped_to_configured_range():
    thread = _make_gimbal(pan_min_deg=0.0, pan_max_deg=170.0, step_deg=5.0, deadband=0.15,
                           move_cooldown_sec=0.0)
    thread._current_pan = 1.0
    thread._current_tilt = 70.0
    # 対象が右端(パンを更に押し出す方向)にいるケースを大きく外側へずらす
    frame_w, frame_h = 640, 480
    bbox = (0, 220, 20, 40)  # 左端 -> パンをさらに範囲外方向へ動かそうとする
    thread._track_target(bbox, frame_w, frame_h)
    assert 0.0 <= thread._current_pan <= 170.0


def test_tilt_is_clamped_to_configured_range():
    thread = _make_gimbal(tilt_min_deg=40.0, tilt_max_deg=130.0, step_deg=5.0, deadband=0.15,
                           move_cooldown_sec=0.0)
    thread._current_pan = 85.0
    thread._current_tilt = 41.0
    frame_w, frame_h = 640, 480
    bbox = (300, 0, 20, 10)  # 上端 -> チルトをさらに範囲外方向へ動かそうとする
    thread._track_target(bbox, frame_w, frame_h)
    assert 40.0 <= thread._current_tilt <= 130.0


# 2. デッドバンド内では角度が変化しない


def test_within_deadband_pan_does_not_change():
    thread = _make_gimbal(step_deg=5.0, deadband=0.15, move_cooldown_sec=0.0)
    thread._current_pan = 85.0
    thread._current_tilt = 70.0
    frame_w, frame_h = 640, 480
    # bboxを画面中心に配置(誤差ほぼ0)
    bbox = (frame_w // 2 - 10, frame_h // 2 - 10, 20, 20)
    thread._track_target(bbox, frame_w, frame_h)
    assert thread._current_pan == 85.0


# 3. デッドバンドを超えると5°ステップで中心方向に動く


def test_beyond_deadband_pan_moves_by_one_step():
    thread = _make_gimbal(step_deg=5.0, deadband=0.15, move_cooldown_sec=0.0)
    thread._current_pan = 85.0
    thread._current_tilt = 70.0
    frame_w, frame_h = 640, 480
    # bboxを画面右寄りに配置(中心から大きくずれる)
    bbox = (frame_w - 40, frame_h // 2 - 10, 20, 20)
    thread._track_target(bbox, frame_w, frame_h)
    assert abs(thread._current_pan - 85.0) == 5.0


# 単発の検知ミス(bbox=Noneが1フレームだけ)では、すぐにスピン探索へ移らず
# 猶予期間(bbox_loss_grace_sec)は今の角度を保持する(見逃し対策)


def test_within_bbox_loss_grace_period_right_after_seeing_target():
    thread = _make_gimbal(bbox_loss_grace_sec=0.5)
    thread._last_bbox_seen_time = time.time()
    assert thread._within_bbox_loss_grace(time.time()) is True


def test_outside_bbox_loss_grace_period_after_grace_elapses():
    thread = _make_gimbal(bbox_loss_grace_sec=0.1)
    thread._last_bbox_seen_time = time.time() - 0.2  # 猶予期間より前
    assert thread._within_bbox_loss_grace(time.time()) is False


def test_never_seen_bbox_is_outside_grace_immediately():
    thread = _make_gimbal(bbox_loss_grace_sec=0.5)
    # _last_bbox_seen_timeの初期値は0.0(未検知) -> 猶予期間の対象外(即探索でよい)
    assert thread._within_bbox_loss_grace(time.time()) is False


# bearing_deg(atan2による実角度)が渡されたときは固定5度ステップではなく
# その角度そのもので動く(実機で「中心付近で行ったり来たりする」と報告された振動対策)


def test_bearing_deg_moves_pan_by_exact_angle_not_fixed_step():
    thread = _make_gimbal(step_deg=5.0, deadband=0.15, move_cooldown_sec=0.0,
                           bearing_deadband=1.0, max_bearing_step=20.0)
    thread._current_pan = 85.0
    thread._current_tilt = 70.0
    frame_w, frame_h = 640, 480
    bbox = (frame_w - 40, frame_h // 2 - 10, 20, 20)  # ピクセル的には大きくずれている
    thread._track_target(bbox, frame_w, frame_h, bearing_deg=12.3)
    # 固定5度ではなく、bearing_degそのもの(12.3度)だけ動く
    assert thread._current_pan == 85.0 - 12.3


def test_bearing_deg_within_deadband_does_not_move():
    thread = _make_gimbal(move_cooldown_sec=0.0, bearing_deadband=1.0)
    thread._current_pan = 85.0
    thread._current_tilt = 70.0
    frame_w, frame_h = 640, 480
    bbox = (frame_w - 40, frame_h // 2 - 10, 20, 20)
    thread._track_target(bbox, frame_w, frame_h, bearing_deg=0.5)  # デッドバンド未満
    assert thread._current_pan == 85.0


def test_bearing_deg_is_clamped_to_max_bearing_step():
    thread = _make_gimbal(move_cooldown_sec=0.0, bearing_deadband=1.0, max_bearing_step=20.0)
    thread._current_pan = 85.0
    thread._current_tilt = 70.0
    frame_w, frame_h = 640, 480
    bbox = (frame_w - 40, frame_h // 2 - 10, 20, 20)
    thread._track_target(bbox, frame_w, frame_h, bearing_deg=80.0)  # 外れ値
    assert thread._current_pan == 85.0 - 20.0  # max_bearing_stepでクランプされる


def test_bearing_deg_none_falls_back_to_fixed_step():
    thread = _make_gimbal(step_deg=5.0, deadband=0.15, move_cooldown_sec=0.0)
    thread._current_pan = 85.0
    thread._current_tilt = 70.0
    frame_w, frame_h = 640, 480
    bbox = (frame_w - 40, frame_h // 2 - 10, 20, 20)
    thread._track_target(bbox, frame_w, frame_h, bearing_deg=None)
    assert abs(thread._current_pan - 85.0) == 5.0


# 4. クールダウン中は連続してtrack_targetを呼んでも角度が変化しない


def test_cooldown_prevents_consecutive_moves():
    thread = _make_gimbal(step_deg=5.0, deadband=0.15, move_cooldown_sec=1.0)
    thread._current_pan = 85.0
    thread._current_tilt = 70.0
    frame_w, frame_h = 640, 480
    bbox = (frame_w - 40, frame_h // 2 - 10, 20, 20)

    thread._track_target(bbox, frame_w, frame_h)
    first_pan = thread._current_pan
    assert first_pan != 85.0  # 1回目は動く

    # 直後にもう一度呼んでもクールダウン中なので変化しない
    thread._track_target(bbox, frame_w, frame_h)
    assert thread._current_pan == first_pan


# 見つかった直後は長いクールダウン(move_cooldown_sec)で安定を待ち、その後
# 連続して追従できている間は短いクールダウン(tracking_cooldown_sec)で素早く反応する


def test_actual_move_forces_long_cooldown_before_next_move():
    """回帰テスト: 角度を実際に動かした直後にtracking_cooldown_sec(短い)で
    すぐ次の補正を出すと、サーボが前回の補正を完了する前に次の補正が
    積み上がり振動が増幅していく問題があったため、実際に動かした直後は
    必ずmove_cooldown_sec(長い、サーボが追いつくのを待つ)を使うようにした。"""
    thread = _make_gimbal(step_deg=5.0, deadband=0.15,
                           move_cooldown_sec=1.0, tracking_cooldown_sec=0.0)
    thread._current_pan = 85.0
    thread._current_tilt = 70.0
    thread._search_state = "search_direction"  # 直前まで探索中だった状態を再現
    frame_w, frame_h = 640, 480
    bbox = (frame_w - 40, frame_h // 2 - 10, 20, 20)

    # 1回目(見つかった直後): 実際に動く
    thread._track_target(bbox, frame_w, frame_h)
    first_pan = thread._current_pan
    assert first_pan != 85.0
    assert thread._search_state == "tracking"

    # 2回目(直後): tracking_cooldown_sec=0.0だが、直前に実際に動いたので
    # move_cooldown_sec(1.0)がまだ経過しておらずクールダウン中 -> 動かない
    thread._track_target(bbox, frame_w, frame_h)
    assert thread._current_pan == first_pan


def test_no_move_needed_allows_fast_recheck_via_tracking_cooldown():
    """対象が既にデッドバンド内(補正不要)なら、次のtickはtracking_cooldown_sec
    (短い)ですぐ再評価してよい。"""
    thread = _make_gimbal(step_deg=5.0, deadband=0.15,
                           move_cooldown_sec=1.0, tracking_cooldown_sec=0.0)
    thread._current_pan = 85.0
    thread._current_tilt = 70.0
    frame_w, frame_h = 640, 480
    centered_bbox = (frame_w // 2 - 10, frame_h // 2 - 10, 20, 20)

    # 1回目: 中心付近なので動かない
    thread._track_target(centered_bbox, frame_w, frame_h)
    assert thread._current_pan == 85.0
    assert thread._last_move_had_delta is False

    # 2回目(直後): 対象が右にずれても、直前は「動かなかった」のでtracking_cooldown_sec(0.0)
    # が適用され、即座に補正できる
    offset_bbox = (frame_w - 40, frame_h // 2 - 10, 20, 20)
    thread._track_target(offset_bbox, frame_w, frame_h)
    assert thread._current_pan != 85.0


def test_first_detection_gates_search_until_inference_reports_once():
    thread = _make_gimbal()
    assert thread._first_detection_received is False
    thread.update_detection(bbox=None, frame_w=640, frame_h=480)
    assert thread._first_detection_received is True


# 5. チルトがデッドバンド内(対象がほぼ中心)のとき、現在のチルトがキャリブレーション角度(70)と
#    異なれば5°ステップで70度に近づく


def test_tilt_returns_toward_calibration_angle_when_centered():
    thread = _make_gimbal(step_deg=5.0, deadband=0.15, move_cooldown_sec=0.0,
                           calibration_tilt_deg=70.0)
    thread._current_pan = 85.0
    thread._current_tilt = 90.0  # キャリブレーション角度からずれた状態
    frame_w, frame_h = 640, 480
    bbox = (frame_w // 2 - 10, frame_h // 2 - 10, 20, 20)  # 画面中心(デッドバンド内)
    thread._track_target(bbox, frame_w, frame_h)
    assert thread._current_tilt == 85.0  # 90 -> 5度分だけ70に近づく


def test_tilt_does_not_move_when_already_at_calibration_angle():
    thread = _make_gimbal(step_deg=5.0, deadband=0.15, move_cooldown_sec=0.0,
                           calibration_tilt_deg=70.0)
    thread._current_pan = 85.0
    thread._current_tilt = 70.0
    frame_w, frame_h = 640, 480
    bbox = (frame_w // 2 - 10, frame_h // 2 - 10, 20, 20)
    thread._track_target(bbox, frame_w, frame_h)
    assert thread._current_tilt == 70.0


# 回帰テスト: 車体が画面下寄りに映る程度の通常の縦ズレでは、チルトは
# キャリブレーション角度への復帰を優先し、追従優先モードに入らない
# (実機で「車が静止しているのにチルトが動き続ける」として報告されたバグ)


def test_tilt_stays_in_return_mode_for_moderate_vertical_offset():
    thread = _make_gimbal(step_deg=5.0, deadband=0.15, move_cooldown_sec=0.0,
                           calibration_tilt_deg=70.0)
    thread._current_pan = 85.0
    thread._current_tilt = 90.0  # キャリブレーション角度からずれた状態
    frame_w, frame_h = 640, 480
    # error_y ≈ 0.39相当(車体が画面下寄りに映る、実機ログで観測された程度のズレ)
    bbox = (270, 184, 291, 303)
    thread._track_target(bbox, frame_w, frame_h)
    # 追従優先(誤差方向へのステップ)ではなく、復帰優先(70度へ5度分近づく)になっているはず
    assert thread._current_tilt == 85.0


def test_tilt_switches_to_tracking_mode_near_frame_edge():
    thread = _make_gimbal(step_deg=5.0, deadband=0.15, move_cooldown_sec=0.0,
                           calibration_tilt_deg=70.0)
    thread._current_pan = 85.0
    thread._current_tilt = 70.0
    frame_w, frame_h = 640, 480
    # 対象がほぼ画面下端(error_y > tilt_deadband=0.5) -> 見失い防止のため追従優先
    bbox = (270, 420, 20, 20)
    thread._track_target(bbox, frame_w, frame_h)
    assert thread._current_tilt == 75.0  # 70から追従方向(+5度)へステップ


# compute_discrete_step の単体テスト


def test_compute_discrete_step_returns_zero_within_deadband():
    thread = _make_gimbal()
    assert thread._compute_discrete_step(0.05, deadband=0.15, step_deg=5.0) == 0.0
    assert thread._compute_discrete_step(-0.1, deadband=0.15, step_deg=5.0) == 0.0


def test_compute_discrete_step_returns_step_outside_deadband():
    thread = _make_gimbal()
    assert thread._compute_discrete_step(0.5, deadband=0.15, step_deg=5.0) != 0.0
    assert abs(thread._compute_discrete_step(0.5, deadband=0.15, step_deg=5.0)) == 5.0
    assert abs(thread._compute_discrete_step(-0.5, deadband=0.15, step_deg=5.0)) == 5.0


# is_settled のテスト


def test_is_settled_true_before_any_move():
    thread = _make_gimbal(move_cooldown_sec=1.0)
    assert thread.is_settled() is True


def test_is_settled_false_immediately_after_move_then_true_after_cooldown():
    """is_settled()はtracking_cooldown_sec(実際の追従中の反応間隔)を基準にする。
    以前は常に長いmove_cooldown_secを基準にしていたため、追従中に短い間隔で
    微補正が入るたびに長時間「未安定」のままになり、シャシーが距離が離れていても
    近づけない問題が実機で報告された。"""
    thread = _make_gimbal(step_deg=5.0, deadband=0.15, tracking_cooldown_sec=0.05)
    thread._current_pan = 85.0
    thread._current_tilt = 70.0
    frame_w, frame_h = 640, 480
    bbox = (frame_w - 40, frame_h // 2 - 10, 20, 20)
    thread._track_target(bbox, frame_w, frame_h)
    assert thread.is_settled() is False
    time.sleep(0.06)
    assert thread.is_settled() is True


# パン中央値の実機要確認コメント/デフォルト値の確認


def test_gimbal_center_pan_default_is_85():
    thread = _make_gimbal()
    assert thread._gimbal_center_pan == 85.0
