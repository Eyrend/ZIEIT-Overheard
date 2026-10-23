from .connection import get_connection

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

def ban_user(is_banned, telegram_id):
    with get_connection() as conn:
        cursor = conn.cursor()

        update_query = """
        UPDATE users
        SET is_banned = ?
        WHERE telegram_id = ?
"""
        data = (
            is_banned,
            telegram_id
        )
        cursor.execute(update_query, data)
        conn.commit()