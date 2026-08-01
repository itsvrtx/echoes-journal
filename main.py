import sys
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor, QPalette, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QGraphicsOpacityEffect
)

from database.db_manager import DatabaseManager
from ui.lock_screen import LockScreen
from ui.header import HeaderView
from ui.sidebar import SidebarView
from ui.editor import EditorView
from ui.components import COLOR_BG
from ui.animations import AnimationManager
from utils.win_theme import apply_dark_titlebar
from utils import branding


class EchoesApp(QMainWindow):
    KONAMI_SEQUENCE = [
        Qt.Key.Key_Up, Qt.Key.Key_Up,
        Qt.Key.Key_Down, Qt.Key.Key_Down,
        Qt.Key.Key_Left, Qt.Key.Key_Right,
        Qt.Key.Key_Left, Qt.Key.Key_Right,
        Qt.Key.Key_B, Qt.Key.Key_A,
    ]

    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.konami_progress = 0
        self.anim = None

        self.setWindowTitle("ECHOES — Minimalist Journal")
        self.resize(1080, 700)
        self.setMinimumSize(880, 580)
        self.logo_path = branding.find_logo()
        self.setWindowIcon(branding.app_icon(self.logo_path))

        self._apply_global_theme()
        self._setup_keybinds()

        self.root_stack = QStackedWidget(self)
        self.setCentralWidget(self.root_stack)

        self.lock_screen = LockScreen(self.db, logo_path=self.logo_path or "")
        self.lock_screen.unlocked.connect(self._animated_unlock)
        self.root_stack.addWidget(self.lock_screen)

        self.main_workspace = QWidget()
        self._build_workspace()
        self.root_stack.addWidget(self.main_workspace)

        self.root_stack.setCurrentWidget(self.lock_screen)

    def _apply_global_theme(self):
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor(COLOR_BG))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#FAFAFA"))
        self.setPalette(pal)

    def _setup_keybinds(self):
        QShortcut(QKeySequence(Qt.Key.Key_F11), self).activated.connect(self._toggle_fullscreen)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self).activated.connect(self._exit_fullscreen)
        QShortcut(QKeySequence("Ctrl+M"), self).activated.connect(self._spawn_single_cat)

    def _toggle_fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def _exit_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()

    def _build_workspace(self):
        ws = QVBoxLayout(self.main_workspace)
        ws.setContentsMargins(14, 14, 14, 14)
        ws.setSpacing(10)

        self.header = HeaderView(logo_path=self.logo_path or "")
        self.header.lock_requested.connect(self._lock_app)
        self.header.new_entry_requested.connect(self._create_new_entry)
        self.header.cat_requested.connect(self._spawn_single_cat)
        self.header.magic_requested.connect(self._magic_easter_egg)
        ws.addWidget(self.header)

        content = QHBoxLayout()
        content.setSpacing(10)

        self.sidebar = SidebarView(self.db)
        self.sidebar.entry_selected.connect(self.editor_load)
        self.sidebar.meow_easter_egg.connect(self._spawn_single_cat)

        self.editor = EditorView(self.db)
        self.editor.entry_saved.connect(self.sidebar.refresh_entries)
        self.editor.entry_deleted.connect(self.sidebar.refresh_entries)
        self.editor.confetti_requested.connect(self._celebrate_save)

        content.addWidget(self.sidebar)
        content.addWidget(self.editor, stretch=1)
        ws.addLayout(content)

        self.anim = AnimationManager(self.main_workspace)

    def editor_load(self, entry_id: int):
        self.editor.load_entry(entry_id)

    def _animated_unlock(self):
        effect = QGraphicsOpacityEffect(self.main_workspace)
        self.main_workspace.setGraphicsEffect(effect)

        self.root_stack.setCurrentWidget(self.main_workspace)
        self.sidebar.refresh_entries()

        self.fade_anim = QPropertyAnimation(effect, b"opacity")
        self.fade_anim.setDuration(400)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_anim.finished.connect(self._clear_fade_effect)
        self.fade_anim.start()

    def _clear_fade_effect(self):
        self.main_workspace.setGraphicsEffect(None)
        if self.anim:
            self.anim._sync_geometry()

    def _lock_app(self):
        self.lock_screen.reset()
        self.root_stack.setCurrentWidget(self.lock_screen)

    def _create_new_entry(self):
        self.editor.clear_editor()
        self.sidebar.clear_selection()

    def _spawn_single_cat(self):
        if self.anim:
            self.anim.spawn_cat()

    def _celebrate_save(self):
        if not self.anim:
            return
        r = self.editor.geometry()
        self.anim.confetti_burst(r.right() - 90, r.bottom() - 40, 45)
        self.anim.confetti_rain(35)

    def _magic_easter_egg(self):
        if self.anim:
            self.anim.celebrate("✨  M A G I C !  ✨",
                                "You found a secret. Have some cats.",
                                rain=True, cats=5)

    def keyPressEvent(self, event):
        key = event.key()
        if key == self.KONAMI_SEQUENCE[self.konami_progress]:
            self.konami_progress += 1
            if self.konami_progress >= len(self.KONAMI_SEQUENCE):
                self.konami_progress = 0
                self._konami_activated()
        else:
            self.konami_progress = 1 if key == self.KONAMI_SEQUENCE[0] else 0
        super().keyPressEvent(event)

    def _konami_activated(self):
        if not self.anim:
            return
        self.anim.celebrate("🐱  CAT INVASION  🐱",
                            "Konami Code accepted.", rain=True, cats=14)
        w, h = self.main_workspace.width(), self.main_workspace.height()
        for x in (w // 4, w // 2, w * 3 // 4):
            self.anim.confetti_burst(x, h // 3, 32)


def main():
    branding.set_app_user_model_id("Echoes.Journal.Desktop.1")

    app = QApplication(sys.argv)
    branding.describe()

    app.setWindowIcon(branding.app_icon())

    font = QFont("Inter")
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    window = EchoesApp()
    window.show()

    apply_dark_titlebar(window)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
