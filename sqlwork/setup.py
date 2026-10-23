from .connection import get_connection

def create_table():
    with get_connection() as conn:
        cursor = conn.cursor()
        create_table_query = """
        CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        is_banned INTEGER NOT NULL DEFAULT 0
        )
"""
        cursor.execute(create_table_query)



