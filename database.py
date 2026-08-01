import sqlite3
import hashlib
import os
from typing import List, Dict, Optional

class Database:
    def __init__(self, db_path: str = "echoes_journal.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'Personal',
                    mood TEXT NOT NULL DEFAULT 'happy',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.commit()

    def set_pin(self, pin: str):
        salt = os.urandom(16).hex()
        hashed = hashlib.sha256((salt + pin).encode('utf-8')).hexdigest()
        stored_val = f"{salt}:{hashed}"
        with self._get_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('pin_auth', ?)", (stored_val,))
            conn.commit()

    def has_pin(self) -> bool:
        with self._get_connection() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key='pin_auth'").fetchone()
            return row is not None

    def verify_pin(self, pin: str) -> bool:
        with self._get_connection() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key='pin_auth'").fetchone()
            if not row:
                return True
            salt, stored_hash = row['value'].split(":")
            check_hash = hashlib.sha256((salt + pin).encode('utf-8')).hexdigest()
            return check_hash == stored_hash

    def create_entry(self, title: str, content: str, category: str, mood: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO entries (title, content, category, mood, created_at, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (title, content, category, mood))
            conn.commit()
            return cursor.lastrowid

    def update_entry(self, entry_id: int, title: str, content: str, category: str, mood: str):
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE entries 
                SET title = ?, content = ?, category = ?, mood = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (title, content, category, mood, entry_id))
            conn.commit()

    def delete_entry(self, entry_id: int):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
            conn.commit()

    def get_all_entries(self, search: str = "", category: str = "All") -> List[Dict]:
        query = "SELECT * FROM entries WHERE 1=1"
        params = []

        if search:
            query += " AND (title LIKE ? OR content LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        if category != "All":
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY created_at DESC"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_entry_by_id(self, entry_id: int) -> Optional[Dict]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
            return dict(row) if row else None