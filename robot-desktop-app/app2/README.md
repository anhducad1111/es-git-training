# ESP32-CAM Live Object Detection

ESP32-CAM の既存 MJPEG ストリームを PyQt6 で表示し、最新フレームだけを物体検出へ渡す低遅延ビューアです。UIは英語表記ですが、このドキュメントは日本語で説明します。

## セットアップ

このプロジェクトは仮想環境を使わず、システムの Python にそのまま依存パッケージをインストールする構成です。

```powershell
cd C:\xampp\htdocs
pip install -r esp32_mjpeg_detector\requirements.txt
```

起動:

```powershell
python -m esp32_mjpeg_detector
```

**Host** 欄には ESP32 の IP（例 `192.168.4.1`）またはホスト名だけを入力し、**Resolution** で解像度を選びます。ESP32-Cam ファームウェアは `GET /{width}x{height}.mjpeg` という固定解像度エンドポイントを提供しており、`640x480`（VGA）が**25-30FPSで安定動作する推奨設定**です。`/stream` 任せ（Resolutionを`auto`にする）よりも、解像度を明示的に指定したほうが安定します。すでに `/stream` や `.mjpeg` を含む完全なURLをHost欄に入力した場合はそれがそのまま使われ、Resolutionの選択は無視されます。

**Quality**（0〜63、デフォルト14）は接続時に `GET /api/quality?val=` へ自動的に送られます。値を大きくするほど圧縮率が上がり1フレームのサイズが小さくなります。カメラは固定していても被写体の動きが激しいシーンではJPEGの1フレームあたりのサイズが急増しやすく、それがWi-Fi経由の送信を詰まらせて映像が不安定になることがあります。動きの激しい被写体で不安定さを感じる場合は、Qualityの数値を上げて（例: 20〜25）試してみてください。

### 任意: TurboJPEG によるデコード高速化

`requirements.txt` には `PyTurboJPEG` が含まれていますが、実体のデコード処理は `libjpeg-turbo` が提供する共有ライブラリ（Windowsでは `turbojpeg.dll` / `libturbojpeg.dll`）に依存します。

