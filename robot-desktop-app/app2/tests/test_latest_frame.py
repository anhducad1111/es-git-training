import threading

from esp32_mjpeg_detector.latest_frame import LatestFrame


def test_put_replaces_stale_frame():
    slot = LatestFrame[int]()
    slot.put(1)
    slot.put(2)

    assert slot.get(timeout=0.01) == 2
    assert slot.get(timeout=0.01) is None


def test_close_unblocks_waiting_get():
    slot = LatestFrame[int]()
    result = []

    def reader():
        result.append(slot.get(timeout=None))

    thread = threading.Thread(target=reader)
    thread.start()
    slot.close()
    thread.join(timeout=1)

    assert result == [None]
