DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #0a0e1a;
    color: #e2e8f0;
    font-family: 'Inter', 'Segoe UI', sans-serif;
    font-size: 12px;
}
QGroupBox {
    font-weight: 600;
    border: 1px solid #1e293b;
    border-radius: 8px;
    margin-top: 10px;
    padding: 12px 10px 10px 10px;
    background-color: #0f172a;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #64748b;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
}
QPushButton {
    background-color: #1e293b;
    color: #e2e8f0;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
    font-size: 11px;
}
QPushButton:hover {
    background-color: #334155;
    border-color: #475569;
}
QPushButton:pressed {
    background-color: #0f172a;
}
QSlider::groove:horizontal {
    border: 1px solid #1e293b;
    height: 4px;
    background: #1e293b;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #06b6d4;
    border: none;
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}
QSlider::sub-page:horizontal {
    background: #06b6d4;
    border-radius: 2px;
}
QLineEdit {
    background-color: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 4px;
    padding: 6px 10px;
    color: #e2e8f0;
    font-size: 11px;
}
QLineEdit:focus {
    border: 1px solid #06b6d4;
}
QTextEdit {
    background-color: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 4px;
    color: #94a3b8;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 11px;
}
QLabel {
    color: #94a3b8;
}
QProgressBar {
    background-color: #1e293b;
    border: none;
    border-radius: 2px;
    height: 4px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background-color: #06b6d4;
    border-radius: 2px;
}
"""
