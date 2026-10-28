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
        ban_until INTEGER,
        username TEXT,
        is_muted INTEGER NOT NULL DEFAULT 0,
        mute_until INTEGER,
        mute_reason TEXT
        )
"""
        cursor.execute(create_table_query)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                admin_id INTEGER NOT NULL,
                reason TEXT,
                created_at INTEGER NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            )
        """)


def add_ban_reason_column():
    with get_connection() as conn:
        cursor = conn.cursor()
        

        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        new_columns = {
            "ban_reason": "TEXT",
            "username": "TEXT",
            "is_muted": "INTEGER NOT NULL DEFAULT 0",
            "mute_until": "INTEGER",
            "mute_reason": "TEXT",
            "birthday": "TEXT",
            "birthday_notified_on": "TEXT",
            "created_at": "INTEGER",
        }
        for column, definition in new_columns.items():
            if column not in columns:
                cursor.execute(
                    f"ALTER TABLE users ADD COLUMN {column} {definition}"
                )

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_username "
            "ON users(username COLLATE NOCASE)"
        )
