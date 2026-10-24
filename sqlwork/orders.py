
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
                telegram_payment_charge_id TEXT UNIQUE
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


def create_pin_order(
    user_id: int,
    post_chat_id: int,
    post_message_id: int,
    hours: int,
    amount: int,
) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO pin_orders (
                user_id, post_chat_id, post_message_id,
                hours, amount, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                post_chat_id,
                post_message_id,
                hours,
                amount,
                int(time.time()),
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
              AND payment_submitted_at IS NULL
            """,
            (file_id, int(time.time()), order_id, user_id),
        )
        return cursor.rowcount == 1

