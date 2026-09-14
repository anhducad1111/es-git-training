from __future__ import annotations

import re
from pathlib import Path

import cv2
import numpy as np


def next_capture_path(directory: str | Path, prefix: str = "capture", ext: str = ".jpg", suffix: str = "") -> Path:
    """Next sequential filename in directory, continuing past whatever is already
    there so re-running a capture session never overwrites earlier photos.

    Existing filenames may carry their own metadata suffix (e.g. distance/yaw
    embedded for ML training labels), so numbering is read from the leading
    digits right after the prefix rather than the whole stem.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    number_pattern = re.compile(rf"^{re.escape(prefix)}_(\d+)")
    max_index = 0
    for existing in directory.glob(f"{prefix}_*{ext}"):
        match = number_pattern.match(existing.stem)
        if match:
            max_index = max(max_index, int(match.group(1)))
    return directory / f"{prefix}_{max_index + 1:04d}{suffix}{ext}"


def save_capture(frame: np.ndarray, directory: str | Path, prefix: str = "capture", ext: str = ".jpg", suffix: str = "") -> Path:
    path = next_capture_path(directory, prefix, ext, suffix)
    cv2.imwrite(str(path), frame)
    return path
