import json
import logging
import re
import time
from html import escape

from aiogram import Router, F, Bot
from aiogram.types import (
    CallbackQuery,
    LinkPreviewOptions,
    Message,
    MessageEntity,
)
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from fsm import PostStates
from keyboards import (
    birthday_delete_keyboard,
    birthday_list_keyboard,
    birthday_user_keyboard,
    moderation_keyboard,
    rejection_reason_reply,
    support_answer_kb,
)
from sqlwork.support import (
    cancel_post_submission_rejection,
    claim_post_submission_approval,
    claim_post_submission_rejection,
    count_support_requests,
    create_support_answer,
    get_support_answer,
    get_moderation_post_user,
    get_post_submission_by_rejection_prompt,
    mark_post_submission_pinned,
    mark_post_submission_published,
    mark_post_submission_rejected,
    mark_post_submission_unpinned,
    postpone_post_submission_pin,
    restore_post_submission_pending,
    save_post_rejection_prompt,
    get_support_user,
)
from sqlwork.user import (
    add_user_warning,
    ban_user,
    count_birthday_users,
    create_user,
    delete_user_birthday,
    get_active_warning_count,
    get_birthday_user,
    get_birthday_users,
    get_user,
    get_user_by_username,
    get_user_statistics,
    mute_user,
    remove_latest_user_warning,
    set_user_birthday,
    unban_user,
    unmute_user,
)
from config import (
    ADMIN_IDS,
    MODERATION_GROUP_ID,
    PUBLISH_CHANNEL_ID,
)
from sqlwork.orders import get_pin_order_statistics
from utils.birthdays import (
    current_kyiv_date,
    format_stored_birthday,
    parse_birthday_date,
)
from utils.duration import parse_duration


router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("chatid"))
async def show_chat_id(message: Message, is_admin: bool):
    if not is_admin:
        return
    await message.answer(
        f"ID этого чата: <code>{message.chat.id}</code>",
        parse_mode="HTML",
    )


