import sqlite3
from contextlib import contextmanager
from app.core.config import settings

DB_PATH = settings.data_dir / "recall.sqlite3"

@contextmanager
def connect():
    db = sqlite3.connect(DB_PATH, timeout=30)
    db.row_factory = sqlite3.Row
    try:
        yield db
        db.commit()
    finally:
        db.close()

def init_db():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
          id TEXT PRIMARY KEY, filename TEXT NOT NULL, safe_name TEXT NOT NULL,
          file_type TEXT NOT NULL, size INTEGER NOT NULL, sha256 TEXT UNIQUE NOT NULL,
          status TEXT NOT NULL, chunk_count INTEGER DEFAULT 0, created_at TEXT NOT NULL,
          error TEXT
        );
        CREATE TABLE IF NOT EXISTS memories (
          id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
          content TEXT NOT NULL, kind TEXT NOT NULL, page INTEGER, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS activity (
          id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL, detail TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        PRAGMA foreign_keys=ON;
        """)
