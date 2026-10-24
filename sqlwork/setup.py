from .connection import get_connection

# Создание таблицы
def create_table():
    with get_connection() as conn:
        cursor = conn.cursor()
        create_table_query = """
        CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        is_banned INTEGER NOT NULL DEFAULT 0,
        ban_until INTEGER
        )
"""
        cursor.execute(create_table_query)


def add_ban_reason_column():
    with get_connection() as conn:
        cursor = conn.cursor()
        

        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "ban_reason" not in columns:
            alter_query = "ALTER TABLE users ADD COLUMN ban_reason TEXT;"
            cursor.execute(alter_query)
            conn.commit()


