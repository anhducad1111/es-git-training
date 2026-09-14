from esp32_mjpeg_detector.app import (
    AppConfig,
    camera_pose_suffix,
    capture_filename_suffix,
    format_marker_panel,
    normalize_url,
    yaw_suffix,
)
from esp32_mjpeg_detector.marker_tracking import MarkerPose, MarkerTrackResult


def test_normalize_url_adds_stream_endpoint_to_host():
    assert normalize_url("192.168.4.1") == "http://192.168.4.1/stream"
    assert normalize_url("http://192.168.4.1/640x480.mjpeg") == "http://192.168.4.1/640x480.mjpeg"


def test_app_config_defaults_to_hog_detection():
    config = AppConfig()

    assert config.detector_kind == "hog"
    assert config.detection_enabled is True


def test_format_marker_panel_shows_no_marker_when_nothing_detected():
    assert format_marker_panel(MarkerTrackResult(status="none")) == "Marker: 検出なし"


def test_format_marker_panel_shows_high_precision_distance_and_xy_for_one_marker():
    pose = MarkerPose(x_m=0.123456789, y_m=-0.045678912, z_m=0.4, distance_m=0.412345678, yaw_deg=12.3, rvec=None, tvec=None)
    result = MarkerTrackResult(status="single", label="marker 0", pose=pose, stale=False)

    text = format_marker_panel(result)

    assert "marker 0" in text
    assert "0.412346" in text
    assert "+0.123457" in text
    assert "-0.045679" in text
    assert "12.3" in text
    assert "前回検出値" not in text


def test_format_marker_panel_flags_a_held_stale_pose():
    pose = MarkerPose(0.1, 0.2, 0.4, 0.4, 5.0, None, None)
    result = MarkerTrackResult(status="single", label="marker 0", pose=pose, stale=True)

    assert "前回検出値" in format_marker_panel(result)


def test_format_marker_panel_reports_multiple_markers_without_picking_one():
    assert "2" in format_marker_panel(MarkerTrackResult(status="multiple", count=2))


def test_format_marker_panel_flags_missing_calibration():
    assert "キャリブレーション" in format_marker_panel(MarkerTrackResult(status="uncalibrated"))


def test_capture_filename_suffix_prefers_measured_distance_over_manual():
    pose = MarkerPose(x_m=0.1, y_m=0.2, z_m=0.412, distance_m=0.412, yaw_deg=12.3, rvec=None, tvec=None)
    result = MarkerTrackResult(status="single", label="marker 0", pose=pose)

    assert capture_filename_suffix(result, manual_distance_m=9.999) == "_d0.412"


def test_capture_filename_suffix_falls_back_to_manual_distance_without_a_measurement():
    assert capture_filename_suffix(MarkerTrackResult(status="none"), manual_distance_m=1.5) == "_d1.500"
    assert capture_filename_suffix(MarkerTrackResult(status="multiple", count=2), manual_distance_m=1.5) == "_d1.500"


def test_yaw_suffix_is_manually_entered_not_derived_from_marker_pose():
    assert yaw_suffix(12.3) == "_yaw+12.3"
    assert yaw_suffix(-5.6) == "_yaw-5.6"
    assert yaw_suffix(0) == "_yaw+0.0"


def test_camera_pose_suffix_embeds_pan_and_tilt_zero_padded():
    assert camera_pose_suffix(pan=90, tilt=45) == "_pan090_tilt045"
    assert camera_pose_suffix(pan=0, tilt=180) == "_pan000_tilt180"
