import json

import cv2
import numpy as np

from esp32_mjpeg_detector.calibration import (
    CalibrationData,
    CharucoCalibrationSession,
    CoverageSample,
    append_calibration_history,
    calibration_from_dict,
    calibration_to_dict,
    coverage_sample_from_corners,
    error_quality_tier,
    format_history_entry,
    load_calibration_history,
    make_charuco_board,
    summarize_coverage,
)


def test_calibration_data_round_trips_json_payload():
    data = CalibrationData(
        camera_matrix=np.array([[1.0, 0.0, 2.0], [0.0, 1.5, 3.0], [0.0, 0.0, 1.0]]),
        distortion=np.array([0.1, -0.2, 0.0, 0.0, 0.01]),
        image_size=(640, 480),
        reprojection_error=0.25,
    )
    loaded = calibration_from_dict(calibration_to_dict(data))

    assert loaded.image_size == (640, 480)
    assert np.allclose(loaded.camera_matrix, data.camera_matrix)
    assert np.allclose(loaded.distortion, data.distortion)


def test_append_calibration_history_accumulates_past_runs(tmp_path):
    history_path = tmp_path / "calibration_history.json"
    data = CalibrationData(
        camera_matrix=np.eye(3),
        distortion=np.zeros(5),
        image_size=(640, 480),
        reprojection_error=0.5,
    )

    append_calibration_history(history_path, data, extra={"quality": 20})
    append_calibration_history(history_path, data, extra={"quality": 14})

    entries = json.loads(history_path.read_text(encoding="utf-8"))
    assert len(entries) == 2
    assert [entry["quality"] for entry in entries] == [20, 14]
    assert all("timestamp" in entry for entry in entries)


def test_load_calibration_history_returns_empty_list_when_file_missing(tmp_path):
    assert load_calibration_history(tmp_path / "nope.json") == []


def test_load_calibration_history_returns_appended_entries(tmp_path):
    history_path = tmp_path / "calibration_history.json"
    data = CalibrationData(camera_matrix=np.eye(3), distortion=np.zeros(5), image_size=(640, 480), reprojection_error=0.5)
    append_calibration_history(history_path, data, extra={"quality": 20})

    entries = load_calibration_history(history_path)

    assert len(entries) == 1
    assert entries[0]["quality"] == 20
    assert entries[0]["reprojection_error"] == 0.5


def test_format_history_entry_includes_timestamp_error_tier_and_size():
    entry = {
        "timestamp": "2026-09-09T12:00:00+00:00",
        "reprojection_error": 0.3,
        "image_size": [640, 480],
        "quality": 20,
    }

    text = format_history_entry(entry)

    assert "2026-09-09T12:00:00+00:00" in text
    assert "0.300px" in text
    assert "優秀" in text
    assert "640x480" in text
    assert "quality=20" in text


def test_coverage_sample_from_corners_computes_area_ratio_and_center():
    # A 100x100 board patch in a 640x480 frame, top-left corner
    corners = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=np.float32)

    sample = coverage_sample_from_corners(corners, (640, 480))

    assert sample.area_ratio == (100 * 100) / (640 * 480)
    assert sample.center_x == 50 / 640
    assert sample.center_y == 50 / 480


def test_error_quality_tier_thresholds():
    assert error_quality_tier(0.3) == "excellent"
    assert error_quality_tier(0.8) == "good"
    assert error_quality_tier(1.5) == "acceptable"
    assert error_quality_tier(3.0) == "poor"


def test_summarize_coverage_suggests_far_shots_when_all_close():
    samples = [CoverageSample(area_ratio=0.3, center_x=0.5, center_y=0.5) for _ in range(5)]

    tips = summarize_coverage(samples)

    assert any("遠い" in tip for tip in tips)


def test_summarize_coverage_suggests_close_shots_when_all_far():
    samples = [CoverageSample(area_ratio=0.01, center_x=0.5, center_y=0.5) for _ in range(5)]

    tips = summarize_coverage(samples)

    assert any("近い" in tip for tip in tips)


def test_summarize_coverage_suggests_edge_shots_when_all_centered():
    samples = [CoverageSample(area_ratio=0.1, center_x=0.5, center_y=0.5) for _ in range(5)]

    tips = summarize_coverage(samples)

    assert any("端" in tip or "四隅" in tip for tip in tips)


def test_summarize_coverage_reports_balanced_when_well_distributed():
    samples = [
        CoverageSample(area_ratio=0.3, center_x=0.5, center_y=0.5),
        CoverageSample(area_ratio=0.01, center_x=0.5, center_y=0.5),
        CoverageSample(area_ratio=0.1, center_x=0.05, center_y=0.05),
    ]

    tips = summarize_coverage(samples)

    assert tips == ["撮影バランス良好です。"]


def test_add_frame_records_a_coverage_sample_for_a_detected_board():
    board = make_charuco_board()
    frame = cv2.cvtColor(board.generateImage((640, 480)), cv2.COLOR_GRAY2BGR)
    session = CharucoCalibrationSession(board=board)

    corner_count = session.add_frame(frame)

    assert corner_count > 0
    assert len(session.coverage) == 1
    sample = session.coverage[0]
    assert 0.0 < sample.area_ratio <= 1.0
    assert 0.0 <= sample.center_x <= 1.0
    assert 0.0 <= sample.center_y <= 1.0
