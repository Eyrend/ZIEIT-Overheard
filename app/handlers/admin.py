from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from fsm import PostStates
from keyboards import moderation_keyboard, support_answer_kb
from sqlwork.support import (
    create_support_answer,
    get_support_answer,
    get_moderation_post_user,
    get_support_user,
)
from sqlwork.user import (
    add_user_warning,
    ban_user,
    create_user,
    get_active_warning_count,
    get_user,
    get_user_by_username,
    mute_user,
    remove_latest_user_warning,
    unban_user,
    unmute_user,
)
from config import ADMIN_IDS, MODERATION_GROUP_ID
from utils.duration import parse_duration


router = Router()


@router.message(
    Command("moderation", "mod"),
    F.chat.id == MODERATION_GROUP_ID,
)
async def show_moderation_panel(message: Message, is_admin: bool):
    if not is_admin:
        return

    await message.answer(
        "⚖️ <b>Модерация пользователей</b>",
        reply_markup=moderation_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("mod:"))
async def choose_moderation_action(
    callback: CallbackQuery,
    state: FSMContext,
):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    if callback.message is None or callback.message.chat.id != MODERATION_GROUP_ID:
        await callback.answer("Панель работает только в группе модерации.", show_alert=True)
        return

    action = callback.data.removeprefix("mod:")
    if action not in {
        "ban_forever", "ban_temporary", "mute_temporary", "warn",
        "unban", "unmute", "unwarn",
    }:
        await callback.answer("Неизвестное действие.", show_alert=True)
        return

    await state.update_data(moderation_action=action)
    await state.set_state(PostStates.moderation_target)
    instructions = {
        "ban_forever": "Введи ID или @username и причину, например:\n<code>@user спам</code>",
        "ban_temporary": "Введи ID или @username, срок и причину, например:\n<code>@user 1h спам</code>",
        "mute_temporary": "Введи ID или @username, срок и причину, например:\n<code>@user 1h флуд</code>",
        "warn": "Введи ID или @username и причину, например:\n<code>@user спам</code>",
        "unban": "Введи ID или @username пользователя для разбана.",
        "unmute": "Введи ID или @username пользователя для снятия мута.",
        "unwarn": "Введи ID или @username пользователя, чтобы снять последний варн.",
    }
    await callback.message.answer(instructions[action], parse_mode="HTML")
    await callback.answer()


@router.message(
    F.chat.id == MODERATION_GROUP_ID,
    PostStates.moderation_target,
)
async def apply_moderation_action(
    message: Message,
    state: FSMContext,
    bot: Bot,
    is_admin: bool,
):
    if not is_admin:
        await state.clear()
        return

    text = (message.text or "").strip()
    if text.lower() in {"/cancel", "отмена"}:
        await state.clear()
        await message.answer("Действие отменено.")
        return

    parts = text.split(maxsplit=2)
    if not parts:
        await message.answer("Введи ID или username пользователя.")
        return

    target = parts[0].lstrip("@")
    if target.isdigit():
        user_id = int(target)
        user = get_user(user_id)
    else:
        user = get_user_by_username(target)
        user_id = user["telegram_id"] if user is not None else None

    if user_id is None or user is None:
        await message.answer(
            "Пользователь не найден. Он должен хотя бы раз написать боту; "
            "попробуй его Telegram ID или сохранённый username."
        )
        return

    if user_id in ADMIN_IDS:
        await state.clear()
        await message.answer("⛔️ Нельзя применять ограничения к администраторам.")
        return

    data = await state.get_data()
    action = data.get("moderation_action")
    reason = None
    duration = None
    duration_label = None

    if action in {"ban_temporary", "mute_temporary"}:
        if len(parts) < 2:
            await message.answer("Укажи срок: например, <code>30m</code>, <code>1h</code> или <code>1d</code>.", parse_mode="HTML")
            return
        duration = parse_duration(parts[1])
        if duration is None:
            await message.answer("Неверный срок. Используй <code>30m</code>, <code>1h</code> или <code>1d</code>.", parse_mode="HTML")
            return
        duration_label = parts[1]
        reason = parts[2] if len(parts) == 3 else None
    elif action in {"ban_forever", "warn", "unban", "unmute", "unwarn"}:
        reason = parts[1] if len(parts) > 1 else None
    else:
        await state.clear()
        await message.answer("Действие устарело. Открой панель заново: /moderation")
        return

    reason_text = reason or "не указана"
    if action in {"ban_forever", "ban_temporary"}:
        changed = ban_user(user_id, duration, reason)
        if not changed:
            await message.answer("Не удалось применить бан.")
            await state.clear()
            return
        period = "навсегда" if duration is None else duration_label
        user_notice = f"🔨 Вы заблокированы в боте на {period}.\nПричина: {reason_text}"
        result = f"🔨 Бан применён: {period}. Причина: {reason_text}"
    elif action == "mute_temporary":
        if not mute_user(user_id, duration, reason):
            await message.answer("Не удалось применить мут.")
            await state.clear()
            return
        user_notice = f"🔇 Вам ограничили отправку сообщений боту на {duration_label}.\nПричина: {reason_text}"
        result = f"🔇 Мут применён на {duration_label}. Причина: {reason_text}"
    elif action == "warn":
        if add_user_warning(user_id, message.from_user.id, reason) is None:
            await message.answer("Не удалось выдать варн.")
            await state.clear()
            return
        warning_count = get_active_warning_count(user_id)
        user_notice = f"⚠️ Вам вынесено предупреждение.\nПричина: {reason_text}\nАктивных варнов: {warning_count}"
        result = f"⚠️ Варн выдан. Активных варнов: {warning_count}. Причина: {reason_text}"
    elif action == "unban":
        if not user["is_banned"]:
            await message.answer("У пользователя нет активного бана.")
            await state.clear()
            return
        unban_user(user_id)
        user_notice = "✅ Ограничение на использование бота снято."
        result = "✅ Бан снят."
    elif action == "unmute":
        if not user["is_muted"]:
            await message.answer("У пользователя нет активного мута.")
            await state.clear()
            return
        unmute_user(user_id)
        user_notice = "🔊 Мут снят. Вы снова можете пользоваться ботом."
        result = "🔊 Мут снят."
    else:
        if not remove_latest_user_warning(user_id):
            await message.answer("У пользователя нет активных варнов.")
            await state.clear()
            return
        warning_count = get_active_warning_count(user_id)
        user_notice = f"✅ Последний варн снят. Активных варнов: {warning_count}."
        result = f"✅ Последний варн снят. Активных осталось: {warning_count}."

    try:
        await bot.send_message(chat_id=user_id, text=user_notice)
    except Exception:
        result += "\n⚠️ Не удалось доставить уведомление в личные сообщения."

    await message.answer(f"{result}\n👤 Пользователь: {user_id}")
    await state.clear()


