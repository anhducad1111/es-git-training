from PyQt6.QtWidgets import (
    QPushButton, QTextEdit, QVBoxLayout, QWidget
)


def create_log_panel(app):
    app._log_collapsed = True

    app._log_panel = QWidget()
    app._log_panel.setStyleSheet("""
        background-color: #0a0e1a;
        border-top: 1px solid #1e293b;
    """)
    layout = QVBoxLayout()
    layout.setContentsMargins(16, 4, 16, 4)
    layout.setSpacing(0)

    header = QPushButton("LOG")
    header.setStyleSheet("""
        background: transparent;
        border: none;
        color: #475569;
        font-size: 9px;
        font-weight: 600;
        letter-spacing: 2px;
        text-align: left;
        padding: 4px 0;
    """)
    header.clicked.connect(lambda: _toggle_log(app))
    layout.addWidget(header)
    app._log_header = header

    app._log_display = QTextEdit()
    app._log_display.setReadOnly(True)
    app._log_display.setStyleSheet("""
        background-color: #0a0e1a;
        border: none;
        color: #64748b;
        font-size: 10px;
        font-family: 'JetBrains Mono', monospace;
    """)
    app._log_display.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
    app._log_display.setVisible(False)
    layout.addWidget(app._log_display)

    app._log_panel.setLayout(layout)
    app._log_panel.setFixedHeight(24)
    return app._log_panel


def _toggle_log(app):
    app._log_collapsed = not app._log_collapsed
    app._log_display.setVisible(not app._log_collapsed)
    if app._log_collapsed:
        app._log_panel.setFixedHeight(24)
        app._log_header.setStyleSheet("""
            background: transparent;
            border: none;
            color: #475569;
            font-size: 9px;
            font-weight: 600;
            letter-spacing: 2px;
            text-align: left;
            padding: 4px 0;
        """)
    else:
        app._log_panel.setFixedHeight(160)
        app._log_header.setStyleSheet("""
            background: transparent;
            border: none;
            color: #06b6d4;
            font-size: 9px;
            font-weight: 600;
            letter-spacing: 2px;
            text-align: left;
            padding: 4px 0;
        """)
