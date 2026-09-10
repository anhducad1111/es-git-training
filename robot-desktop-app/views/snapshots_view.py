from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QVBoxLayout, QWidget, QScrollArea, QFrame, QGridLayout
)

PAGE_SIZE = 6


def _extract_video_frame(video_data):
    """Extract first frame from video data for thumbnail."""
    import cv2
    import numpy as np
    import os
    from tempfile import gettempdir

    tmp_path = os.path.join(gettempdir(), "thumb_temp.avi")
    try:
        with open(tmp_path, "wb") as f:
            f.write(video_data)

        cap = cv2.VideoCapture(tmp_path)
        ret, frame = cap.read()
        cap.release()
        os.remove(tmp_path)

        if ret and frame is not None:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            return QPixmap.fromImage(qimg)
    except Exception:
        pass
    return None


def create_snapshots_view(app):
    widget = QWidget()
    layout = QHBoxLayout()
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(16)

    left_panel = QWidget()
    left_layout = QVBoxLayout()
    left_layout.setContentsMargins(0, 0, 0, 0)
    left_layout.setSpacing(8)

    header = QHBoxLayout()
    title = QLabel("SNAPSHOT GALLERY")
    title.setStyleSheet("""
        color: #06b6d4;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 2px;
    """)
    header.addWidget(title)
    header.addStretch()

    refresh_btn = QPushButton("REFRESH")
    refresh_btn.setFixedWidth(70)
    refresh_btn.setStyleSheet("""
        QPushButton {
            background-color: #1e293b;
            border: 1px solid #334155;
            color: #06b6d4;
            font-weight: 600;
            font-size: 9px;
            letter-spacing: 1px;
        }
        QPushButton:hover {
            background-color: #334155;
        }
    """)
    refresh_btn.clicked.connect(lambda: _load_snapshots(app))
    header.addWidget(refresh_btn)

    left_layout.addLayout(header)

    tab_bar = QHBoxLayout()
    tab_bar.setSpacing(4)
    app._snapshot_tab_buttons = []
    tab_bar.addStretch()
    app._snapshot_tab_layout = tab_bar
    left_layout.addLayout(tab_bar)

    nav_layout = QHBoxLayout()
    nav_layout.setSpacing(8)

    app._prev_btn = QPushButton("< PREV")
    app._prev_btn.setFixedHeight(26)
    app._prev_btn.setStyleSheet("""
        QPushButton {
            background-color: #1e293b;
            border: 1px solid #334155;
            color: #94a3b8;
            font-weight: 600;
            font-size: 9px;
            padding: 4px 12px;
        }
        QPushButton:hover { background-color: #334155; }
        QPushButton:disabled { color: #475569; }
    """)
    app._prev_btn.clicked.connect(lambda: _change_page(app, -1))
    nav_layout.addWidget(app._prev_btn)

    app._page_label = QLabel("Page 1 / 1")
    app._page_label.setStyleSheet("color: #94a3b8; font-size: 9px;")
    app._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    nav_layout.addWidget(app._page_label)

    app._next_btn = QPushButton("NEXT >")
    app._next_btn.setFixedHeight(26)
    app._next_btn.setStyleSheet("""
        QPushButton {
            background-color: #1e293b;
            border: 1px solid #334155;
            color: #94a3b8;
            font-weight: 600;
            font-size: 9px;
            padding: 4px 12px;
        }
        QPushButton:hover { background-color: #334155; }
        QPushButton:disabled { color: #475569; }
    """)
    app._next_btn.clicked.connect(lambda: _change_page(app, 1))
    nav_layout.addWidget(app._next_btn)

    left_layout.addLayout(nav_layout)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("""
        QScrollArea {
            background-color: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 6px;
        }
    """)

    app._snapshot_grid = QWidget()
    app._snapshot_grid.setStyleSheet("background-color: #0f172a;")
    app._snapshot_grid_layout = QGridLayout()
    app._snapshot_grid_layout.setContentsMargins(8, 8, 8, 8)
    app._snapshot_grid_layout.setSpacing(8)
    app._snapshot_grid.setLayout(app._snapshot_grid_layout)

    scroll.setWidget(app._snapshot_grid)
    left_layout.addWidget(scroll, 1)

    left_panel.setLayout(left_layout)
    layout.addWidget(left_panel, 1)

    right_panel = QWidget()
    right_panel.setFixedWidth(320)
    right_layout = QVBoxLayout()
    right_layout.setContentsMargins(0, 0, 0, 0)
    right_layout.setSpacing(8)

    preview_title = QLabel("PREVIEW")
    preview_title.setStyleSheet("""
        color: #06b6d4;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 2px;
    """)
    right_layout.addWidget(preview_title)

    app._snapshot_preview = QLabel("Select a snapshot")
    app._snapshot_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
    app._snapshot_preview.setMinimumHeight(240)
    app._snapshot_preview.setStyleSheet("""
        background-color: #0a0e1a;
        border: 1px solid #1e293b;
        border-radius: 6px;
        color: #64748b;
        font-size: 11px;
    """)
    right_layout.addWidget(app._snapshot_preview, 1)

    info_title = QLabel("INFO")
    info_title.setStyleSheet("""
        color: #06b6d4;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 2px;
    """)
    right_layout.addWidget(info_title)

    app._snapshot_info = QTextEdit()
    app._snapshot_info.setReadOnly(True)
    app._snapshot_info.setMaximumHeight(100)
    app._snapshot_info.setStyleSheet("""
        background-color: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 6px;
        padding: 8px;
        color: #94a3b8;
        font-size: 10px;
        font-family: 'JetBrains Mono', monospace;
    """)
    right_layout.addWidget(app._snapshot_info)

    action_layout = QHBoxLayout()

    download_btn = QPushButton("DOWNLOAD")
    download_btn.setFixedHeight(28)
    download_btn.setStyleSheet("""
        QPushButton {
            background-color: rgba(59, 130, 246, 0.15);
            border: 1px solid rgba(59, 130, 246, 0.3);
            color: #3b82f6;
            font-weight: 600;
            font-size: 10px;
            padding: 4px 12px;
            letter-spacing: 1px;
        }
        QPushButton:hover {
            background-color: rgba(59, 130, 246, 0.25);
        }
    """)
    download_btn.clicked.connect(lambda: _download_snapshot(app))
    action_layout.addWidget(download_btn)

    delete_btn = QPushButton("DELETE")
    delete_btn.setFixedHeight(28)
    delete_btn.setStyleSheet("""
        QPushButton {
            background-color: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: #ef4444;
            font-weight: 600;
            font-size: 10px;
            padding: 4px 12px;
            letter-spacing: 1px;
        }
        QPushButton:hover {
            background-color: rgba(239, 68, 68, 0.25);
        }
    """)
    delete_btn.clicked.connect(lambda: _delete_snapshot(app))
    action_layout.addWidget(delete_btn)

    right_layout.addLayout(action_layout)

    process_title = QLabel("IMAGE PROCESSING")
    process_title.setStyleSheet("""
        color: #06b6d4;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 2px;
    """)
    right_layout.addWidget(process_title)

    process_layout = QVBoxLayout()
    process_layout.setSpacing(4)

    app._process_btns = {}
    app._selected_modes = set()

    auto_btn = QPushButton("AUTO CORRECT")
    auto_btn.setFixedHeight(28)
    auto_btn._mode = "auto"
    auto_btn._normal_style = """
        QPushButton {
            background-color: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: #10b981;
            font-weight: 600;
            font-size: 10px;
            padding: 4px 12px;
            letter-spacing: 1px;
        }
        QPushButton:hover {
            background-color: rgba(16, 185, 129, 0.25);
        }
    """
    auto_btn._selected_style = """
        QPushButton {
            background-color: #10b981;
            border: 2px solid #10b981;
            color: white;
            font-weight: 700;
            font-size: 10px;
            padding: 4px 12px;
            letter-spacing: 1px;
        }
    """
    auto_btn._processing_style = """
        QPushButton {
            background-color: #059669;
            border: 2px solid #059669;
            color: white;
            font-weight: 700;
            font-size: 10px;
            padding: 4px 12px;
            letter-spacing: 1px;
        }
    """
    auto_btn.setStyleSheet(auto_btn._normal_style)
    auto_btn.clicked.connect(lambda: _toggle_mode(app, "auto", auto_btn))
    process_layout.addWidget(auto_btn)
    app._process_btns["auto"] = auto_btn

    contrast_btn = QPushButton("ENHANCE CONTRAST")
    contrast_btn.setFixedHeight(28)
    contrast_btn._mode = "contrast"
    contrast_btn._normal_style = """
        QPushButton {
            background-color: rgba(139, 92, 246, 0.15);
            border: 1px solid rgba(139, 92, 246, 0.3);
            color: #8b5cf6;
            font-weight: 600;
            font-size: 10px;
            padding: 4px 12px;
            letter-spacing: 1px;
        }
        QPushButton:hover {
            background-color: rgba(139, 92, 246, 0.25);
        }
    """
    contrast_btn._selected_style = """
        QPushButton {
            background-color: #8b5cf6;
            border: 2px solid #8b5cf6;
            color: white;
            font-weight: 700;
            font-size: 10px;
            padding: 4px 12px;
            letter-spacing: 1px;
        }
    """
    contrast_btn._processing_style = """
        QPushButton {
            background-color: #7c3aed;
            border: 2px solid #7c3aed;
            color: white;
            font-weight: 700;
            font-size: 10px;
            padding: 4px 12px;
            letter-spacing: 1px;
        }
    """
    contrast_btn.setStyleSheet(contrast_btn._normal_style)
    contrast_btn.clicked.connect(lambda: _toggle_mode(app, "contrast", contrast_btn))
    process_layout.addWidget(contrast_btn)
    app._process_btns["contrast"] = contrast_btn

    denoise_btn = QPushButton("DENOISE")
    denoise_btn.setFixedHeight(28)
    denoise_btn._mode = "denoise"
    denoise_btn._normal_style = """
        QPushButton {
            background-color: rgba(245, 158, 11, 0.15);
            border: 1px solid rgba(245, 158, 11, 0.3);
            color: #f59e0b;
            font-weight: 600;
            font-size: 10px;
            padding: 4px 12px;
            letter-spacing: 1px;
        }
        QPushButton:hover {
            background-color: rgba(245, 158, 11, 0.25);
        }
    """
    denoise_btn._selected_style = """
        QPushButton {
            background-color: #f59e0b;
            border: 2px solid #f59e0b;
            color: white;
            font-weight: 700;
            font-size: 10px;
            padding: 4px 12px;
            letter-spacing: 1px;
        }
    """
    denoise_btn._processing_style = """
        QPushButton {
            background-color: #d97706;
            border: 2px solid #d97706;
            color: white;
            font-weight: 700;
            font-size: 10px;
            padding: 4px 12px;
            letter-spacing: 1px;
        }
    """
    denoise_btn.setStyleSheet(denoise_btn._normal_style)
    denoise_btn.clicked.connect(lambda: _toggle_mode(app, "denoise", denoise_btn))
    process_layout.addWidget(denoise_btn)
    app._process_btns["denoise"] = denoise_btn

    bicubic_btn = QPushButton("BICUBIC (1.5x)")
    bicubic_btn.setFixedHeight(28)
    bicubic_btn._mode = "bicubic"
    bicubic_btn._normal_style = """
        QPushButton {
            background-color: rgba(236, 72, 153, 0.15);
            border: 1px solid rgba(236, 72, 153, 0.3);
            color: #ec4899;
            font-weight: 600;
            font-size: 10px;
            padding: 4px 12px;
            letter-spacing: 1px;
        }
        QPushButton:hover {
            background-color: rgba(236, 72, 153, 0.25);
        }
    """
    bicubic_btn._selected_style = """
        QPushButton {
            background-color: #ec4899;
            border: 2px solid #ec4899;
            color: white;
            font-weight: 700;
            font-size: 10px;
            padding: 4px 12px;
            letter-spacing: 1px;
        }
    """
    bicubic_btn._processing_style = """
        QPushButton {
            background-color: #db2777;
            border: 2px solid #db2777;
            color: white;
            font-weight: 700;
            font-size: 10px;
            padding: 4px 12px;
            letter-spacing: 1px;
        }
    """
    bicubic_btn.setStyleSheet(bicubic_btn._normal_style)
    bicubic_btn.clicked.connect(lambda: _toggle_mode(app, "bicubic", bicubic_btn))
    process_layout.addWidget(bicubic_btn)
    app._process_btns["bicubic"] = bicubic_btn

    apply_btn = QPushButton("APPLY SELECTED")
    apply_btn.setFixedHeight(30)
    apply_btn._normal_style = """
        QPushButton {
            background-color: rgba(6, 182, 212, 0.2);
            border: 1px solid rgba(6, 182, 212, 0.4);
            color: #06b6d4;
            font-weight: 700;
            font-size: 10px;
            padding: 4px 12px;
            letter-spacing: 1px;
        }
        QPushButton:hover {
            background-color: rgba(6, 182, 212, 0.3);
        }
        QPushButton:disabled {
            color: #475569;
        }
    """
    apply_btn._processing_style = """
        QPushButton {
            background-color: #0891b2;
            border: 1px solid #0891b2;
            color: white;
            font-weight: 700;
            font-size: 10px;
            padding: 4px 12px;
            letter-spacing: 1px;
        }
    """
    apply_btn.setStyleSheet(apply_btn._normal_style)
    apply_btn.clicked.connect(lambda: _apply_selected(app))
    process_layout.addWidget(apply_btn)
    app._apply_btn = apply_btn

    right_layout.addLayout(process_layout)

    right_panel.setLayout(right_layout)
    layout.addWidget(right_panel)

    widget.setLayout(layout)
    return widget


