import asyncio
import logging
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot

from config import MODERATION_GROUP_ID
from sqlwork.user import get_unnotified_birthdays, mark_birthday_notified


logger = logging.getLogger(__name__)
KYIV = ZoneInfo("Europe/Kyiv")


def current_kyiv_date() -> date:
    return datetime.now(KYIV).date()


def parse_birthday_date(value: str) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.strptime(value, "%d.%m.%Y").date()
    except ValueError:
        return None
    return parsed if parsed.strftime("%d.%m.%Y") == value else None


def format_stored_birthday(value: str) -> str:
    try:
        return date.fromisoformat(value).strftime("%d.%m.%Y")
    except ValueError:
        return value


def seconds_until_kyiv_midnight(now: datetime | None = None) -> float:
    current = now.astimezone(KYIV) if now is not None else datetime.now(KYIV)
    next_date = current.date() + timedelta(days=1)
    next_midnight = datetime.combine(next_date, time.min, tzinfo=KYIV)
    return max(0.0, (next_midnight - current).total_seconds())


async def notify_todays_birthdays(bot: Bot) -> None:
    today = current_kyiv_date()
    for user in get_unnotified_birthdays(today):
        birthday_text = format_stored_birthday(user["birthday"])
        username = f"@{user['username']}" if user["username"] else "отсутствует"
        await bot.send_message(
            chat_id=MODERATION_GROUP_ID,
            text=(
                "🎂 Сегодня день рождения!\n\n"
                f"👤 Никнейм: {user['name'] or 'Без имени'}\n"
                f"🔗 Username: {username}\n"
                f"📅 Дата рождения: {birthday_text}"
            )
        )
        mark_birthday_notified(user["telegram_id"], today)


async def run_daily_birthday_notifications(bot: Bot) -> None:
    while True:
        try:
            await notify_todays_birthdays(bot)
            await asyncio.sleep(seconds_until_kyiv_midnight())
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Daily birthday notifications failed; retrying in 10 minutes")
            await asyncio.sleep(600)
