from .connection import get_connection
import time
# Создание юзера в таблице 
def create_user(telegram_id, name, is_banned):
    with get_connection() as conn:
        cursor = conn.cursor()
        

        insert_query = """
        INSERT OR IGNORE INTO users(
        telegram_id,
        name,
        is_banned
        )
        VALUES(?,?,?)
"""
        data = (
            telegram_id,
            name,
            is_banned
        )
        cursor.execute(insert_query, data)
        conn.commit()

# Получение информации о юзере по айди
def get_user(telegram_id):
    with get_connection() as conn:
        cursor = conn.cursor()

        select_query = """
        SELECT * FROM users
        WHERE telegram_id = ?
"""
        cursor.execute(select_query, (telegram_id,))
        return cursor.fetchone()

def ban_user(telegram_id, duration=None, ban_reason=None):
    with get_connection() as conn:
        ban_until = int(time.time()) + duration if duration is not None else None
        cursor = conn.cursor()

        update_query = """
        UPDATE users
        SET is_banned = 1,
            ban_until = ?,
            ban_reason = ?
        WHERE telegram_id = ?
"""
        data = (
            ban_until,
            ban_reason, 
            telegram_id
        )
        cursor.execute(update_query, data)
    conn.commit()

def unban_user(telegram_id):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE users
            SET is_banned = 0, ban_until = NULL,  ban_reason = NULL
            WHERE telegram_id = ?
            """,
            (telegram_id,)
        )