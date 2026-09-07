DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #0b1326;
    color: #f1f5f9;
    font-family: 'Inter', 'Segoe UI', sans-serif;
    font-size: 12px;
}
QGroupBox {
    font-weight: 600;
    border: 1px solid #243147;
    border-radius: 6px;
    margin-top: 10px;
    padding: 10px 8px 8px 8px;
    background-color: #171f33;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #94a3b8;
    font-size: 11px;
}
QPushButton {
    background-color: #3b82f6;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
    font-weight: 600;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #2563eb;
}
QPushButton:pressed {
    background-color: #1d4ed8;
}
QSlider::groove:horizontal {
    border: 1px solid #243147;
    height: 6px;
    background: #0f172a;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #3b82f6;
    border: none;
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 7px;
}
QSlider::sub-page:horizontal {
    background: #3b82f6;
    border-radius: 3px;
}
QLineEdit {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 4px 8px;
    color: #f1f5f9;
    font-size: 11px;
}
QLineEdit:focus {
    border: 1px solid #3b82f6;
}
QTextEdit {
    background-color: #0f172a;
    border: 1px solid #243147;
    border-radius: 4px;
    color: #94a3b8;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 11px;
}
QLabel {
    color: #94a3b8;
}
QProgressBar {
    background-color: #0f172a;
    border: none;
    border-radius: 3px;
    height: 6px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background-color: #3b82f6;
    border-radius: 3px;
}
"""
