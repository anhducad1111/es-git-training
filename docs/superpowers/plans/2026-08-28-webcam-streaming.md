# Webcam Streaming to Desktop App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stream a laptop's webcam into a new panel in the `haru-app2` PyQt6 desktop app over WebRTC, with sub-100ms latency on a shared LAN.

**Architecture:** A small standalone `aiohttp` server (`webcam-stream/sender.py`) runs on the laptop, exposing `POST /offer` to exchange WebRTC SDP with callers and attaching a webcam track to the resulting `RTCPeerConnection` (the aiortc offer/answer server pattern). `haru-app2` gets a new `WebcamWorker(QThread)` (in `webrtc_client.py`) that creates its own `RTCPeerConnection`, `POST`s an SDP offer to the sender's URL, and emits decoded video frames as `QImage` via a Qt signal for a new "Webcam" panel to display. Once negotiated, video flows peer-to-peer over UDP — the HTTP API is used only for the one-time signaling handshake.

**Tech Stack:** Python 3, `aiortc`, `aiohttp`, `av` (PyAV), PyQt6 (existing), `pytest` + `pytest-asyncio` (new test infra — this is the first automated test suite in this repo), `numpy` (test-only, synthetic video frames).

**Spec:** `docs/superpowers/specs/2026-08-28-webcam-streaming-design.md`

## Global Constraints

- Laptop and desktop app are on the same LAN — no STUN/TURN, ICE uses host candidates only.
- No authentication beyond what WebRTC (SRTP) provides by default — trusted-LAN assumption.
- Audio is out of scope.
- Multiple simultaneous viewers of one sender is out of scope.
- Signaling must be a new, dedicated small server — do not touch the Sensor Dashboard PHP backend.
- The webcam video panel lives inside `haru-app2`, not a separate app.

---

## Task 1: Signaling + media sender (`webcam-stream/sender.py`)

**Files:**
- Create: `webcam-stream/sender.py`
- Create: `webcam-stream/tests/test_sender.py`
- Create: `webcam-stream/README.md`

**Interfaces:**
- Produces: `build_app(track_factory)` — `track_factory` is a zero-argument callable returning an `aiortc.mediastreams.MediaStreamTrack`; returns an `aiohttp.web.Application` with `POST /offer` registered. Consumed by Task 1's own tests only (not reused by `haru-app2`, which talks to the running server over HTTP, not via import).
- Produces: `create_camera_track(device_name: str)` — real webcam track used by `main()`, not covered by automated tests (no camera in CI).

- [ ] **Step 1: Install dependencies**

Run from the repo root:

```bash
pip install aiortc aiohttp av numpy pytest pytest-asyncio
```

- [ ] **Step 2: Create the test scaffolding**

Create `webcam-stream/tests/__init__.py` (empty file) and `webcam-stream/pytest.ini`:

```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 3: Write the failing test**

Create `webcam-stream/tests/test_sender.py`:

```python
import asyncio
import sys
from pathlib import Path

import numpy as np
from aiohttp.test_utils import TestClient, TestServer
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sender import build_app


class ColorFrameTrack(VideoStreamTrack):
  def __init__(self, width=64, height=48):
    super().__init__()
    self.width = width
    self.height = height

  async def recv(self):
    pts, time_base = await self.next_timestamp()
    array = np.zeros((self.height, self.width, 3), dtype=np.uint8)
    array[:, :, 1] = 255
    frame = VideoFrame.from_ndarray(array, format="rgb24")
    frame.pts = pts
    frame.time_base = time_base
    return frame


async def _capture_first_frame(track, future):
  frame = await track.recv()
  if not future.done():
    future.set_result(frame)


async def test_offer_endpoint_streams_video_track_to_client():
  app = build_app(track_factory=lambda: ColorFrameTrack())
  server = TestServer(app)
  client = TestClient(server)
  await client.start_server()

  client_pc = RTCPeerConnection()
  client_pc.addTransceiver("video", direction="recvonly")
  received = asyncio.get_event_loop().create_future()

  @client_pc.on("track")
  def on_track(track):
    asyncio.ensure_future(_capture_first_frame(track, received))

  offer = await client_pc.createOffer()
  await client_pc.setLocalDescription(offer)

  response = await client.post("/offer", json={
      "sdp": client_pc.localDescription.sdp,
      "type": client_pc.localDescription.type,
  })
  assert response.status == 200
  data = await response.json()
  answer = RTCSessionDescription(sdp=data["sdp"], type=data["type"])
  await client_pc.setRemoteDescription(answer)

  frame = await asyncio.wait_for(received, timeout=5)
  assert frame.width == 64
  assert frame.height == 48

  await client_pc.close()
  await client.close()
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `cd webcam-stream && python -m pytest tests/test_sender.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sender'`

