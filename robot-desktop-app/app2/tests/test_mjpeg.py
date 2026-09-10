from esp32_mjpeg_detector.mjpeg import MjpegParser


def test_parser_handles_headers_and_jpeg_split_across_chunks():
    parser = MjpegParser()
    data = (
        b"--123\r\nContent-Type: image/jpeg\r\nContent-Length: 4\r\n\r\n"
        b"abcd\r\n--123\r\nContent-Type: image/jpeg\r\nContent-Length: 3\r\n\r\nxyz"
    )

    frames = []
    for chunk in (data[:9], data[9:31], data[31:58], data[58:]):
        frames.extend(parser.feed(chunk))

    assert frames == [b"abcd", b"xyz"]


def test_parser_ignores_part_without_content_length():
    parser = MjpegParser()

    assert parser.feed(b"--x\r\nContent-Type: image/jpeg\r\n\r\nabc") == []
