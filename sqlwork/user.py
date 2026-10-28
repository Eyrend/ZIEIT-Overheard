from .connection import get_connection
from config import ADMIN_IDS
import time


# Создание юзера в таблице 
def create_user(telegram_id, name, is_banned, username=None):
    with get_connection() as conn:
        cursor = conn.cursor()

        insert_query = """
        INSERT OR IGNORE INTO users(
        telegram_id,
        name,
        is_banned,
        username,
        created_at
        )
        VALUES(?,?,?,?,?)
"""
        data = (
            telegram_id,
            name,
            is_banned,
            username,
            int(time.time()),
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


def get_or_create_user(telegram_id, name, username):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO users (
                telegram_id, name, is_banned, username, created_at
            )
            VALUES (?, ?, 0, ?, ?)
            """,
            (telegram_id, name, username, int(time.time())),
        )
        is_new_user = cursor.rowcount == 1
        conn.execute(
            """
            UPDATE users
            SET username = ?
            WHERE telegram_id = ? AND username IS NOT ?
            """,
            (username, telegram_id, username),
        )
        user = conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?",
            (telegram_id,),
        ).fetchone()
        return user, is_new_user


def get_user_statistics(days=7):
    now = int(time.time())
    cutoff = now - days * 24 * 60 * 60
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_users,
                SUM(CASE WHEN created_at >= ? THEN 1 ELSE 0 END) AS new_users,
                SUM(
                    CASE WHEN is_banned = 1
                        AND (ban_until IS NULL OR ban_until > ?)
                    THEN 1 ELSE 0 END
                ) AS banned_users,
                SUM(CASE WHEN birthday IS NOT NULL THEN 1 ELSE 0 END) AS birthday_users
            FROM users
            """,
            (cutoff, now),
        ).fetchone()
        return dict(row)


def get_user_by_username(username):
    normalized = username.lstrip("@").strip()
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE",
            (normalized,),
        ).fetchone()


def update_user_username(telegram_id, username):
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET username = ? WHERE telegram_id = ?",
            (username, telegram_id),
        )


def set_user_birthday(telegram_id, birthday, name=None, username=None):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE users
            SET birthday = ?, birthday_notified_on = NULL,
                name = COALESCE(?, name), username = ?
            WHERE telegram_id = ?
            """,
            (birthday, name, username, telegram_id),
        )
        return cursor.rowcount == 1


def get_birthday_users(limit, offset):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT telegram_id, name, username, birthday
            FROM users
            WHERE birthday IS NOT NULL
            ORDER BY birthday, telegram_id
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()


def get_birthday_user(telegram_id):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT telegram_id, name, username, birthday
            FROM users
            WHERE telegram_id = ? AND birthday IS NOT NULL
            """,
            (telegram_id,),
        ).fetchone()


def count_birthday_users():
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS count FROM users WHERE birthday IS NOT NULL"
        ).fetchone()
        return row["count"]


def delete_user_birthday(telegram_id):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE users
            SET birthday = NULL, birthday_notified_on = NULL
            WHERE telegram_id = ? AND birthday IS NOT NULL
            """,
            (telegram_id,),
        )
        return cursor.rowcount == 1


def get_unnotified_birthdays(today):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT telegram_id, name, username, birthday
            FROM users
            WHERE strftime('%m-%d', birthday) = ?
                AND (birthday_notified_on IS NULL OR birthday_notified_on != ?)
            ORDER BY telegram_id
            """,
            (today.strftime("%m-%d"), today.isoformat()),
        ).fetchall()


def mark_birthday_notified(telegram_id, today):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE users
            SET birthday_notified_on = ?
            WHERE telegram_id = ? AND birthday IS NOT NULL
            """,
            (today.isoformat(), telegram_id),
        )


def ban_user(telegram_id, duration=None, ban_reason=None):
    if telegram_id in ADMIN_IDS:
        return False

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
        return cursor.rowcount == 1


def mute_user(telegram_id, duration, mute_reason=None):
    if telegram_id in ADMIN_IDS:
        return False

    mute_until = int(time.time()) + duration
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE users
            SET is_muted = 1, mute_until = ?, mute_reason = ?
            WHERE telegram_id = ?
            """,
            (mute_until, mute_reason, telegram_id),
        )
        return cursor.rowcount == 1

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


def unmute_user(telegram_id):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE users
            SET is_muted = 0, mute_until = NULL, mute_reason = NULL
            WHERE telegram_id = ?
            """,
            (telegram_id,),
        )
        return cursor.rowcount == 1


def add_user_warning(user_id, admin_id, reason=None):
    if user_id in ADMIN_IDS:
        return None

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO user_warnings (user_id, admin_id, reason, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, admin_id, reason, int(time.time())),
        )
        return cursor.lastrowid


def get_active_warning_count(user_id):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS count FROM user_warnings
            WHERE user_id = ? AND is_active = 1
            """,
            (user_id,),
        ).fetchone()
        return row["count"]


def remove_latest_user_warning(user_id):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id FROM user_warnings
            WHERE user_id = ? AND is_active = 1
            ORDER BY id DESC LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        if row is None:
            return False

        cursor = conn.execute(
            "UPDATE user_warnings SET is_active = 0 WHERE id = ?",
            (row["id"],),
        )
        return cursor.rowcount == 1