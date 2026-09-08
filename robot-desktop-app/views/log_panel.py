from PyQt6.QtWidgets import (
    QPushButton, QTextEdit, QVBoxLayout, QWidget
)


def create_log_panel(app):
    app._log_collapsed = True

    app._log_panel = QWidget()
    app._log_panel.setStyleSheet("background-color: #0f172a; border-top: 1px solid #334155;")
    layout = QVBoxLayout()
    layout.setContentsMargins(16, 4, 16, 4)
    layout.setSpacing(0)

    header = QPushButton("[LOG] Click to expand/collapse   \u25b6")
    header.setStyleSheet("background: transparent; border: none; color: #94a3b8; font-size: 11px; text-align: left; padding: 4px 0;")
    header.clicked.connect(lambda: _toggle_log(app))
    layout.addWidget(header)
    app._log_header = header

    app._log_display = QTextEdit()
    app._log_display.setReadOnly(True)
    app._log_display.setStyleSheet("background-color: #0f172a; border: none; color: #94a3b8; font-size: 11px;")
    app._log_display.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
    app._log_display.setVisible(False)
    layout.addWidget(app._log_display)

    app._log_panel.setLayout(layout)
    app._log_panel.setFixedHeight(28)
    return app._log_panel


def _toggle_log(app):
    app._log_collapsed = not app._log_collapsed
    app._log_display.setVisible(not app._log_collapsed)
    if app._log_collapsed:
        app._log_panel.setFixedHeight(28)
        app._log_header.setText("[LOG] Click to expand/collapse   \u25b6")
    else:
        app._log_panel.setFixedHeight(180)
        app._log_header.setText("[LOG] Click to expand/collapse   \u25bc")
