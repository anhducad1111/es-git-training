# 実機確認手順書: FOLLOW TUNINGタブ（追従パラメータのライブ調整）

対象コミット: DEBUGタブを2タブ構成(CALIBRATION / FOLLOW TUNING)に分割、
FollowConfigパラメータをスライダーで即時調整できるようにした変更
（`views/debug_view.py` 変更のみ、他ファイルへの変更なし）

## 事前確認（自動テスト済み・実機不要）

- `pytest tests/` 75件 全てpass（このタブ自体はロジックを持たないため専用のユニットテストは無し）
- `RoverTeleopApp()` 生成時、DEBUGタブが `CALIBRATION` / `FOLLOW TUNING` の2タブ構成になっていることを確認済み
- スライダーの値変更が `FollowController.config` の該当属性に書き込まれることをフェイクオブジェクトで確認済み（`turn_speed=210`, `distance_band=0.15` で検証）

## 実機確認手順

### 1. タブ切り替え

1. `python main.py` でアプリを起動し、サイドバーのDEBUGボタンを押す
2. 上部に `CALIBRATION` / `FOLLOW TUNING` の2タブが表示されることを確認
3. 両タブを行き来しても、以前実装したCALIBRATION側（旋回テスト・前進テスト・履歴テーブル）が問題なく動作すること（前回手順書の再確認は不要、タブに移しただけで中身は変えていません）

### 2. follow mode開始前のスライダー表示

1. follow modeを開始する前にFOLLOW TUNINGタブを開く
2. 7つのスライダー（turn_speed, max_follow_pwm, min_pwm, spin_pulse_on_sec, straight_command_w_threshold, distance_band, approach_slowdown_dist）が、`follow_controller.FollowConfig`の現在のデフォルト値（turn_speed=190, max_follow_pwm=200, min_pwm=180, spin_pulse_on_sec=0.08, straight_command_w_threshold=10, distance_band=0.075, approach_slowdown_dist=1.0）で初期表示されることを確認
3. この時点でスライダーを動かしてもエラーにならないこと（follow controllerがまだ存在しないため、ログに反映メッセージは出ないはず）

### 3. follow mode実行中のライブ反映

1. follow modeを開始（既存の手順通り、対象車を検出させる）
2. FOLLOW TUNINGタブでいずれかのスライダー（例: `turn_speed`）を動かす
3. ログパネルに `follow config更新: turn_speed=...` が出ることを確認
4. その後の旋回動作の速さが変わる（体感でよい）ことを確認
5. 同様に `distance_band` や `max_follow_pwm` も動かし、追従の距離帯・速度の挙動が変わることを確認

**特に確認したい点**: これまで一連のやり取りで手動で書き換えてきた値（turn_speed, max_follow_pwm, min_pwm, spin_pulse_on_sec, straight_command_w_threshold）を、コード変更・アプリ再起動なしにその場で追い込めるか。使い勝手に問題があれば教えてください（スライダーの刻み幅・範囲が実用に合わない等）。

## 問題があった場合

上記のどこかで期待通りに動かなかった場合、該当する手順番号と実際の挙動を教えてください。