def _utf16_length(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def _post_with_author_quote(submission: dict) -> tuple[str, list[MessageEntity]]:
    if submission.get("post_content_type") is None:
        raise ValueError("This submission has no stored post text")
    post_text = submission.get("post_text") or ""

    entities = [
        MessageEntity.model_validate(entity)
        for entity in json.loads(submission.get("post_entities") or "[]")
    ]
    author_text = f"Автор: {submission['author_label']}"
    separator = "\n\n" if post_text else ""
    text = f"{post_text}{separator}{author_text}"
    if submission["post_content_type"] == "text":
        limit = 4096
    elif submission["post_content_type"] in {
        "photo",
        "video",
        "animation",
        "audio",
        "document",
    }:
        limit = 1024
    else:
        raise ValueError(
            f"Cannot add author quote to {submission['post_content_type']} messages"
        )
    if _utf16_length(text) > limit:
        raise ValueError(
            "The post is too long to add an author quote in the same message"
        )

    quote_offset = _utf16_length(post_text + separator)
    quote_length = _utf16_length(author_text)
    entities.append(
        MessageEntity(
            type="blockquote",
            offset=quote_offset,
            length=quote_length,
        )
    )
    username = submission["author_label"]
    if re.fullmatch(r"@[A-Za-z0-9_]{5,32}", username):
        author_offset = quote_offset + _utf16_length("Автор: ")
        entities.append(
            MessageEntity(
                type="text_link",
                offset=author_offset,
                length=_utf16_length(username),
                url=f"https://t.me/{username[1:]}",
            )
        )
    return text, entities


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


def _birthday_list_content(page: int, users, total_count: int) -> str:
    if not total_count:
        return "🎂 <b>Дни рождения</b>\n\nПока нет сохранённых дат рождения."

    lines = ["🎂 <b>Дни рождения</b>"]
    for index, user in enumerate(users, start=page * 5 + 1):
        username = f"@{user['username']}" if user["username"] else "нет"
        birthday_text = format_stored_birthday(user["birthday"])
        lines.append(
            f"{index}. {escape(user['name'] or 'Без имени')} — {escape(username)}\n"
            f"   ID: <code>{user['telegram_id']}</code> | ДР: {birthday_text}"
        )
    return "\n\n".join(lines)


async def _show_birthday_page(message: Message, page: int, edit: bool = False):
    total_count = count_birthday_users()
    total_pages = max(1, (total_count + 4) // 5)
    page = min(max(page, 0), total_pages - 1)
    users = get_birthday_users(limit=5, offset=page * 5)
    text = _birthday_list_content(page, users, total_count)
    markup = birthday_list_keyboard(users, page, total_pages)
    if edit:
        await message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=markup, parse_mode="HTML")


async def _show_admin_statistics(message: Message):
    user_stats = get_user_statistics(days=7)
    order_stats = get_pin_order_statistics()
    support_count = count_support_requests()
    await message.answer(
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: <b>{user_stats['total_users'] or 0}</b>\n"
        f"🆕 Новых за 7 дней: <b>{user_stats['new_users'] or 0}</b>\n"
        f"🔨 Пользователей с активным баном: <b>{user_stats['banned_users'] or 0}</b>\n"
        f"🎂 Дней рождения указано: <b>{user_stats['birthday_users'] or 0}</b>\n\n"
        f"📌 Заказов на закрепление: <b>{order_stats['total_orders'] or 0}</b>\n"
        f"⏳ Ожидают завершения: <b>{order_stats['pending_orders'] or 0}</b>\n"
        f"✅ Выполнено: <b>{order_stats['fulfilled_orders'] or 0}</b>\n"
        f"📨 Заявок от пользователей: <b>{support_count}</b>\n\n"
        "<i>Учёт новых пользователей начинается после установки обновления.</i>",
        reply_markup=moderation_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("post_review:"))
async def review_post_submission(
    callback: CallbackQuery,
    bot: Bot,
):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа.", show_alert=True)
        return
    if (
        callback.message is None
        or callback.message.chat.id != MODERATION_GROUP_ID
    ):
        await callback.answer("Кнопки работают только в чате модерации.", show_alert=True)
        return

    match = re.fullmatch(r"post_review:(approve|reject):(\d+)", callback.data)
    if match is None:
        await callback.answer("Некорректная заявка.", show_alert=True)
        return

    action, submission_id_text = match.groups()
    submission_id = int(submission_id_text)
    if action == "reject":
        if not claim_post_submission_rejection(submission_id):
            await callback.answer("Заявка уже обработана или устарела.", show_alert=True)
            return
        try:
            prompt = await callback.message.answer(
                f"Напиши причину отказа для заявки №{submission_id} "
                "ответом на это сообщение.",
                reply_markup=rejection_reason_reply(),
            )
        except Exception:
            cancel_post_submission_rejection(submission_id)
            logger.exception(
                "Could not request rejection reason for submission %s",
                submission_id,
            )
            await callback.answer("Не удалось запросить причину отказа.", show_alert=True)
            return
        if not save_post_rejection_prompt(submission_id, prompt.message_id):
            cancel_post_submission_rejection(submission_id)
            await callback.answer("Не удалось сохранить запрос причины.", show_alert=True)
            return
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer("Напиши причину отказа ответом на сообщение бота.")
        return

    submission = claim_post_submission_approval(submission_id)
    if submission is None:
        await callback.answer("Заявка уже обработана или устарела.", show_alert=True)
        return

    try:
        if submission["post_content_type"] == "text":
            post_text = submission.get("post_text") or ""
            post_entities = [
                MessageEntity.model_validate(entity)
                for entity in json.loads(submission.get("post_entities") or "[]")
            ]
            if not submission["anonymous"]:
                post_text, post_entities = _post_with_author_quote(submission)
            published_post = await bot.send_message(
                chat_id=PUBLISH_CHANNEL_ID,
                text=post_text,
                entities=post_entities,
                link_preview_options=LinkPreviewOptions(is_disabled=True),
            )
        elif submission["anonymous"]:
            published_post = await bot.copy_message(
                chat_id=PUBLISH_CHANNEL_ID,
                from_chat_id=submission["source_chat_id"],
                message_id=submission["source_message_id"],
            )
        else:
            post_text, post_entities = _post_with_author_quote(submission)
            published_post = await bot.copy_message(
                chat_id=PUBLISH_CHANNEL_ID,
                from_chat_id=submission["source_chat_id"],
                message_id=submission["source_message_id"],
                caption=post_text,
                caption_entities=post_entities,
            )
    except Exception as error:
        if not restore_post_submission_pending(submission_id):
            logger.error(
                "Could not restore submission %s after publication failed",
                submission_id,
            )
        logger.exception("Could not publish submission %s", submission_id)
        error_text = (
            "Не удалось добавить цитату автора в это сообщение. "
            "Попроси автора прислать более короткий текст или обычное фото/видео."
            if isinstance(error, ValueError)
            else "Не удалось опубликовать пост. "
            "Проверь права бота в канале и попробуй снова."
        )
        await callback.answer(error_text, show_alert=True)
        return

    published_at = int(time.time())
    unpin_at = (
        published_at + submission["pin_hours"] * 3600
        if submission["pin_hours"] is not None
        else None
    )
    if not mark_post_submission_published(
        submission_id,
        published_post.message_id,
        unpin_at,
    ):
        logger.error(
            "Post %s was published but its state could not be saved",
            submission_id,
        )
        await callback.answer(
            "Пост опубликован, но не удалось сохранить результат в базе.",
            show_alert=True,
        )
        return

    follow_up_errors = []
    if submission["pin_hours"] is not None:
        try:
            await bot.pin_chat_message(
                chat_id=PUBLISH_CHANNEL_ID,
                message_id=published_post.message_id,
                disable_notification=True,
            )
        except Exception:
            follow_up_errors.append("не удалось закрепить пост")
            logger.exception("Could not pin submission %s", submission_id)
            if not postpone_post_submission_pin(
                submission_id,
                int(time.time()) + 600,
            ):
                logger.error(
                    "Could not schedule pin retry for submission %s",
                    submission_id,
                )
        else:
            if not mark_post_submission_pinned(submission_id):
                logger.error(
                    "Could not record pin for submission %s",
                    submission_id,
                )

    result_text = f"✅ Заявка №{submission_id} одобрена и опубликована."
    if follow_up_errors:
        result_text += "\n⚠️ " + "; ".join(follow_up_errors) + "."
    try:
        await callback.message.edit_text(result_text, reply_markup=None)
    except Exception:
        logger.exception("Could not update review message for submission %s", submission_id)
    try:
        await bot.send_message(
            chat_id=submission["user_id"],
            text="✅ Твой пост одобрен и опубликован в канале.",
        )
    except Exception:
        logger.exception("Could not notify author for submission %s", submission_id)
    await callback.answer("Пост опубликован.")


@router.message(
    F.chat.id == MODERATION_GROUP_ID,
    F.reply_to_message,
    F.reply_to_message.message_id.func(
        lambda message_id: (
            get_post_submission_by_rejection_prompt(message_id) is not None
        )
    ),
    F.text,
)
async def receive_post_rejection_reason(
    message: Message,
    bot: Bot,
    is_admin: bool,
):
    if not is_admin:
        return

    submission = get_post_submission_by_rejection_prompt(
        message.reply_to_message.message_id
    )
    if submission is None:
        return

    reason = message.text.strip()
    if not reason:
        await message.reply("Причина не должна быть пустой. Напиши её ещё раз.")
        return

    try:
        await bot.send_message(
            chat_id=submission["user_id"],
            text=f"❌ Твой пост отклонён.\nПричина: {reason}",
        )
    except Exception:
        logger.exception(
            "Could not deliver rejection reason for submission %s",
            submission["id"],
        )
        await message.reply(
            "Не удалось отправить причину автору. Проверь, что он не заблокировал бота."
        )
        return

    if not mark_post_submission_rejected(submission["id"], reason):
        await message.reply(
            "Причина отправлена, но не удалось сохранить решение. "
            "Проверь заявку в базе перед повторной обработкой."
        )
        logger.error("Could not mark submission %s as rejected", submission["id"])
        return

    review_message_id = submission.get("review_message_id")
    if review_message_id is not None:
        try:
            await bot.edit_message_text(
                chat_id=MODERATION_GROUP_ID,
                message_id=review_message_id,
                text=f"❌ Заявка №{submission['id']} отклонена.",
                reply_markup=None,
            )
        except Exception:
            logger.exception(
                "Could not update review message for submission %s",
                submission["id"],
            )
    await message.reply("Причина отправлена автору. Заявка отклонена.")


@router.callback_query(F.data.startswith("mod:"))
async def choose_moderation_action(
    callback: CallbackQuery,
    state: FSMContext,
):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    if (
        callback.message is None
        or callback.message.chat.id != MODERATION_GROUP_ID
    ):
        await callback.answer("Панель работает только в группе модерации.", show_alert=True)
        return

    action = callback.data.removeprefix("mod:")
    if action not in {
        "ban_forever", "ban_temporary", "mute_temporary", "warn",
        "unban", "unmute", "unwarn", "birthdays", "stats",
    }:
        await callback.answer("Неизвестное действие.", show_alert=True)
        return

    if action == "stats":
        await _show_admin_statistics(callback.message)
        await callback.answer()
        return

    if action == "birthdays":
        await _show_birthday_page(callback.message, page=0)
        await callback.answer()
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


@router.callback_query(F.data.startswith("birthday:"))
async def manage_birthdays(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа.", show_alert=True)
        return
    if (
        callback.message is None
        or callback.message.chat.id != MODERATION_GROUP_ID
    ):
        await callback.answer("Раздел работает только в группе модерации.", show_alert=True)
        return

    parts = callback.data.split(":")
    action = parts[1] if len(parts) > 1 else ""
    if action == "noop":
        await callback.answer()
        return
    if action == "back":
        await callback.message.edit_text(
            "⚖️ <b>Модерация пользователей</b>",
            reply_markup=moderation_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        return
    if action == "page" and len(parts) == 3:
        try:
            page = int(parts[2])
        except ValueError:
            await callback.answer("Некорректная страница.", show_alert=True)
            return
        await _show_birthday_page(callback.message, page, edit=True)
        await callback.answer()
        return
    if action in {"user", "edit", "delete", "confirm_delete"} and len(parts) == 4:
        try:
            user_id = int(parts[2])
            page = int(parts[3])
        except ValueError:
            await callback.answer("Некорректные данные пользователя.", show_alert=True)
            return
        user = get_birthday_user(user_id)
        if user is None:
            await callback.answer("Дата рождения не найдена.", show_alert=True)
            await _show_birthday_page(callback.message, page, edit=True)
            return

        if action == "user":
            username = f"@{user['username']}" if user["username"] else "не указан"
            birthday_text = format_stored_birthday(user["birthday"])
            await callback.message.edit_text(
                "🎂 <b>Дата рождения пользователя</b>\n\n"
                f"Никнейм: {escape(user['name'] or 'Без имени')}\n"
                f"Username: {escape(username)}\n"
                f"ID: <code>{user_id}</code>\n"
                f"Дата рождения: {birthday_text}",
                reply_markup=birthday_user_keyboard(user_id, page),
                parse_mode="HTML",
            )
        elif action == "edit":
            await state.update_data(
                birthday_edit_user_id=user_id,
                birthday_edit_page=page,
            )
            await state.set_state(PostStates.moderation_birthday_edit)
            await callback.message.answer(
                f"Введи новую дату рождения для пользователя {user_id} "
                "в формате ДД.ММ.ГГГГ. Для отмены напиши /cancel."
            )
        elif action == "delete":
            await callback.message.edit_text(
                f"Удалить дату рождения пользователя {user_id}?",
                reply_markup=birthday_delete_keyboard(user_id, page),
            )
        else:
            if not delete_user_birthday(user_id):
                await callback.answer("Не удалось удалить дату рождения.", show_alert=True)
                return
            await callback.answer("Дата рождения удалена.")
            await _show_birthday_page(callback.message, page, edit=True)
            return
        await callback.answer()
        return

    await callback.answer("Неизвестное действие.", show_alert=True)


@router.message(
    F.chat.id == MODERATION_GROUP_ID,
    PostStates.moderation_birthday_edit,
)
async def edit_user_birthday(message: Message, state: FSMContext, is_admin: bool):
    if not is_admin:
        await state.clear()
        return

    text = (message.text or "").strip()
    if text.lower() in {"/cancel", "отмена"}:
        await state.clear()
        await message.answer("Изменение даты рождения отменено.")
        return

    birthday = parse_birthday_date(text)
    if birthday is None:
        await message.answer("Некорректная дата. Введи её в формате ДД.ММ.ГГГГ.")
        return
    if birthday > current_kyiv_date():
        await message.answer("Дата рождения не может быть в будущем.")
        return

    data = await state.get_data()
    user_id = data.get("birthday_edit_user_id")
    page = data.get("birthday_edit_page", 0)
    user = get_birthday_user(user_id) if isinstance(user_id, int) else None
    if user is None:
        await state.clear()
        await message.answer("Пользователь не найден или его дата рождения уже удалена.")
        return
    if not set_user_birthday(
        user_id,
        birthday.isoformat(),
        name=user["name"],
        username=user["username"],
    ):
        await message.answer("Не удалось сохранить дату рождения. Попробуй ещё раз.")
        return

    await state.clear()
    await message.answer(
        f"✅ Дата рождения пользователя {user_id} изменена на "
        f"{birthday.strftime('%d.%m.%Y')}."
    )
    await _show_birthday_page(message, page=page if isinstance(page, int) else 0)


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


@router.message(
    Command("ban"),
    F.chat.id == MODERATION_GROUP_ID,
)
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

    


@router.message(
    Command('unban'),
    F.chat.id == MODERATION_GROUP_ID,
)
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

@router.message(
    Command("reply"),
    F.chat.id == MODERATION_GROUP_ID,
)
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