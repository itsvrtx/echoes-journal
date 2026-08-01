import hashlib
import sqlite3
from typing import Dict, List, Optional
from database.database import get_db_path


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

    def set_pin(self, pin: str) -> bool:
        if len(pin) != 4 or not pin.isdigit():
            return False
        hashed = hashlib.sha256(pin.encode("utf-8")).hexdigest()
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO app_security (id, pin_hash) VALUES (1, ?)",
            (hashed,),
        )
        conn.commit()
        return True

    def verify_pin(self, entered_pin: str) -> bool:
        hashed = hashlib.sha256(entered_pin.encode("utf-8")).hexdigest()
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT pin_hash FROM app_security WHERE id = 1")
        row = cursor.fetchone()
        return row is not None and row["pin_hash"] == hashed

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

    def add_entry(
        self,
        title: str,
        content: str,
        category: str = "General",
        mood: str = "Neutral",
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

    def update_entry(
        self,
        entry_id: int,
        title: str,
        content: str,
        category: str = "General",
        mood: str = "Neutral",
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

    def delete_entry(self, entry_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM journal_entries WHERE id = ?", (entry_id,)
        )
        conn.commit()
