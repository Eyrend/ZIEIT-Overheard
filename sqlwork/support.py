from sqlwork.connection import get_connection


def init_support_tables():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS support_requests (
                group_message_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS support_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                answer_text TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS moderation_posts (
                group_message_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL
            )
            """
        )


def save_support_request(group_message_id: int, user_id: int):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO support_requests (group_message_id, user_id)
            VALUES (?, ?)
            """,
            (group_message_id, user_id),
        )


def get_support_user(group_message_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT user_id FROM support_requests WHERE group_message_id = ?",
            (group_message_id,),
        ).fetchone()
        return row["user_id"] if row is not None else None


def save_moderation_post(group_message_id: int, user_id: int):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO moderation_posts (group_message_id, user_id)
            VALUES (?, ?)
            """,
            (group_message_id, user_id),
        )


def get_moderation_post_user(group_message_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT user_id FROM moderation_posts WHERE group_message_id = ?",
            (group_message_id,),
        ).fetchone()
        return row["user_id"] if row is not None else None


def create_support_answer(user_id: int, answer_text: str) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO support_answers (user_id, answer_text)
            VALUES (?, ?)
            """,
            (user_id, answer_text),
        )
        return cursor.lastrowid


def get_support_answer(answer_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT user_id, answer_text FROM support_answers WHERE id = ?",
            (answer_id,),
        ).fetchone()
        return dict(row) if row is not None else None