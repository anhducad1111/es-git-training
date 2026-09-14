import cv2
import numpy as np

from esp32_mjpeg_detector.capture import next_capture_path, save_capture


def test_next_capture_path_starts_at_0001_for_empty_directory(tmp_path):
    path = next_capture_path(tmp_path)

    assert path == tmp_path / "capture_0001.jpg"


def test_next_capture_path_continues_after_existing_files(tmp_path):
    (tmp_path / "capture_0001.jpg").touch()
    (tmp_path / "capture_0007.jpg").touch()

    path = next_capture_path(tmp_path)

    assert path == tmp_path / "capture_0008.jpg"


def test_next_capture_path_creates_missing_directory(tmp_path):
    directory = tmp_path / "captures"

    path = next_capture_path(directory)

    assert directory.is_dir()
    assert path == directory / "capture_0001.jpg"


def test_save_capture_writes_an_image_file_and_returns_its_path(tmp_path):
    frame = np.zeros((4, 6, 3), dtype=np.uint8)

    path = save_capture(frame, tmp_path)

    assert path.exists()
    saved = cv2.imread(str(path))
    assert saved.shape == (4, 6, 3)


def test_save_capture_increments_across_calls(tmp_path):
    frame = np.zeros((4, 6, 3), dtype=np.uint8)

    first = save_capture(frame, tmp_path)
    second = save_capture(frame, tmp_path)

    assert first.name == "capture_0001.jpg"
    assert second.name == "capture_0002.jpg"


def test_next_capture_path_with_suffix(tmp_path):
    path = next_capture_path(tmp_path, suffix="_d0.412_yaw+12.3")

    assert path.name == "capture_0001_d0.412_yaw+12.3.jpg"


def test_next_capture_path_numbering_continues_past_files_that_have_a_suffix(tmp_path):
    (tmp_path / "capture_0001_d0.412_yaw+12.3.jpg").touch()

    path = next_capture_path(tmp_path, suffix="_d0.500_yaw-5.0")

    assert path.name == "capture_0002_d0.500_yaw-5.0.jpg"


def test_save_capture_writes_metadata_suffix_into_filename(tmp_path):
    frame = np.zeros((4, 6, 3), dtype=np.uint8)

    path = save_capture(frame, tmp_path, suffix="_d0.412_yaw+12.3")

    assert path.name == "capture_0001_d0.412_yaw+12.3.jpg"
    assert path.exists()
