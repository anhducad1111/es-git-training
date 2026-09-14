"""Generate the ChArUco board used by the calibration mode."""

import cv2

from esp32_mjpeg_detector.calibration import make_charuco_board


board = make_charuco_board()
image = board.generateImage((1200, 1600), marginSize=40, borderBits=1)
cv2.imwrite("charuco_board.png", image)
print("charuco_board.png を印刷してください。外周を切り取らず、実寸を測ってください。")
