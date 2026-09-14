import asyncio
import json

from PyQt6.QtCore import QThread, pyqtSignal

try:
    from websockets.asyncio.server import serve
    from websockets.exceptions import ConnectionClosed
except ImportError:
    serve = None
    ConnectionClosed = Exception


class RemoteControlServer(QThread):
    """WebSocket server that relays commands from a web browser to the rover."""

    command_received = pyqtSignal(str)
    status_changed = pyqtSignal(bool, bool)

    def __init__(self, host, port):
        super().__init__()
        self._host = host
        self._port = port
        self._running = False
        self._allowed = False
        self._rover_connected = False
        self._clients = set()
        self._loop = None
        self._server = None

    def run(self):
        if serve is None:
            return
        self._running = True
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._serve())

    async def _serve(self):
        self._server = await serve(
            self._on_connect, self._host, self._port
        )
        while self._running:
            await asyncio.sleep(0.5)

    async def _on_connect(self, websocket):
        self._clients.add(websocket)
        try:
            await self._send_status(websocket)
            async for raw in websocket:
                await self._handle_message(raw)
        except ConnectionClosed:
            pass
        finally:
            self._clients.discard(websocket)

    async def _handle_message(self, raw):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return
        if data.get("type") != "command":
            return
        command = data.get("command", "")
        if not command:
            return
        if not self._allowed:
            await self._broadcast({"type": "rejected", "reason": "not_allowed"})
            return
        self.command_received.emit(command)

    async def _send_status(self, websocket):
        msg = {
            "type": "status",
            "allowed": self._allowed,
            "rover_connected": self._rover_connected,
        }
        try:
            await websocket.send(json.dumps(msg))
        except ConnectionClosed:
            pass

    async def _broadcast(self, msg):
        payload = json.dumps(msg)
        stale = []
        for ws in list(self._clients):
            try:
                await ws.send(payload)
            except ConnectionClosed:
                stale.append(ws)
        for ws in stale:
            self._clients.discard(ws)

    def set_allowed(self, allowed):
        self._allowed = allowed
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._broadcast({
                    "type": "status",
                    "allowed": self._allowed,
                    "rover_connected": self._rover_connected,
                }),
                self._loop,
            )

    def set_rover_connected(self, connected):
        self._rover_connected = connected
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._broadcast({
                    "type": "status",
                    "allowed": self._allowed,
                    "rover_connected": self._rover_connected,
                }),
                self._loop,
            )

    def stop(self):
        self._running = False
        if self._server:
            self._server.close()
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        self.wait()
