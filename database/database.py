import ctypes
import os
import sys


def get_db_path() -> str:
    if sys.platform == "win32":
        base_dir = os.environ.get(
            "LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local")
        )
    else:
        base_dir = os.path.expanduser("~/.local/share")

    app_dir = os.path.join(base_dir, "ECHOES")
    os.makedirs(app_dir, exist_ok=True)

    db_path = os.path.join(app_dir, "echoes_data.db")
    if os.path.exists(db_path):
        _hide_file_windows(db_path)

    return db_path


def _hide_file_windows(path: str):
    if sys.platform == "win32":
        try:
            ctypes.windll.kernel32.SetFileAttributesW(path, 0x02)
        except Exception:
            pass
