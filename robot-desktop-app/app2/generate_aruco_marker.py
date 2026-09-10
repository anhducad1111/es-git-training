"""Generate the default tracking marker centered on A4 at exactly 50 mm."""

import cv2

A4_WIDTH_MM = 210.0
A4_HEIGHT_MM = 297.0
MM_TO_PT = 72.0 / 25.4


def marker_rects_mm(marker_id: int = 0, marker_mm: float = 50.0) -> list[tuple[float, float, float, float]]:
    """Black marker cells as (x_mm, y_mm, width_mm, height_mm), origin top-left, centered on A4."""
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    pattern = cv2.aruco.generateImageMarker(dictionary, marker_id, 10, borderBits=1)
    origin_x, origin_y = (A4_WIDTH_MM - marker_mm) / 2, (A4_HEIGHT_MM - marker_mm) / 2
    cell_mm = marker_mm / pattern.shape[0]
    rects = []
    for row in range(pattern.shape[0]):
        for col in range(pattern.shape[1]):
            if pattern[row, col] < 128:
                rects.append((origin_x + col * cell_mm, origin_y + row * cell_mm, cell_mm, cell_mm))
    return rects


def build_marker_svg(marker_id: int = 0, marker_mm: float = 50.0) -> str:
    rects = marker_rects_mm(marker_id, marker_mm)
    rect_tags = "".join(
        f'<rect x="{x:.4f}" y="{y:.4f}" width="{w:.4f}" height="{h:.4f}" fill="black"/>' for x, y, w, h in rects
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{A4_WIDTH_MM:g}mm" height="{A4_HEIGHT_MM:g}mm" '
        f'viewBox="0 0 {A4_WIDTH_MM:g} {A4_HEIGHT_MM:g}">'
        f'<rect width="{A4_WIDTH_MM:g}" height="{A4_HEIGHT_MM:g}" fill="white"/>'
        f'<g aria-label="ArUco marker {marker_id}" data-marker-width="{marker_mm:g}mm" '
        f'data-marker-height="{marker_mm:g}mm">{rect_tags}</g></svg>'
    )


def build_marker_pdf(marker_id: int = 0, marker_mm: float = 50.0) -> bytes:
    """A one-page, print-ready A4 PDF with the marker drawn as vector-filled squares
    (no rasterization/DPI to worry about; printing at 100% scale reproduces marker_mm exactly)."""
    rects = marker_rects_mm(marker_id, marker_mm)
    page_width_pt = A4_WIDTH_MM * MM_TO_PT
    page_height_pt = A4_HEIGHT_MM * MM_TO_PT

    content_lines = ["0 0 0 rg"]
    for x_mm, y_mm, w_mm, h_mm in rects:
        x_pt = x_mm * MM_TO_PT
        # PDF space is bottom-left origin; our rects are measured from the top.
        y_pt = page_height_pt - (y_mm + h_mm) * MM_TO_PT
        w_pt = w_mm * MM_TO_PT
        h_pt = h_mm * MM_TO_PT
        content_lines.append(f"{x_pt:.4f} {y_pt:.4f} {w_pt:.4f} {h_pt:.4f} re")
    content_lines.append("f")
    content_stream = "\n".join(content_lines).encode("ascii")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width_pt:.2f} {page_height_pt:.2f}] "
            f"/Contents 4 0 R /Resources << >> >>"
        ).encode("ascii"),
        (f"<< /Length {len(content_stream)} >>\nstream\n".encode("ascii") + content_stream + b"\nendstream"),
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{index} 0 obj\n".encode("ascii") + body + b"\nendobj\n"

    xref_offset = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n".encode("ascii")
    pdf += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        pdf += f"{offset:010d} 00000 n \n".encode("ascii")
    pdf += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode("ascii")
    )
    return bytes(pdf)


if __name__ == "__main__":
    svg = build_marker_svg()
    with open("aruco_marker_id0_a4.svg", "w", encoding="utf-8") as output:
        output.write(svg)
    with open("aruco_marker_id0_a4.pdf", "wb") as output:
        output.write(build_marker_pdf())
    print("aruco_marker_id0_a4.svg / .pdf をA4・倍率100%で印刷してください。マーカーは50 mm角です。")
