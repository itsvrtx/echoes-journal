import ctypes
import hashlib
import os
import sqlite3
import sys
from typing import Dict, List, Optional


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

    if sys.platform == "win32":
        try:
            ctypes.windll.kernel32.SetFileAttributesW(app_dir, 0x02)
            if os.path.exists(db_path):
                ctypes.windll.kernel32.SetFileAttributesW(db_path, 0x02)
        except Exception:
            pass

    return db_path


class DatabaseManager:

    def __init__(self):
        self.db_path = get_db_path()
        self.conn = None
        self._init_db()

    def get_connection(self):
        if not self.conn:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def _init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS app_security (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                pin_hash TEXT NOT NULL
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                category TEXT DEFAULT 'General',
                mood TEXT DEFAULT 'Neutral',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        conn.commit()

    def has_pin(self) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT pin_hash FROM app_security WHERE id = 1")
        return cursor.fetchone() is not None

    is_pin_set = has_pin

    def verify_pin(self, pin: str) -> bool:
        pin_hash = hashlib.sha256(pin.encode()).hexdigest()
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT pin_hash FROM app_security WHERE id = 1 AND pin_hash = ?",
            (pin_hash,),
        )
        return cursor.fetchone() is not None

    def set_pin(self, pin: str) -> bool:
        pin_hash = hashlib.sha256(pin.encode()).hexdigest()
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO app_security (id, pin_hash) VALUES (1, ?)
            ON CONFLICT(id) DO UPDATE SET pin_hash = excluded.pin_hash
        """,
            (pin_hash,),
        )
        conn.commit()
        return True

    def add_entry(
        self,
        title: str,
        content: str,
        category: str = "General",
        mood: str = "Neutral",
        *args,
        **kwargs,
    ) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO journal_entries (title, content, category, mood)
            VALUES (?, ?, ?, ?)
        """,
            (title, content, category, mood),
        )
        conn.commit()
        return cursor.lastrowid

    def save_entry(
        self,
        title: str,
        content: str,
        category: str = "General",
        mood: str = "Neutral",
        *args,
        **kwargs,
    ) -> int:
        return self.add_entry(title, content, category, mood, *args, **kwargs)

    def create_entry(
        self,
        title: str,
        content: str,
        category: str = "General",
        mood: str = "Neutral",
        *args,
        **kwargs,
    ) -> int:
        return self.add_entry(title, content, category, mood, *args, **kwargs)

    def update_entry(
        self,
        entry_id: int,
        title: str,
        content: str,
        category: str = "General",
        mood: str = "Neutral",
        *args,
        **kwargs,
    ):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE journal_entries
            SET title = ?, content = ?, category = ?, mood = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (title, content, category, mood, entry_id),
        )
        conn.commit()

    def get_all_entries(
        self,
        search: str = "",
        category: str = "All",
        tag: str = "All",
        sort_by: str = "newest",
    ) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM journal_entries WHERE 1=1"
        params = []

        if search:
            query += " AND (title LIKE ? OR content LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        if category and category != "All":
            query += " AND category = ?"
            params.append(category)

        if sort_by == "oldest":
            query += " ORDER BY created_at ASC"
        else:
            query += " ORDER BY created_at DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_entry_count(self) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM journal_entries")
        result = cursor.fetchone()
        return result[0] if result else 0

    def get_entry(self, entry_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM journal_entries WHERE id = ?", (entry_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_entry_by_id(self, entry_id: int) -> Optional[Dict]:
        return self.get_entry(entry_id)

    def delete_entry(self, entry_id: int) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM journal_entries WHERE id = ?", (entry_id,))
        conn.commit()
        return cursor.rowcount > 0
