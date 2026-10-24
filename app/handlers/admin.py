from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command, CommandStart, CommandObject
from sqlwork.user import ban_user, create_user, get_user, unban_user
from config import MODERATION_GROUP_ID
from utils.duration import parse_duration


router = Router()

@router.message(Command("ban"), F.chat.id == MODERATION_GROUP_ID)
async def ban_command(message: Message, bot: Bot, is_admin: bool):
    if not is_admin:
        return

    arguments = message.text.split(maxsplit=3)

    if len(arguments) < 2:
        await message.answer(
            "❗️ Использование:\n"
            "/ban ID [время] [причина]\n"
            "/ban ID причина — бессрочно"
        )
        return

    try:
        user_id = int(arguments[1])
    except ValueError:
        await message.answer("❗️ Некорректный ID")
        return

    user_data = get_user(user_id)

    if user_data is None:
        await message.answer(f"❌ Пользователь {user_id} не найден в базе данных")
        return

    if user_data["is_banned"] == 1:
        await message.answer(f"❌ Пользователь {user_id} уже забанен")
        return

    duration = None
    reason = None

    if len(arguments) == 3:
        parsed_duration = parse_duration(arguments[2])

        if parsed_duration is not None:
            duration = parsed_duration
        else:
            reason = arguments[2]

    elif len(arguments) == 4:
        duration = parse_duration(arguments[2])

        if duration is None:
            await message.answer("❗️Неверная длительность. Используйте 30m, 1h или 1d.")
            return

        reason = arguments[3]

    ban_user(user_id, duration, reason)

    if duration is None:
        duration_text = "навсегда"
    else:
        duration_text = arguments[2]

    await message.answer(
        f"🔨 Пользователь {user_id} забанен на {duration_text}.\n"
        f"Причина: {reason or 'не указана'}"
    )

    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                f"💔 Вы были забанены.\n"
                f"Причина: {reason or 'не указана'}"
            )
        )
    except Exception:
        pass

    


@router.message(Command('unban'), F.chat.id == MODERATION_GROUP_ID)
async def unban_command(message: Message, is_admin: bool, user):
    if not is_admin:
        return
    arguments = message.text.split()
    if len(arguments) != 2:
        await message.answer("❗️Использование: /unban ID")
        return
    user_id = arguments[1]
    user_data = get_user(user_id)
    if user_data['is_banned'] == 0:
        await message.answer(f"❗️ Пользователь {user_id} не забанен")
        return

    try:
        user_id = int(user_id)
    except ValueError:
        await message.answer("Неккоретный тип данных")
        return

    if user_data is None:
        await message.answer(f"Пользователь {user_id} не найден в базе данных")
        return
    
    unban_user(user_id)
    await message.answer(f"Пользователь {user_id} разбанен")

@router.message(Command("reply"), F.chat.id == MODERATION_GROUP_ID)
async def reply_to_user(message: Message, bot: Bot, is_admin: bool):
    if not is_admin:
        return

    args = (message.text or "").split(maxsplit=2)

    if len(args) < 3:
        await message.answer(
            "Использование:\n"
            "/reply ID сообщение\n\n"
            "Пример:\n"
            "/reply 123456789 Здравствуйте! Чем можем помочь?"
        )
        return

    try:
        user_id = int(args[1])
    except ValueError:
        await message.answer("❌ ID пользователя должен быть числом.")
        return

    reply_text = args[2].strip()

    if not reply_text:
        await message.answer("❌ Напиши текст ответа.")
        return

    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"💬 Ответ поддержки:\n\n{reply_text}",
        )
        await message.answer(f"✅ Ответ пользователю {user_id} отправлен.")

    except Exception:
        await message.answer(
            f"❌ Не удалось отправить сообщение пользователю {user_id}. "
            "Возможно, он не запускал бота или заблокировал его."
        )