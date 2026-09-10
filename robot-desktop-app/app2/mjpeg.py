from __future__ import annotations

import re


class MjpegParser:
    """Incrementally extracts JPEG payloads from an ESP32 multipart stream."""

    _length_re = re.compile(rb"(?:^|\r\n)content-length\s*:\s*(\d+)\s*(?:\r\n|$)", re.I)

    def __init__(self, max_frame_bytes: int = 8 * 1024 * 1024) -> None:
        self.max_frame_bytes = max_frame_bytes
        self._buffer = bytearray()
        self._expected = None

    def reset(self) -> None:
        self._buffer.clear()
        self._expected = None

    def feed(self, data: bytes) -> list[bytes]:
        self._buffer.extend(data)
        frames: list[bytes] = []
        while True:
            if self._expected is None:
                header_end = self._buffer.find(b"\r\n\r\n")
                if header_end < 0:
                    if len(self._buffer) > 64 * 1024:
                        self._buffer = self._buffer[-4096:]
                    break
                header = bytes(self._buffer[: header_end + 4])
                del self._buffer[: header_end + 4]
                match = self._length_re.search(header)
                if not match:
                    continue
                self._expected = int(match.group(1))
                if not 0 < self._expected <= self.max_frame_bytes:
                    self._expected = None
                    continue
            if len(self._buffer) < self._expected:
                break
            frames.append(bytes(self._buffer[: self._expected]))
            del self._buffer[: self._expected]
            self._expected = None
            while self._buffer.startswith(b"\r\n"):
                del self._buffer[:2]
        return frames
