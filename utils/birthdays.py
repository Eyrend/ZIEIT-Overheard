import asyncio
import logging
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError

from config import MODERATION_GROUP_ID
from sqlwork.user import (
    get_unnotified_birthday_reminders,
    get_unnotified_birthdays,
    mark_birthday_notified,
    mark_birthday_reminded,
)


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


def days_until_next_birthday(birthday: date, today: date | None = None) -> int:
    current_date = today or current_kyiv_date()
    year = current_date.year
    while True:
        try:
            next_birthday = date(year, birthday.month, birthday.day)
        except ValueError:
            year += 1
            continue
        if next_birthday >= current_date:
            return (next_birthday - current_date).days
        year += 1


def birthday_reminder_offset(birthday: date, today: date | None = None) -> int:
    current_date = today or current_kyiv_date()
    days_until = days_until_next_birthday(birthday, current_date)
    if days_until <= 1:
        return days_until
    yesterday = current_date - timedelta(days=1)
    if (yesterday.month, yesterday.day) == (birthday.month, birthday.day):
        return -1
    return days_until


def calculate_age(birthday: date, today: date | None = None) -> int:
    current_date = today or current_kyiv_date()
    birthday_not_reached = (current_date.month, current_date.day) < (
        birthday.month,
        birthday.day,
    )
    return current_date.year - birthday.year - birthday_not_reached


def age_at_next_birthday(birthday: date, today: date | None = None) -> int:
    current_date = today or current_kyiv_date()
    next_birthday = current_date + timedelta(
        days=days_until_next_birthday(birthday, current_date)
    )
    return next_birthday.year - birthday.year


def format_years(years: int) -> str:
    last_two_digits = years % 100
    if 11 <= last_two_digits <= 14:
        unit = "лет"
    elif years % 10 == 1:
        unit = "год"
    elif 2 <= years % 10 <= 4:
        unit = "года"
    else:
        unit = "лет"
    return f"{years} {unit}"


def format_birthday_countdown(birthday: date, today: date | None = None) -> str:
    days = days_until_next_birthday(birthday, today)
    if days == 0:
        return "Сегодня твой день рождения! 🎉"
    return format_days_remaining(days)


def format_days_remaining(days: int) -> str:
    if days % 10 == 1 and days % 100 != 11:
        unit = "день"
    elif 2 <= days % 10 <= 4 and not 12 <= days % 100 <= 14:
        unit = "дня"
    else:
        unit = "дней"
    return f"До дня рождения осталось {days} {unit}."


def seconds_until_kyiv_midnight(now: datetime | None = None) -> float:
    current = now.astimezone(KYIV) if now is not None else datetime.now(KYIV)
    next_date = current.date() + timedelta(days=1)
    next_midnight = datetime.combine(next_date, time.min, tzinfo=KYIV)
    return max(0.0, (next_midnight - current).total_seconds())


async def notify_todays_birthdays(bot: Bot) -> None:
    today = current_kyiv_date()
    for user in get_unnotified_birthdays(today):
        birthday_text = format_stored_birthday(user["birthday"])
        birthday = date.fromisoformat(user["birthday"])
        age = calculate_age(birthday, today)
        username = f"@{user['username']}" if user["username"] else "отсутствует"
        await bot.send_message(
            chat_id=MODERATION_GROUP_ID,
            text=(
                "🎂 Сегодня день рождения!\n\n"
                f"👤 Никнейм: {user['name'] or 'Без имени'}\n"
                f"🔗 Username: {username}\n"
                f"📅 Дата рождения: {birthday_text}\n"
                f"🎉 Исполняется: {format_years(age)}"
            )
        )
        mark_birthday_notified(user["telegram_id"], today)


async def notify_tomorrows_birthdays(bot: Bot) -> None:
    today = current_kyiv_date()
    tomorrow = today + timedelta(days=1)
    for user in get_unnotified_birthday_reminders(tomorrow, today):
        try:
            await bot.send_message(
                chat_id=user["telegram_id"],
                text="🎂 Завтра твой день рождения! Остался 1 день. Хорошего праздника!",
            )
        except TelegramForbiddenError:
            logger.warning(
                "Could not send birthday reminder to Telegram user %s",
                user["telegram_id"],
            )
        mark_birthday_reminded(user["telegram_id"], today)


async def run_daily_birthday_notifications(bot: Bot) -> None:
    while True:
        try:
            await notify_tomorrows_birthdays(bot)
            await notify_todays_birthdays(bot)
            await asyncio.sleep(seconds_until_kyiv_midnight())
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Daily birthday notifications failed; retrying in 10 minutes")
            await asyncio.sleep(600)
