from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtGui import QFont, QAction
from PySide6.QtWidgets import (
    QFrame, QPushButton, QLineEdit, QTextEdit, QLabel, QHBoxLayout, QGraphicsOpacityEffect
)
from utils.icons import get_svg_icon, get_svg_pixmap

# Color Palette Tokens
COLOR_BG = "#0F0F12"
COLOR_SURFACE = "#18181B"
COLOR_SURFACE_HOVER = "#242429"
COLOR_BORDER = "#27272A"
COLOR_ACCENT = "#8B5CF6"
COLOR_ACCENT_HOVER = "#7C3AED"
COLOR_TEXT = "#FAFAFA"
COLOR_MUTED = "#A1A1AA"
COLOR_DANGER = "#EF4444"

class MinimalCard(QFrame):
    """Clean surface card container with border outline."""
    def __init__(self, parent=None, corner_radius: int = 12):
        super().__init__(parent)
        self.setStyleSheet(f"""
            MinimalCard {{
                background-color: {COLOR_SURFACE};
                border: 1px solid {COLOR_BORDER};
                border-radius: {corner_radius}px;
            }}
        """)


class AnimatedButton(QPushButton):
    """Modern flat minimalist button supporting icons and clear states."""
    def __init__(self, text: str = "", parent=None, primary: bool = False, 
                 icon_name: str = None, icon_color: str = "#FAFAFA", corner_radius: int = 8):
        super().__init__(text, parent)
        self.setFixedHeight(38)
        self.setFont(QFont("Inter", 9, QFont.Weight.Medium))
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        if icon_name:
            self.setIcon(get_svg_icon(icon_name, color=icon_color, size=18))
            self.setIconSize(QSize(18, 18))

        if primary:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_ACCENT};
                    color: #FFFFFF;
                    border: none;
                    border-radius: {corner_radius}px;
                    padding: 0 16px;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_ACCENT_HOVER};
                }}
                QPushButton:pressed {{
                    background-color: #6D28D9;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_SURFACE};
                    color: {COLOR_TEXT};
                    border: 1px solid {COLOR_BORDER};
                    border-radius: {corner_radius}px;
                    padding: 0 12px;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_SURFACE_HOVER};
                    border: 1px solid #3F3F46;
                }}
                QPushButton:checked {{
                    background-color: {COLOR_ACCENT};
                    border: 1px solid {COLOR_ACCENT};
                    color: #FFFFFF;
                }}
            """)


class MinimalInput(QLineEdit):
    """Line edit with optional leading vector icon."""
    def __init__(self, placeholder: str = "", icon_name: str = None, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setFixedHeight(40)
        self.setFont(QFont("Inter", 10))

        if icon_name:
            action = QAction(get_svg_icon(icon_name, color=COLOR_MUTED, size=18), "", self)
            self.addAction(action, QLineEdit.ActionPosition.LeadingPosition)

        self.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLOR_SURFACE};
                color: {COLOR_TEXT};
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                padding-left: 10px;
                padding-right: 10px;
            }}
            QLineEdit:focus {{
                border: 1px solid {COLOR_ACCENT};
            }}
        """)


class MinimalTextEdit(QTextEdit):
    """Sleek minimalist editor area."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Inter", 10))
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLOR_SURFACE};
                color: {COLOR_TEXT};
                border: 1px solid {COLOR_BORDER};
                border-radius: 10px;
                padding: 14px;
                line-height: 1.6;
            }}
            QTextEdit:focus {{
                border: 1px solid {COLOR_ACCENT};
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: #27272A;
                border-radius: 3px;
            }}
        """)


class ToastNotification(QFrame):
    """Animated sliding toast notification banner with vector SVG icon."""
    def __init__(self, message: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(260, 42)
        self.setStyleSheet("""
            ToastNotification {
                background-color: #10B981;
                border-radius: 8px;
            }
            QLabel {
                color: white;
                font-weight: 600;
                font-size: 12px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_svg_pixmap("check", color="#FFFFFF", size=18))

        msg_lbl = QLabel(message)
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(icon_lbl)
        layout.addWidget(msg_lbl, stretch=1)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

    def animate_show(self):
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(1800)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.setEasingCurve(QEasingCurve.Type.InQuad)
        self.anim.finished.connect(self.deleteLater)
        self.anim.start()