- [ ] **Step 5: Implement `sender.py`**

Create `webcam-stream/sender.py`:

```python
import argparse
import asyncio
import functools

from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer


def create_camera_track(device_name):
  player = MediaPlayer(f"video={device_name}", format="dshow")
  if player.video is None:
    raise RuntimeError(f"No video track available from device '{device_name}'")
  return player.video


async def offer(request):
  params = await request.json()
  pc = RTCPeerConnection()
  request.app["pcs"].add(pc)

  @pc.on("connectionstatechange")
  async def on_connectionstatechange():
    if pc.connectionState in ("failed", "closed"):
      await pc.close()
      request.app["pcs"].discard(pc)

  track = request.app["track_factory"]()
  pc.addTrack(track)

  offer_desc = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
  await pc.setRemoteDescription(offer_desc)
  answer = await pc.createAnswer()
  await pc.setLocalDescription(answer)

  return web.json_response({
      "sdp": pc.localDescription.sdp,
      "type": pc.localDescription.type,
  })


async def on_shutdown(app):
  await asyncio.gather(*(pc.close() for pc in app["pcs"]))
  app["pcs"].clear()


def build_app(track_factory):
  app = web.Application()
  app["pcs"] = set()
  app["track_factory"] = track_factory
  app.router.add_post("/offer", offer)
  app.on_shutdown.append(on_shutdown)
  return app


def main():
  parser = argparse.ArgumentParser(description="WebRTC webcam signaling/media server")
  parser.add_argument("--device", default="Integrated Camera", help="DirectShow video device name")
  parser.add_argument("--port", type=int, default=8080)
  args = parser.parse_args()

  app = build_app(functools.partial(create_camera_track, args.device))
  web.run_app(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
  main()
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `cd webcam-stream && python -m pytest tests/test_sender.py -v`
Expected: PASS

- [ ] **Step 7: Write the sender README**

Create `webcam-stream/README.md`:

```markdown
# Webcam Stream Sender

Runs on the laptop that owns the webcam. Exposes a WebRTC signaling
endpoint (`POST /offer`) that `haru-app2`'s Webcam panel connects to.
Once negotiated, video flows directly peer-to-peer over UDP — this
HTTP server is only used for the initial handshake.

## Install

```bash
pip install aiortc aiohttp av
```

## Run

```bash
python sender.py --device "Integrated Camera" --port 8080
```

Use `ffmpeg -list_devices true -f dshow -i dummy` to list available
DirectShow device names on Windows if the default doesn't match your
webcam.

In `haru-app2`'s Webcam panel, enter `http://<this-machine's-LAN-IP>:8080/offer`
and click Start.

## Test

```bash
pip install pytest pytest-asyncio numpy
python -m pytest tests/ -v
```
```

- [ ] **Step 8: Commit**

```bash
git add webcam-stream/sender.py webcam-stream/tests/ webcam-stream/pytest.ini webcam-stream/README.md
git commit -m "feat: add WebRTC webcam signaling/media sender"
```

---

## Task 2: Desktop config field for the sender URL

**Files:**
- Modify: `haru-app2/config.py`
- Create: `haru-app2/tests/test_config.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `DEFAULT_CONFIG["webcam_url"]` (default `""`), read by Task 4's UI panel via `load_config()`/`save_config()` (unchanged signatures).

- [ ] **Step 1: Set up test infra for haru-app2**

Create `haru-app2/tests/__init__.py` (empty file) and `haru-app2/pytest.ini`:

```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 2: Write the failing test**

Create `haru-app2/tests/test_config.py`:

```python
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config as config_module


def test_load_config_fills_in_missing_webcam_url(tmp_path, monkeypatch):
  config_file = tmp_path / "config.json"
  config_file.write_text(json.dumps({"api_url": "http://example.test"}))
  monkeypatch.setattr(config_module, "CONFIG_FILE", str(config_file))

  loaded = config_module.load_config()

  assert loaded["webcam_url"] == ""
  assert loaded["api_url"] == "http://example.test"


def test_save_config_persists_webcam_url(tmp_path, monkeypatch):
  config_file = tmp_path / "config.json"
  monkeypatch.setattr(config_module, "CONFIG_FILE", str(config_file))

  config_module.save_config({"webcam_url": "http://192.168.1.50:8080/offer"})

  saved = json.loads(config_file.read_text())
  assert saved["webcam_url"] == "http://192.168.1.50:8080/offer"
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `cd haru-app2 && python -m pytest tests/test_config.py -v`
Expected: FAIL on `test_load_config_fills_in_missing_webcam_url` with `KeyError: 'webcam_url'`

- [ ] **Step 4: Add the field to `config.py`**

In `haru-app2/config.py`, modify `DEFAULT_CONFIG`:

```python
DEFAULT_CONFIG = {
    "api_url": "https://iotdigi.io.vn/es-git-training/sensor-dashboard/api/get-data.php",
    "gemini_api_key": "",
    "center_charts": {},
    "center_charts_hidden": [],
    "custom_charts": {},
    "custom_charts_normalize": {},
    "webcam_url": "",
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd haru-app2 && python -m pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add haru-app2/config.py haru-app2/tests/ haru-app2/pytest.ini
git commit -m "feat: add webcam_url field to haru-app2 config"
```

---

## Task 3: WebRTC client — negotiation logic and QThread worker

**Files:**
- Create: `haru-app2/webrtc_client.py`
- Create: `haru-app2/tests/test_webrtc_client.py`

**Interfaces:**
- Consumes: nothing new (standalone module; does not import `webcam-stream/sender.py`).
- Produces:
  - `async def negotiate(offer_url: str, pc: aiortc.RTCPeerConnection, session: aiohttp.ClientSession | None = None) -> None` — adds a recvonly video transceiver to `pc`, posts an SDP offer to `offer_url`, and sets the returned SDP answer as `pc`'s remote description. Raises on HTTP/network failure.
  - `class WebcamWorker(PyQt6.QtCore.QThread)` with:
    - `__init__(self, offer_url: str)`
    - `frame_ready = pyqtSignal(QImage)`
    - `connection_state_changed = pyqtSignal(str)` — emits `"connected"`, `"disconnected"`, `"failed"`, or `"closed"`
    - `stop(self) -> None`
  - Consumed by Task 4's UI panel in `app.py`.

- [ ] **Step 1: Write the failing test for `negotiate()`**

Create `haru-app2/tests/test_webrtc_client.py`:

```python
import sys
from pathlib import Path

from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from webrtc_client import negotiate


async def _run_fake_offer_server(responder_pc):
  async def offer_handler(request):
    params = await request.json()
    await responder_pc.setRemoteDescription(
        RTCSessionDescription(sdp=params["sdp"], type=params["type"]))
    answer = await responder_pc.createAnswer()
    await responder_pc.setLocalDescription(answer)
    return web.json_response({
        "sdp": responder_pc.localDescription.sdp,
        "type": responder_pc.localDescription.type,
    })

  app = web.Application()
  app.router.add_post("/offer", offer_handler)
  runner = web.AppRunner(app)
  await runner.setup()
  site = web.TCPSite(runner, "127.0.0.1", 8765)
  await site.start()
  return runner


async def test_negotiate_sets_remote_description_from_answer():
  responder_pc = RTCPeerConnection()
  responder_pc.addTransceiver("video", direction="sendonly")
  runner = await _run_fake_offer_server(responder_pc)

  pc = RTCPeerConnection()
  try:
    await negotiate("http://127.0.0.1:8765/offer", pc)

    assert pc.remoteDescription is not None
    assert pc.remoteDescription.type == "answer"
    assert pc.localDescription is not None
    assert pc.localDescription.type == "offer"
  finally:
    await pc.close()
    await responder_pc.close()
    await runner.cleanup()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd haru-app2 && python -m pytest tests/test_webrtc_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'webrtc_client'`

- [ ] **Step 3: Implement `negotiate()` and `WebcamWorker`**

Create `haru-app2/webrtc_client.py`:

```python
import asyncio

import aiohttp
from aiortc import RTCPeerConnection, RTCSessionDescription
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage


async def negotiate(offer_url, pc, session=None):
  pc.addTransceiver("video", direction="recvonly")
  offer = await pc.createOffer()
  await pc.setLocalDescription(offer)

  own_session = session is None
  if own_session:
    session = aiohttp.ClientSession()
  try:
    async with session.post(
        offer_url,
        json={"sdp": pc.localDescription.sdp, "type": pc.localDescription.type},
        timeout=aiohttp.ClientTimeout(total=10),
    ) as response:
      response.raise_for_status()
      data = await response.json()
  finally:
    if own_session:
      await session.close()

  answer = RTCSessionDescription(sdp=data["sdp"], type=data["type"])
  await pc.setRemoteDescription(answer)


def frame_to_qimage(frame):
  array = frame.to_ndarray(format="rgb24")
  height, width, _ = array.shape
  bytes_per_line = 3 * width
  image = QImage(array.tobytes(), width, height, bytes_per_line, QImage.Format.Format_RGB888)
  return image.copy()


class WebcamWorker(QThread):
  frame_ready = pyqtSignal(QImage)
  connection_state_changed = pyqtSignal(str)

  def __init__(self, offer_url):
    super().__init__()
    self.offer_url = offer_url
    self._pc = None
    self._stop_requested = False

  def run(self):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
      loop.run_until_complete(self._connect_and_receive())
    finally:
      loop.close()

  async def _connect_and_receive(self):
    self._pc = RTCPeerConnection()

    @self._pc.on("connectionstatechange")
    async def on_connectionstatechange():
      self.connection_state_changed.emit(self._pc.connectionState)

    @self._pc.on("track")
    def on_track(track):
      asyncio.ensure_future(self._consume_track(track))

    try:
      await negotiate(self.offer_url, self._pc)
    except Exception:
      self.connection_state_changed.emit("failed")
      return

    while not self._stop_requested:
      await asyncio.sleep(0.1)
    await self._pc.close()

  async def _consume_track(self, track):
    while not self._stop_requested:
      try:
        frame = await track.recv()
      except Exception:
        break
      self.frame_ready.emit(frame_to_qimage(frame))

  def stop(self):
    self._stop_requested = True
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd haru-app2 && python -m pytest tests/test_webrtc_client.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add haru-app2/webrtc_client.py haru-app2/tests/test_webrtc_client.py
git commit -m "feat: add WebRTC negotiation logic and WebcamWorker QThread"
```

---

## Task 4: Webcam panel in `haru-app2`'s UI

**Files:**
- Modify: `haru-app2/app.py`
- Modify: `haru-app2/README.md`

**Interfaces:**
- Consumes: `webrtc_client.WebcamWorker(offer_url)` with `frame_ready` (`QImage`) and `connection_state_changed` (`str`) signals and `.stop()` (from Task 3); `config.load_config()`/`save_config()` with the `webcam_url` key (from Task 2).
- Produces: nothing consumed by later tasks (final task in this plan).

- [ ] **Step 1: Add the Webcam panel to `init_ui()`**

In `haru-app2/app.py`, add the import near the top (alongside the existing `from worker import Worker` line):

```python
from webrtc_client import WebcamWorker
```

In `init_ui()`, after the block that builds `far_right_layout` and before `self.top_layout.addLayout(left_layout, stretch=1)`, add a new panel to `left_layout` (so it sits under the sensor cards, consistent with the existing left-column stacking):

```python
    webcam_group = QGroupBox("Webcam")
    webcam_group.setStyleSheet(GROUP_BOX_STYLE)
    webcam_layout = QVBoxLayout()

    self.webcam_url_entry = QLineEdit()
    self.webcam_url_entry.setPlaceholderText("http://<laptop-ip>:8080/offer")
    webcam_layout.addWidget(QLabel("Sender URL:"))
    webcam_layout.addWidget(self.webcam_url_entry)

    self.webcam_toggle_btn = QPushButton("Start Webcam")
    self.webcam_toggle_btn.setStyleSheet(
        "background-color: #4CAF50; color: white; font-weight: bold; padding: 5px 15px; border-radius: 4px;"
    )
    self.webcam_toggle_btn.clicked.connect(self.toggle_webcam)
    webcam_layout.addWidget(self.webcam_toggle_btn)

    self.webcam_status_label = QLabel("Disconnected")
    self.webcam_status_label.setStyleSheet("color: #FF5252; font-weight: bold;")
    webcam_layout.addWidget(self.webcam_status_label)

    self.webcam_view = QLabel()
    self.webcam_view.setMinimumSize(240, 180)
    self.webcam_view.setStyleSheet("background-color: #191A1E; border: 1px solid #333;")
    self.webcam_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.webcam_view.setText("No signal")
    webcam_layout.addWidget(self.webcam_view)

    webcam_group.setLayout(webcam_layout)
    left_layout.addWidget(webcam_group)

    self._webcam_worker = None
```

- [ ] **Step 2: Load and save the webcam URL with the rest of the config**

In `load_saved_config()`, alongside the existing `self.url_entry.setText(...)` line, add:

```python
    self.webcam_url_entry.setText(self._config.get("webcam_url", ""))
```

In `save_current_config()`, alongside the existing `self._config["api_url"] = ...` line, add:

```python
    self._config["webcam_url"] = self.webcam_url_entry.text().strip()
```

- [ ] **Step 3: Add the start/stop and frame-handling methods**

Add these methods to `SensorDashboardApp` (near `toggle_polling`, since it's the closest existing analog):

```python
  def toggle_webcam(self):
    if self._webcam_worker is not None:
      self._webcam_worker.stop()
      self._webcam_worker.wait()
      self._webcam_worker = None
      self.webcam_toggle_btn.setText("Start Webcam")
      self.webcam_toggle_btn.setStyleSheet(
          "background-color: #4CAF50; color: white; font-weight: bold; padding: 5px 15px; border-radius: 4px;"
      )
      self.webcam_status_label.setText("Disconnected")
      self.webcam_status_label.setStyleSheet("color: #FF5252; font-weight: bold;")
      self.webcam_view.setText("No signal")
      self.webcam_view.setPixmap(QPixmap())
      self.append_log("Webcam stopped")
      return

    offer_url = self.webcam_url_entry.text().strip()
    if not offer_url:
      self.append_log("ERROR | Webcam sender URL not set")
      return

    self._webcam_worker = WebcamWorker(offer_url)
    self._webcam_worker.frame_ready.connect(self.on_webcam_frame)
    self._webcam_worker.connection_state_changed.connect(self.on_webcam_state_changed)
    self._webcam_worker.start()
    self.webcam_toggle_btn.setText("Stop Webcam")
    self.webcam_toggle_btn.setStyleSheet(
        "background-color: #F44336; color: white; font-weight: bold; padding: 5px 15px; border-radius: 4px;"
    )
    self.append_log(f"Webcam connecting to {offer_url}")

  def on_webcam_frame(self, image):
    pixmap = QPixmap.fromImage(image).scaled(
        self.webcam_view.width(), self.webcam_view.height(),
        Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation,
    )
    self.webcam_view.setPixmap(pixmap)

  def on_webcam_state_changed(self, state):
    if state == "connected":
      self.webcam_status_label.setText("Connected")
      self.webcam_status_label.setStyleSheet("color: #69F0AE; font-weight: bold;")
    elif state == "failed":
      self.webcam_status_label.setText("Failed")
      self.webcam_status_label.setStyleSheet("color: #FF5252; font-weight: bold;")
    else:
      self.webcam_status_label.setText(state.capitalize())
      self.webcam_status_label.setStyleSheet("color: #FF5252; font-weight: bold;")
    self.append_log(f"Webcam state: {state}")
```

- [ ] **Step 4: Add the missing `QPixmap` import**

In `haru-app2/app.py`, update the `PyQt6.QtGui` import line to include `QPixmap`:

```python
from PyQt6.QtGui import QKeyEvent, QPixmap
```

- [ ] **Step 5: Manually verify end-to-end**

On the laptop:

```bash
cd webcam-stream
python sender.py --device "Integrated Camera" --port 8080
```

On the desktop machine:

```bash
cd haru-app2
python main.py
```

In the app: enter `http://<laptop-LAN-IP>:8080/offer` in the Webcam panel's Sender URL field, click "Start Webcam". Confirm:
- Status label shows "Connected" within a few seconds.
- Live video appears in the panel and looks close to real-time (wave a hand in front of the camera and check the display keeps up).
- Clicking "Stop Webcam" clears the view and shows "No signal" / "Disconnected".
- Entering a wrong URL and clicking Start shows "Failed" in the status label and an `ERROR`/`FAIL`-style line in the log panel.

- [ ] **Step 6: Update `haru-app2/README.md`**

Add a new subsection under `## Features` (after `### Data Analysis`):

```markdown
### Webcam Panel

**Live Video:**
- Displays a live WebRTC video feed from a laptop running
  `webcam-stream/sender.py` on the same LAN.
- Enter the sender's URL (`http://<laptop-ip>:8080/offer`) and click
  "Start Webcam". Video renders directly in the panel once connected.
- Connection setup is a one-time HTTP SDP exchange; the actual video
  stream flows peer-to-peer over UDP for low latency (~sub-100ms on a
  typical LAN).
- Click "Stop Webcam" to disconnect.
```

Add to the `Package Purposes` list under `## Dependencies`:

```markdown
- `aiortc`: WebRTC peer connections and media handling
- `aiohttp`: HTTP client used to POST the SDP offer to the sender
```

And update the `pip install` line:

```bash
pip install PyQt6 requests matplotlib google-genai aiortc aiohttp av
```

- [ ] **Step 7: Commit**

```bash
git add haru-app2/app.py haru-app2/README.md
git commit -m "feat: add Webcam panel to haru-app2, wired to WebcamWorker"
```
