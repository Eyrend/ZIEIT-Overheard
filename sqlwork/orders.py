
import time

from sqlwork.connection import get_connection


def init_orders_table():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pin_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                post_chat_id INTEGER NOT NULL,
                post_message_id INTEGER NOT NULL,
                hours INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (
                        status IN (
                            'pending', 'paid', 'sending_post',
                            'post_sent', 'sending_info', 'fulfilled',
                            'cancelled'
                        )
                    ),
                created_at INTEGER NOT NULL,
                telegram_payment_charge_id TEXT UNIQUE,
                payment_method TEXT NOT NULL DEFAULT 'card',
                stars_amount INTEGER,
                expires_at INTEGER
            )
        """)

        columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(pin_orders)"
            ).fetchall()
        }

        if "payment_proof_file_id" not in columns:
            conn.execute("""
                ALTER TABLE pin_orders
                ADD COLUMN payment_proof_file_id TEXT
            """)

        if "payment_submitted_at" not in columns:
            conn.execute("""
                ALTER TABLE pin_orders
                ADD COLUMN payment_submitted_at INTEGER
            """)

        if "payment_method" not in columns:
            conn.execute("""
                ALTER TABLE pin_orders
                ADD COLUMN payment_method TEXT NOT NULL DEFAULT 'card'
            """)

        if "stars_amount" not in columns:
            conn.execute("""
                ALTER TABLE pin_orders
                ADD COLUMN stars_amount INTEGER
            """)

        if "expires_at" not in columns:
            conn.execute("""
                ALTER TABLE pin_orders
                ADD COLUMN expires_at INTEGER
            """)

        conn.execute(
            "UPDATE pin_orders SET expires_at = created_at + 900 "
            "WHERE expires_at IS NULL"
        )


def create_pin_order(
    user_id: int,
    post_chat_id: int,
    post_message_id: int,
    hours: int,
    amount: int,
    payment_method: str = "card",
    stars_amount: int | None = None,
) -> int:
    created_at = int(time.time())
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO pin_orders (
                user_id, post_chat_id, post_message_id,
                hours, amount, payment_method, stars_amount,
                created_at, expires_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                post_chat_id,
                post_message_id,
                hours,
                amount,
                payment_method,
                stars_amount,
                created_at,
                created_at + 900,
            ),
        )
        return cursor.lastrowid


def get_pin_order(order_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM pin_orders WHERE id = ?",
            (order_id,),
        ).fetchone()

        return dict(row) if row is not None else None


def update_pin_order_post(
    order_id: int,
    user_id: int,
    post_chat_id: int,
    post_message_id: int,
) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE pin_orders
            SET post_chat_id = ?, post_message_id = ?
            WHERE id = ?
              AND user_id = ?
              AND status = 'pending'
              AND payment_submitted_at IS NOT NULL
            """,
            (post_chat_id, post_message_id, order_id, user_id),
        )
        return cursor.rowcount == 1


def cancel_pin_order(order_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE pin_orders
            SET status = 'cancelled'
            WHERE id = ?
              AND status = 'pending'
              AND payment_submitted_at IS NULL
            """,
            (order_id,),
        )
        return cursor.rowcount == 1


def mark_payment_submitted(
    order_id: int,
    user_id: int,
    file_id: str,
) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE pin_orders
            SET payment_proof_file_id = ?,
                payment_submitted_at = ?
            WHERE id = ?
              AND user_id = ?
              AND status = 'pending'
              AND payment_method = 'card'
              AND payment_submitted_at IS NULL
              AND expires_at > ?
            """,
            (file_id, int(time.time()), order_id, user_id, int(time.time())),
        )
        return cursor.rowcount == 1


def mark_stars_payment_submitted(
    order_id: int,
    user_id: int,
    telegram_payment_charge_id: str,
) -> bool:
    now = int(time.time())
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE pin_orders
            SET telegram_payment_charge_id = ?,
                payment_submitted_at = ?
            WHERE id = ?
              AND user_id = ?
              AND status = 'pending'
              AND payment_method = 'stars'
              AND payment_submitted_at IS NULL
              AND expires_at > ?
            """,
            (telegram_payment_charge_id, now, order_id, user_id, now),
        )
        return cursor.rowcount == 1


def expire_pin_order(order_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE pin_orders
            SET status = 'cancelled'
            WHERE id = ?
              AND status = 'pending'
              AND payment_submitted_at IS NULL
              AND expires_at <= ?
            """,
            (order_id, int(time.time())),
        )
        return cursor.rowcount == 1