- Windowsでは [libjpeg-turbo の公式リリース](https://github.com/libjpeg-turbo/libjpeg-turbo/releases) からインストーラを入れてください
- `esp32_mjpeg_detector/workers.py` は以下の場所を自動で探します
  - `C:\libjpeg-turbo-gcc64\bin\libturbojpeg.dll`
  - `C:\libjpeg-turbo64\bin\turbojpeg.dll`
  - 上記以外の場所に入れた場合は環境変数 `TURBOJPEG_LIB_PATH` にDLLのフルパスを設定してください
- 見つからない・読み込みに失敗した場合は自動的に `cv2.imdecode` にフォールバックするため、未インストールでもアプリは正常に動作します

読み込めているか確認するには:

```powershell
python -c "from esp32_mjpeg_detector.workers import _turbojpeg; print(_turbojpeg)"
```

`None` 以外が出力されればTurboJPEGが有効です。

## 検出器

- `hog`: OpenCV 内蔵の人物検出。追加モデル不要。
- `none`: 映像表示のみ。
- `yolo`: Ultralytics YOLO。必要なら `pip install ultralytics` を実行し、初回にモデルがダウンロードされます。
- `aruco`: ArUco マーカーの ID・距離・左右／上下位置を表示します。`camera_calibration.json` があれば実寸距離を表示できます。「Object Detection」欄の **Marker Size** は、この単体ArUcoマーカーの実寸（一辺の長さ）です。下記のChArUcoキャリブレーションボードのマス目サイズとは別物なので注意してください。

ステータス表示（画面下部）は状態に応じて色が変わります。

| 色 | 意味 |
| --- | --- |
| 緑 | 受信中／保存成功など、正常な状態 |
| オレンジ | 接続中・再接続中・キャリブレーション収集中など、進行中の状態 |
| 赤 | エラー・失敗 |
| グレー | 切断中などの通常メッセージ |

## キャリブレーション

`aruco` を使う前に ESP32 の解像度を固定し、ストリームへ接続してから「Calibration」欄の **Start Calibration** を押します。

1. **Frames** で目標収集枚数を指定します（デフォルト20枚、5〜100枚）。開始すると収集完了までロックされます。
2. ChArUco ボードを画面内の好きな位置・角度・距離に構え、**Capture Frame** を押すと、その瞬間のフレームが1枚だけキャリブレーションに使われます。ボードを検出できなかった場合は警告が表示されるので、位置を調整してもう一度押してください。
3. ボードの位置を変えながら Capture Frame を繰り返します。目標枚数に達するとステータスが緑色になります（最低5枚あれば保存自体は可能です）。
4. 十分集まったら **Finish & Save** を押すと `camera_calibration.json` が保存され、次回の `aruco` 検出で距離（m）と左右・上下位置（m）が表示されるようになります。

**撮影のコツ**: ボード全体が画面に写っている必要はありません（コーナーが4点以上検出できれば1枚として採用されます）。むしろレンズ歪みは画面周辺ほど大きく出るため、中央だけでなく画面の端・隅にボードを寄せたショットも混ぜると精度が上がります。上下左右・斜め・近距離／遠距離など、できるだけ多様なシチュエーションで撮影してください。

ボードは [OpenCV の ChArUco 仕様](https://docs.opencv.org/4.x/d9/d6a/group__aruco.html)（5x7マス、1マス4cm、マーカー2cm、`DICT_4X4_50`）に合わせて印刷してください。ボード画像は次のコマンドで生成できます。

```powershell
python -m esp32_mjpeg_detector.generate_charuco_board
```

生成された `charuco_board.png` は拡大縮小せず、実寸（100%）で印刷してください。20cm x 28cmとA4用紙（21.0cm x 29.7cm）にほぼぴったりのサイズなので、印刷時は「用紙に合わせて拡大縮小」を必ずオフにしてください。

追従対象のマーカー（`aruco` 検出器で使う単体マーカー）は次で生成できます。A4 SVG の中央に ID 0 のマーカーを配置し、外周を含む実寸 50 mm になります。

```powershell
python -m esp32_mjpeg_detector.generate_aruco_marker
```

生成された `aruco_marker_id0_a4.svg` を A4・倍率 100%（用紙に合わせる無効）で印刷してください。

## アーキテクチャ・低遅延化の工夫

- キャプチャ（ネットワーク受信）、デコード、推論、GUI表示はそれぞれ別スレッドです。
  - ネットワーク受信スレッドはMJPEGストリームの読み取りとパースだけを行い、デコードは一切行いません。デコード待ちで受信がブロックされないため、ソケット側にデータが溜まりにくくなっています。
  - デコード専用スレッドは、その時点で一番新しいJPEGだけを取り出してデコードします。受信が一時的に先行しても、古いフレームのデコードに時間を使わず、常に最新のフレームを処理します。
  - 各スレッド間の受け渡しは容量1の latest-only スロット（`LatestFrame`）なので、推論が追いつかない場合でもライブ映像は止まらず、古い映像も蓄積しません。
- ネットワーク受信は `response.read(n)` ではなく `response.fp.read1(n)` を使っています。`read(n)` は指定バイト数に達するまでブロックし続ける仕様（`io.BufferedReader`）のため、1フレームより大きいサイズを指定すると複数フレーム分のデータが溜まるまで待たされ、ブラウザに比べて体感速度が大きく落ちる原因になっていました。`read1(n)` は届いているデータをブロックせずすぐ返すため、ブラウザと同等の反応速度になります（`Transfer-Encoding: chunked` の場合のみ通常の `read()` にフォールバックします）。
- 表示側では `cv2.cvtColor(BGR2RGB)` を行わず、`QImage.Format_BGR888` でBGRのまま描画することで色変換の負荷を削減しています。

## トラブルシューティング

- 接続できない場合は PC と ESP32 が同じ Wi-Fi にいるか、ブラウザで `/stream` が開けるか確認してください。
- 遅延が大きい場合は ESP32 側の解像度を `320x240.mjpeg` または `640x480.mjpeg` に下げ、YOLO の代わりに HOG を選択してください。上記のTurboJPEG導入も効果があります。
- 終了時は「Disconnect」またはウィンドウを閉じます。ワーカーは自動的に停止します。

## テスト

```powershell
cd C:\xampp\htdocs
pytest esp32_mjpeg_detector\tests -q
```
