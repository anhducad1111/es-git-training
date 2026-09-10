from esp32_mjpeg_detector.generate_aruco_marker import build_marker_pdf, build_marker_svg, marker_rects_mm


def test_marker_svg_is_a4_with_50mm_marker():
    svg = build_marker_svg(marker_id=0, marker_mm=50)

    assert 'width="210mm"' in svg
    assert 'height="297mm"' in svg
    assert 'data-marker-width="50mm"' in svg
    assert 'data-marker-height="50mm"' in svg


def test_marker_pdf_is_a4_sized_in_points_with_one_fill_per_black_cell():
    pdf_bytes = build_marker_pdf(marker_id=0, marker_mm=50)
    rects = marker_rects_mm(marker_id=0, marker_mm=50)

    assert pdf_bytes.startswith(b"%PDF-1.4")
    assert b"/MediaBox [0 0 595.28 841.89]" in pdf_bytes
    assert pdf_bytes.count(b" re\n") == len(rects)
