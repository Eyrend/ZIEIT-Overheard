import json
import time

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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS post_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                source_chat_id INTEGER NOT NULL,
                source_message_id INTEGER NOT NULL,
                post_text TEXT,
                post_entities TEXT,
                post_content_type TEXT,
                anonymous INTEGER NOT NULL,
                author_label TEXT NOT NULL,
                order_id INTEGER,
                pin_hours INTEGER,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (
                        status IN (
                            'pending', 'awaiting_reason', 'publishing',
                            'approved', 'rejected'
                        )
                    ),
                review_message_id INTEGER,
                rejection_prompt_message_id INTEGER,
                rejection_reason TEXT,
                channel_message_id INTEGER,
                unpin_at INTEGER,
                pinned_at INTEGER,
                pin_retry_at INTEGER,
                unpinned_at INTEGER,
                created_at INTEGER NOT NULL
            )
            """
        )
        columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(post_submissions)"
            ).fetchall()
        }
        for column, column_type in (
            ("post_text", "TEXT"),
            ("post_entities", "TEXT"),
            ("post_content_type", "TEXT"),
            ("pinned_at", "INTEGER"),
            ("pin_retry_at", "INTEGER"),
        ):
            if column not in columns:
                conn.execute(
                    f"ALTER TABLE post_submissions ADD COLUMN {column} {column_type}"
                )
                if column == "pinned_at":
                    conn.execute(
                        """
                        UPDATE post_submissions
                        SET pinned_at = created_at
                        WHERE status = 'approved'
                          AND pin_hours IS NOT NULL
                          AND channel_message_id IS NOT NULL
                          AND unpin_at IS NOT NULL
                          AND unpinned_at IS NULL
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


def count_support_requests():
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS count FROM support_requests"
        ).fetchone()
        return row["count"]


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


def create_post_submission(
    user_id: int,
    source_chat_id: int,
    source_message_id: int,
    post_text: str | None,
    post_entities: list[dict],
    post_content_type: str,
    anonymous: bool,
    author_label: str,
    order_id: int | None,
    pin_hours: int | None,
) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO post_submissions (
                user_id, source_chat_id, source_message_id, anonymous,
                post_text, post_entities, post_content_type,
                author_label, order_id, pin_hours, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                source_chat_id,
                source_message_id,
                int(anonymous),
                post_text,
                json.dumps(post_entities, ensure_ascii=False),
                post_content_type,
                author_label,
                order_id,
                pin_hours,
                int(time.time()),
            ),
        )
        return cursor.lastrowid


def get_post_submission(submission_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM post_submissions WHERE id = ?",
            (submission_id,),
        ).fetchone()
        return dict(row) if row is not None else None


def save_post_review_message(submission_id: int, message_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE post_submissions
            SET review_message_id = ?
            WHERE id = ? AND status = 'pending'
            """,
            (message_id, submission_id),
        )
        return cursor.rowcount == 1


def claim_post_submission_approval(submission_id: int):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE post_submissions
            SET status = 'publishing'
            WHERE id = ? AND status = 'pending'
            """,
            (submission_id,),
        )
        if cursor.rowcount != 1:
            return None
        row = conn.execute(
            "SELECT * FROM post_submissions WHERE id = ?",
            (submission_id,),
        ).fetchone()
        return dict(row) if row is not None else None


def restore_post_submission_pending(submission_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE post_submissions
            SET status = 'pending'
            WHERE id = ? AND status = 'publishing'
            """,
            (submission_id,),
        )
        return cursor.rowcount == 1


def cancel_post_submission_rejection(submission_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE post_submissions
            SET status = 'pending', rejection_prompt_message_id = NULL
            WHERE id = ? AND status = 'awaiting_reason'
            """,
            (submission_id,),
        )
        return cursor.rowcount == 1


def mark_post_submission_published(
    submission_id: int,
    channel_message_id: int,
    unpin_at: int | None,
) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE post_submissions
            SET status = 'approved',
                channel_message_id = ?,
                unpin_at = ?
            WHERE id = ? AND status = 'publishing'
            """,
            (channel_message_id, unpin_at, submission_id),
        )
        return cursor.rowcount == 1


def claim_post_submission_rejection(submission_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE post_submissions
            SET status = 'awaiting_reason'
            WHERE id = ? AND status = 'pending'
            """,
            (submission_id,),
        )
        return cursor.rowcount == 1


def save_post_rejection_prompt(submission_id: int, message_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE post_submissions
            SET rejection_prompt_message_id = ?
            WHERE id = ? AND status = 'awaiting_reason'
            """,
            (message_id, submission_id),
        )
        return cursor.rowcount == 1


def get_post_submission_by_rejection_prompt(message_id: int):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM post_submissions
            WHERE rejection_prompt_message_id = ?
              AND status = 'awaiting_reason'
            """,
            (message_id,),
        ).fetchone()
        return dict(row) if row is not None else None


def mark_post_submission_rejected(submission_id: int, reason: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE post_submissions
            SET status = 'rejected', rejection_reason = ?
            WHERE id = ? AND status = 'awaiting_reason'
            """,
            (reason, submission_id),
        )
        return cursor.rowcount == 1


def get_post_submissions_due_for_unpin(now: int | None = None):
    current_time = int(time.time()) if now is None else now
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, channel_message_id
            FROM post_submissions
            WHERE status = 'approved'
              AND pin_hours IS NOT NULL
              AND channel_message_id IS NOT NULL
              AND pinned_at IS NOT NULL
              AND unpin_at <= ?
              AND unpinned_at IS NULL
            """,
            (current_time,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_post_submissions_due_for_pin(now: int | None = None):
    current_time = int(time.time()) if now is None else now
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, channel_message_id
            FROM post_submissions
            WHERE status = 'approved'
              AND pin_hours IS NOT NULL
              AND channel_message_id IS NOT NULL
              AND pinned_at IS NULL
              AND unpin_at > ?
              AND (pin_retry_at IS NULL OR pin_retry_at <= ?)
              AND unpinned_at IS NULL
            """,
            (current_time, current_time),
        ).fetchall()
        return [dict(row) for row in rows]


def mark_post_submission_pinned(submission_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE post_submissions
            SET pinned_at = ?, pin_retry_at = NULL
            WHERE id = ? AND status = 'approved'
              AND pinned_at IS NULL AND unpinned_at IS NULL
            """,
            (int(time.time()), submission_id),
        )
        return cursor.rowcount == 1


def postpone_post_submission_pin(submission_id: int, retry_at: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE post_submissions
            SET pin_retry_at = ?
            WHERE id = ? AND status = 'approved'
              AND pinned_at IS NULL AND unpinned_at IS NULL
            """,
            (retry_at, submission_id),
        )
        return cursor.rowcount == 1


def mark_post_submission_unpinned(submission_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE post_submissions
            SET unpinned_at = ?
            WHERE id = ? AND status = 'approved' AND unpinned_at IS NULL
            """,
            (int(time.time()), submission_id),
        )
        return cursor.rowcount == 1


def postpone_post_submission_unpin(submission_id: int, retry_at: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE post_submissions
            SET unpin_at = ?
            WHERE id = ? AND status = 'approved' AND unpinned_at IS NULL
            """,
            (retry_at, submission_id),
        )
        return cursor.rowcount == 1


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