def _load_snapshots(app):
    if not hasattr(app, '_cloud_api') or not app._cloud_api:
        app._add_log("SNAPSHOT", "Cloud API not initialized")
        return

    app._add_log("SNAPSHOT", "Loading snapshots from cloud...")

    result = app._cloud_api.get_media()
    if isinstance(result, dict) and "error" in result:
        app._add_log("SNAPSHOT", f"Error: {result['error']}")
        return

    _on_snapshots_loaded(app, result)


def _on_snapshots_loaded(app, data):
    if isinstance(data, dict):
        data = data.get("media", [])
    if not isinstance(data, list):
        app._add_log("SNAPSHOT", f"Invalid response: {data}")
        return

    app._snapshot_data = data
    app._snapshot_page = 0
    total_pages = max(1, (len(data) + PAGE_SIZE - 1) // PAGE_SIZE)
    app._snapshot_total_pages = total_pages
    app._add_log("SNAPSHOT", f"Loaded {len(data)} snapshots ({total_pages} pages)")

    _build_tab_buttons(app)
    _show_current_page(app)


def _build_tab_buttons(app):
    for btn in app._snapshot_tab_buttons:
        btn.deleteLater()
    app._snapshot_tab_buttons.clear()

    for p in range(app._snapshot_total_pages):
        btn = QPushButton(f"{p + 1}")
        btn.setFixedSize(28, 22)
        btn.setCheckable(True)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #334155;
                color: #94a3b8;
                font-weight: 600;
                font-size: 9px;
            }
            QPushButton:checked {
                background-color: #06b6d4;
                color: #0a0e1a;
                border-color: #06b6d4;
            }
            QPushButton:hover {
                border-color: #06b6d4;
            }
        """)
        btn.clicked.connect(lambda checked, page=p: _go_to_page(app, page))
        app._snapshot_tab_layout.insertWidget(app._snapshot_tab_layout.count() - 1, btn)
        app._snapshot_tab_buttons.append(btn)


def _go_to_page(app, page):
    app._snapshot_page = page
    _show_current_page(app)


def _change_page(app, delta):
    new_page = app._snapshot_page + delta
    if 0 <= new_page < app._snapshot_total_pages:
        app._snapshot_page = new_page
        _show_current_page(app)


def _show_current_page(app):
    data = getattr(app, '_snapshot_data', [])
    page = app._snapshot_page
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_data = data[start:end]

    while app._snapshot_grid_layout.count():
        item = app._snapshot_grid_layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()

    for i, snap in enumerate(page_data):
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setFixedSize(220, 190)
        card.setStyleSheet("""
            QFrame {
                background-color: #0a0e1a;
                border: 2px solid #1e293b;
                border-radius: 8px;
            }
            QFrame:hover {
                border-color: #06b6d4;
            }
        """)
        card.setCursor(Qt.CursorShape.PointingHandCursor)

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(6, 6, 6, 6)
        card_layout.setSpacing(0)

        thumb_label = QLabel()
        thumb_label.setFixedSize(208, 140)
        thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb_label.setStyleSheet("background-color: #0f172a; border-radius: 4px; color: #64748b; font-size: 9px;")
        thumb_label.setText("Loading...")
        card_layout.addWidget(thumb_label)

        media_type = snap.get("media_type", "photo")
        if media_type == "video":
            type_badge = QLabel("VIDEO")
            type_badge.setFixedSize(40, 16)
            type_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            type_badge.setStyleSheet("""
                background-color: #8b5cf6;
                color: white;
                font-size: 7px;
                font-weight: bold;
                border-radius: 3px;
            """)
            type_badge.setParent(thumb_label)
            type_badge.move(4, 4)

        time_str = str(snap.get("captured_at", ""))[:16].replace("T", " ")
        time_label = QLabel(time_str)
        time_label.setStyleSheet("color: #94a3b8; font-size: 8px; padding: 2px 4px;")
        card_layout.addWidget(time_label)

        card.setLayout(card_layout)

        snap_id = snap.get("id")
        if snap_id:
            media_data = app._cloud_api.get_media_item(snap_id)
            if media_data:
                if media_type == "video":
                    pixmap = _extract_video_frame(media_data)
                else:
                    pixmap = QPixmap()
                    pixmap.loadFromData(media_data)
                
                if pixmap and not pixmap.isNull():
                    scaled = pixmap.scaled(
                        208, 140,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    thumb_label.setPixmap(scaled)
                else:
                    thumb_label.setText("No preview")
            else:
                thumb_label.setText("Load failed")

        global_index = start + i
        card.mousePressEvent = lambda event, idx=global_index: _select_snapshot(app, idx)

        row = i // 3
        col = i % 3
        app._snapshot_grid_layout.addWidget(card, row, col)

    for p, btn in enumerate(app._snapshot_tab_buttons):
        btn.setChecked(p == page)

    total = app._snapshot_total_pages
    app._page_label.setText(f"Page {page + 1} / {total}")
    app._prev_btn.setEnabled(page > 0)
    app._next_btn.setEnabled(page < total - 1)

    if page_data:
        global_index = start
        _select_snapshot(app, global_index)
    else:
        app._snapshot_preview.setText("No snapshots")
        app._snapshot_info.setText("")


def _select_snapshot(app, index):
    if not hasattr(app, '_snapshot_data') or index >= len(app._snapshot_data):
        return

    snap = app._snapshot_data[index]
    app._selected_snapshot = snap

    info = f"ID: {snap.get('id', 'N/A')}\n"
    info += f"Type: {snap.get('media_type', 'N/A')}\n"
    info += f"MIME: {snap.get('mime_type', 'N/A')}\n"
    info += f"Size: {snap.get('file_size_bytes', 0)} bytes\n"
    info += f"Captured: {snap.get('captured_at', 'N/A')}"
    app._snapshot_info.setText(info)

    snap_id = snap.get("id")
    if not snap_id:
        return

    media_type = snap.get("media_type", "photo")
    media_data = app._cloud_api.get_media_item(snap_id)
    
    if not media_data:
        app._snapshot_preview.setText("Failed to load preview")
        return

    if media_type == "video":
        _show_video_preview(app, media_data, snap_id)
    else:
        _show_image_preview(app, media_data)


def _show_image_preview(app, image_data):
    pixmap = QPixmap()
    pixmap.loadFromData(image_data)
    if not pixmap.isNull():
        scaled = pixmap.scaled(
            app._snapshot_preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        app._snapshot_preview.setPixmap(scaled)
    else:
        app._snapshot_preview.setText("Invalid image data")


def _show_video_preview(app, video_data, snap_id):
    import cv2
    import numpy as np
    import os
    from tempfile import gettempdir

    tmp_path = os.path.join(gettempdir(), f"preview_{snap_id}.avi")
    try:
        with open(tmp_path, "wb") as f:
            f.write(video_data)

        cap = cv2.VideoCapture(tmp_path)
        ret, frame = cap.read()
        cap.release()

        if ret and frame is not None:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            from PyQt6.QtGui import QImage
            qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            scaled = pixmap.scaled(
                app._snapshot_preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            app._snapshot_preview.setPixmap(scaled)
            app._add_log("VIDEO", f"Preview loaded: frame {cap.get(cv2.CAP_PROP_FRAME_COUNT)} frames")
        else:
            app._snapshot_preview.setText("Cannot read video")

        os.remove(tmp_path)
    except Exception as e:
        app._snapshot_preview.setText(f"Video preview error")
        app._add_log("VIDEO", f"Preview error: {str(e)[:50]}")


def _download_snapshot(app):
    if hasattr(app, '_processed_image') and app._processed_image is not None:
        import cv2
        from PyQt6.QtWidgets import QFileDialog

        dst, _ = QFileDialog.getSaveFileName(
            None, "Save Processed Image", "processed.png", "Images (*.png *.jpg)"
        )
        if dst:
            cv2.imwrite(dst, app._processed_image)
            app._add_log("IMAGE", f"Downloaded: {dst}")
        return

    if not hasattr(app, '_selected_snapshot') or not app._cloud_api:
        return

    snap = app._selected_snapshot
    snap_id = snap.get("id")
    if not snap_id:
        return

    app._add_log("SNAPSHOT", f"Downloading snapshot {snap_id}...")
    image_data = app._cloud_api.get_media_item(snap_id)
    if image_data:
        snap_type = snap.get("media_type", "photo")
        ext = "png" if "png" in snap.get("mime_type", "") else "jpg"
        filename = f"{snap_type}_{snap_id}.{ext}"
        filepath = f"snapshot/{filename}"
        import os
        os.makedirs("snapshot", exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(image_data)
        app._add_log("SNAPSHOT", f"Downloaded: {filename}")
    else:
        app._add_log("SNAPSHOT", "Download failed")


def _delete_snapshot(app):
    if not hasattr(app, '_selected_snapshot') or not app._cloud_api:
        return

    snap = app._selected_snapshot
    snap_id = snap.get("id")
    if not snap_id:
        return

    app._add_log("SNAPSHOT", f"Deleting snapshot {snap_id}...")
    success = app._cloud_api.delete_media(snap_id)
    if success:
        app._add_log("SNAPSHOT", "Deleted successfully")
        _load_snapshots(app)
    else:
        app._add_log("SNAPSHOT", "Delete failed")


def _process_snapshot(app, mode, btn=None):
    if not hasattr(app, '_selected_snapshot') or not app._cloud_api:
        return

    if btn and hasattr(btn, '_done_style') and btn.styleSheet() == btn._done_style:
        _restore_original(app, btn, mode)
        return

    if btn:
        btn.setEnabled(False)
        if hasattr(btn, '_processing_style'):
            btn.setStyleSheet(btn._processing_style)
            btn.setText(f"PROCESSING...")

    snap = app._selected_snapshot
    snap_id = snap.get("id")
    if not snap_id:
        if btn:
            btn.setEnabled(True)
            if hasattr(btn, '_normal_style'):
                btn.setStyleSheet(btn._normal_style)
                _reset_btn_text(btn, mode)
        return

    app._add_log("IMAGE", f"Processing: {mode}...")

    image_data = app._cloud_api.get_media_item(snap_id)
    if not image_data:
        app._add_log("IMAGE", "Failed to fetch image")
        if btn:
            btn.setEnabled(True)
            if hasattr(btn, '_normal_style'):
                btn.setStyleSheet(btn._normal_style)
                _reset_btn_text(btn, mode)
        return

    import os
    import tempfile

    os.makedirs("snapshot", exist_ok=True)

    ext = "png" if "png" in snap.get("mime_type", "") else "jpg"
    input_path = os.path.join(tempfile.gettempdir(), f"proc_in_{snap_id}.{ext}")
    output_path = f"snapshot/processed_{mode}_{snap_id}.{ext}"

    with open(input_path, "wb") as f:
        f.write(image_data)

    try:
        from image_processor import ImageProcessor
        worker = ImageProcessor(input_path, output_path, mode)
        worker.finished.connect(lambda path: _on_process_done(app, path, btn, mode))
        worker.error.connect(lambda e: _on_process_error(app, e, btn, mode))
        worker.status.connect(lambda s: app._add_log("IMAGE", s))
        app._cloud_workers.append(worker)
        worker.finished.connect(lambda: app._cloud_workers.remove(worker) if worker in app._cloud_workers else None)
        worker.error.connect(lambda: app._cloud_workers.remove(worker) if worker in app._cloud_workers else None)
        worker.start()
    except ImportError:
        app._add_log("IMAGE", "OpenCV not installed. Run: pip install opencv-python")
        if btn:
            btn.setEnabled(True)
            if hasattr(btn, '_normal_style'):
                btn.setStyleSheet(btn._normal_style)
                _reset_btn_text(btn, mode)
    except Exception as e:
        app._add_log("IMAGE", f"Error: {str(e)[:60]}")
        if btn:
            btn.setEnabled(True)
            if hasattr(btn, '_normal_style'):
                btn.setStyleSheet(btn._normal_style)
                _reset_btn_text(btn, mode)


def _reset_btn_text(btn, mode):
    texts = {"auto": "AUTO CORRECT", "contrast": "ENHANCE CONTRAST", "denoise": "DENOISE"}
    btn.setText(texts.get(mode, "PROCESS"))


def _toggle_mode(app, mode, btn):
    if mode in app._selected_modes:
        app._selected_modes.discard(mode)
        btn.setStyleSheet(btn._normal_style)
        btn.setText(_get_mode_text(mode))
    else:
        app._selected_modes.add(mode)
        btn.setStyleSheet(btn._selected_style)
        btn.setText(f"✓ {mode.upper()}")


def _get_mode_text(mode):
    texts = {"auto": "AUTO CORRECT", "contrast": "ENHANCE CONTRAST", "denoise": "DENOISE", "bicubic": "BICUBIC (1.5x)"}
    return texts.get(mode, mode.upper())


def _apply_selected(app):
    if not app._selected_modes:
        app._add_log("IMAGE", "No processing selected")
        return

    if not hasattr(app, '_selected_snapshot') or not app._cloud_api:
        return

    for mode in app._selected_modes:
        btn = app._process_btns.get(mode)
        if btn:
            btn.setEnabled(False)
            btn.setStyleSheet(btn._processing_style)

    app._apply_btn.setEnabled(False)
    app._apply_btn.setStyleSheet(app._apply_btn._processing_style)
    app._apply_btn.setText("PROCESSING...")

    snap = app._selected_snapshot
    snap_id = snap.get("id")
    if not snap_id:
        _reset_apply_buttons(app)
        return

    app._add_log("IMAGE", f"Applying: {', '.join(app._selected_modes)}...")

    image_data = app._cloud_api.get_media_item(snap_id)
    if not image_data:
        app._add_log("IMAGE", "Failed to fetch image")
        _reset_apply_buttons(app)
        return

    import os
    import tempfile

    os.makedirs("snapshot", exist_ok=True)

    ext = "png" if "png" in snap.get("mime_type", "") else "jpg"
    input_path = os.path.join(tempfile.gettempdir(), f"proc_in_{snap_id}.{ext}")

    with open(input_path, "wb") as f:
        f.write(image_data)

    try:
        from image_processor import ImageProcessor
        modes = list(app._selected_modes)
        output_path = f"snapshot/processed_{'_'.join(modes)}_{snap_id}.{ext}"

        worker = ImageProcessor(input_path, output_path, modes)
        worker.finished.connect(lambda path: _on_apply_done(app, path))
        worker.error.connect(lambda e: _on_apply_error(app, e))
        worker.status.connect(lambda s: app._add_log("IMAGE", s))
        app._cloud_workers.append(worker)
        worker.finished.connect(lambda: _reset_apply_buttons(app))
        worker.error.connect(lambda: _reset_apply_buttons(app))
        worker.start()
    except ImportError:
        app._add_log("IMAGE", "OpenCV not installed. Run: pip install opencv-python")
        _reset_apply_buttons(app)
    except Exception as e:
        app._add_log("IMAGE", f"Error: {str(e)[:60]}")
        _reset_apply_buttons(app)


def _reset_apply_buttons(app):
    for mode, btn in app._process_btns.items():
        btn.setEnabled(True)
        if mode in app._selected_modes:
            btn.setStyleSheet(btn._selected_style)
        else:
            btn.setStyleSheet(btn._normal_style)

    app._apply_btn.setEnabled(True)
    app._apply_btn.setStyleSheet(app._apply_btn._normal_style)
    app._apply_btn.setText("APPLY SELECTED")


def _on_apply_done(app, result_img):
    import cv2
    import numpy as np
    from PyQt6.QtGui import QPixmap, QImage

    app._add_log("IMAGE", "Processing complete")
    app._processed_image = result_img

    h, w, ch = result_img.shape
    bytes_per_line = ch * w
    rgb_image = cv2.cvtColor(result_img, cv2.COLOR_BGR2RGB)
    q_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
    pixmap = QPixmap.fromImage(q_image)

    if not pixmap.isNull():
        scaled = pixmap.scaled(
            app._snapshot_preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        app._snapshot_preview.setPixmap(scaled)


def _on_apply_error(app, error_msg):
    app._add_log("IMAGE", f"Error: {error_msg}")
