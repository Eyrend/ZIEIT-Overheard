import sqlite3
from contextlib import contextmanager
from pathlib import Path

db_path = Path(__file__).resolve().parent.parent / "OverHeard_user.db"

# Инициализация функции подключения с преобразованием данных рядов 
@contextmanager
def get_connection():
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()