@router.message(
    F.chat.id == MODERATION_GROUP_ID,
    F.reply_to_message,
    F.reply_to_message.forward_origin,
    F.text,
    ~F.text.startswith("/"),
)
async def reply_to_group_message(
    message: Message,
    bot: Bot,
    is_admin: bool,
):
    if not is_admin:
        return

    forwarded_message = message.reply_to_message
    if forwarded_message.forward_origin is None:
        return

    user_id = get_support_user(forwarded_message.message_id)
    is_support_reply = user_id is not None
    if user_id is None:
        user_id = get_moderation_post_user(forwarded_message.message_id)
    if user_id is None:
        return

    answer_text = message.text.strip()
    if not answer_text:
        await message.reply("Напиши текст ответа на обращение.")
        return

    if is_support_reply:
        answer_id = create_support_answer(user_id, answer_text)

        try:
            await bot.send_message(
                chat_id=user_id,
                text="📩 Вам пришёл ответ на ваше обращение в поддержку.",
                reply_markup=support_answer_kb(answer_id),
            )
        except Exception:
            await message.reply(
                "Не удалось отправить ответ пользователю. "
                "Возможно, он заблокировал бота."
            )
            return

        await message.reply("✅ Ответ на обращение отправлен пользователю.")
        return

    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"📣 Ответ модерации по вашему посту:\n\n{answer_text}",
        )
    except Exception:
        await message.reply(
            "Не удалось отправить ответ пользователю. "
            "Возможно, он заблокировал бота."
        )
        return

    await message.reply("✅ Ответ по посту отправлен пользователю.")


@router.callback_query(F.data.startswith("support_answer:"))
async def show_support_answer(callback: CallbackQuery):
    try:
        answer_id = int(callback.data.split(":", maxsplit=1)[1])
    except (ValueError, AttributeError):
        await callback.answer("Не удалось найти ответ.", show_alert=True)
        return

    answer = get_support_answer(answer_id)
    if answer is None or answer["user_id"] != callback.from_user.id:
        await callback.answer("Ответ не найден.", show_alert=True)
        return

    await callback.message.edit_text(
        f"💬 Ответ на ваше обращение:\n\n{answer['answer_text']}"
    )
    await callback.answer()


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

    if user_id in ADMIN_IDS:
        await message.answer("⛔️ Администраторов нельзя банить.")
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

    if not ban_user(user_id, duration, reason):
        await message.answer("❌ Не удалось применить бан.")
        return

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
    try:
        user_id = int(arguments[1])
    except ValueError:
        await message.answer("Неккоретный тип данных")
        return

    user_data = get_user(user_id)
    if user_data is None:
        await message.answer(f"Пользователь {user_id} не найден в базе данных")
        return

    if not user_data["is_banned"]:
        await message.answer(f"❗️ Пользователь {user_id} не забанен")
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