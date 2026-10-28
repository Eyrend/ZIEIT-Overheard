import logging
import json

from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from fsm import PostStates
from keyboards import (
    MAIN_MENU_BUTTON,
    anonymity_keyboard,
    birthday_input_keyboard,
    ideas_and_listings_keyboard,
    main_keyboard,
    post_preview_keyboard,
    post_review_keyboard,
    privilege_keyboard,
    return_to_menu_keyboard,
    set_time_kb,
)
from message_text import WELCOME_MESSAGE, RECIEVED_POST, SET_TIME_TEXT, MORE, REFUND
from config import MODERATION_GROUP_ID
from sqlwork.support import (
    create_post_submission,
    save_moderation_post,
    save_post_review_message,
    save_support_request,
)
from sqlwork.orders import cancel_pin_order, get_pin_order, update_pin_order_post
from sqlwork.user import get_birthday_user, set_user_birthday
from utils.birthdays import (
    age_at_next_birthday,
    birthday_reminder_offset,
    calculate_age,
    current_kyiv_date,
    format_birthday_countdown,
    format_days_remaining,
    format_stored_birthday,
    format_years,
    parse_birthday_date,
)
router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == MAIN_MENU_BUTTON, F.chat.type == "private")
async def return_to_main_menu(message: Message, state: FSMContext):
    current_state = await state.get_state()
    data = await state.get_data()

    if current_state == PostStates.waiting_for_pay.state:
        order_id = data.get("order_id")
        order = get_pin_order(order_id) if isinstance(order_id, int) else None
        if (
            order is not None
            and order["status"] == "pending"
            and order["payment_submitted_at"] is None
        ):
            if not cancel_pin_order(order_id):
                await message.answer(
                    "Не удалось отменить ожидающий заказ. "
                    "Используй кнопку отмены под сообщением заказа."
                )
                return
            from payment_init import stop_payment_countdown

            stop_payment_countdown(order_id)

    await state.clear()
    await message.answer(
        "🏠 Ты вернулся в главное меню.",
        reply_markup=main_keyboard(),
    )


# Хэндлер команды старт
@router.message(CommandStart(), F.chat.type == "private")
async def welcome(
    message: Message,
    command: CommandObject,
    state: FSMContext,
):
    await state.clear()
    
    await message.answer(WELCOME_MESSAGE.format(name=message.from_user.first_name),
                         reply_markup=main_keyboard())


@router.message(F.text == "Дата рождения 🎂", F.chat.type == "private")
async def ask_for_birthday(message: Message, state: FSMContext):
    await state.clear()
    existing_birthday = get_birthday_user(message.from_user.id)
    if existing_birthday is None:
        personal_status = "Дата рождения пока не указана."
    else:
        birthday = parse_birthday_date(
            format_stored_birthday(existing_birthday["birthday"])
        )
        if birthday is None:
            personal_status = "Дата рождения уже указана, но её не удалось прочитать."
        else:
            personal_status = (
                f"Сейчас указана дата: {birthday.strftime('%d.%m.%Y')}.\n"
                f"Возраст: {format_years(calculate_age(birthday))}.\n"
                f"{format_birthday_countdown(birthday)}"
            )

    await message.answer(
        "🎂 Укажи дату рождения — в этот день тебя поздравят в канале, "
        "а бот заранее напомнит о празднике. Дату увидит администрация, "
        "чтобы подготовить поздравление."
    )
    await state.set_state(PostStates.waiting_for_birthday)
    await message.answer(
        f"{personal_status}\n\n"
        "Чтобы указать или изменить дату, отправь её в формате ДД.ММ.ГГГГ, "
        "например: 05.11.2004.\n"
        "Напомнить модераторам можно за день до дня рождения, в сам день "
        "и на следующий день.",
        reply_markup=birthday_input_keyboard(),
    )


async def send_birthday_reminder_to_moderators(user, bot: Bot) -> int | None:
    birthday = parse_birthday_date(format_stored_birthday(user["birthday"]))
    if birthday is None:
        return None

    reminder_offset = birthday_reminder_offset(birthday)
    if reminder_offset not in {-1, 0, 1}:
        return reminder_offset

    if reminder_offset == 1:
        birthday_age = age_at_next_birthday(birthday)
    else:
        birthday_age = calculate_age(birthday)
    username = f"@{user['username']}" if user["username"] else "отсутствует"
    moderation_card = await bot.send_message(
        chat_id=MODERATION_GROUP_ID,
        text=(
            "📣 Пользователь напомнил о своём дне рождения\n\n"
            f"👤 Имя: {user['name'] or 'Без имени'}\n"
            f"🆔 Telegram ID: {user['telegram_id']}\n"
            f"🔗 Username: {username}\n"
            f"📅 Дата рождения: {birthday.strftime('%d.%m.%Y')}\n"
            f"🎉 Возраст: {format_years(birthday_age)}"
        ),
    )
    return reminder_offset


def birthday_reminder_response(reminder_offset: int) -> str:
    if reminder_offset == 1:
        return "✅ Напоминание отправлено модераторам: день рождения завтра."
    if reminder_offset == 0:
        return "✅ Напоминание отправлено модераторам: сегодня день рождения."
    if reminder_offset == -1:
        return "✅ Напоминание отправлено модераторам: день рождения был вчера."
    return (
        f"{format_days_remaining(reminder_offset)} "
        "Напоминание модераторам можно отправить за день до ДР, в сам день "
        "или на следующий день."
    )


@router.message(
    F.text == "📣 Напомнить модераторам",
    F.chat.type == "private",
)
async def remind_moderators_about_birthday_message(
    message: Message,
    bot: Bot,
):
    user = get_birthday_user(message.from_user.id)
    if user is None:
        await message.answer(
            "Сначала укажи дату рождения. Отправь её в формате ДД.ММ.ГГГГ "
            "или нажми «🏠 В главное меню»."
        )
        return

    days_until_birthday = await send_birthday_reminder_to_moderators(user, bot)
    if days_until_birthday is None:
        await message.answer(
            "Не удалось прочитать дату рождения. Укажи её заново в формате ДД.ММ.ГГГГ."
        )
        return

    await message.answer(
        f"{birthday_reminder_response(days_until_birthday)} "
        "Можешь указать или изменить дату рождения.",
        reply_markup=birthday_input_keyboard(),
    )


# Хэндлер Предложить пост 🗒️
@router.message(F.text == 'Предложить пост 🗒️', F.chat.type =='private')
async def suggest_post(message: Message, state: FSMContext):
    await state.clear()
    await state.update_data(
        user_id=message.from_user.id,
        username=message.from_user.username,
    )
    await state.set_state(PostStates.choosing_anonymity)
    await message.answer(
        "Как опубликовать пост?",
        reply_markup=anonymity_keyboard(),
    )

@router.message(PostStates.waiting_for_post)
async def receive_post(message: Message, state: FSMContext, bot: Bot):
    if message.text and message.text.startswith("/"):
        await message.answer("Отправьте пост")
        return

    data = await state.get_data()
    order_id = data.get("order_id")
    if order_id is not None:
        order = get_pin_order(order_id) if isinstance(order_id, int) else None
        if (
            order is None
            or order["user_id"] != message.from_user.id
            or order["status"] != "pending"
            or order["payment_submitted_at"] is None
        ):
            await message.answer(
                "Не удалось найти заказ с подтверждённой оплатой или победой. "
                "Обратись в поддержку."
            )
            await state.clear()
            return

    preview = await bot.copy_message(
        chat_id=message.chat.id,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
        reply_markup=post_preview_keyboard(),
    )
    await state.update_data(
        preview_chat_id=message.chat.id,
        preview_message_id=preview.message_id,
        preview_source_message_id=message.message_id,
        post_text=message.text or message.caption,
        post_entities=[
            entity.model_dump(mode="json", exclude_none=True)
            for entity in (message.entities or message.caption_entities or [])
        ],
        post_content_type=message.content_type,
    )
    await state.set_state(PostStates.post_preview)
    await message.answer(
        "Предпросмотр публикации. Выбери, что делать дальше:",
        reply_markup=return_to_menu_keyboard(),
    )


@router.callback_query(F.data.startswith("post_preview:"))
async def handle_post_preview(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
):
    if callback.message is None:
        await callback.answer("Предпросмотр недоступен.", show_alert=True)
        return

    data = await state.get_data()
    if (
        await state.get_state() != PostStates.post_preview.state
        or data.get("user_id") != callback.from_user.id
        or data.get("preview_chat_id") != callback.message.chat.id
        or data.get("preview_message_id") != callback.message.message_id
    ):
        await callback.answer("Предпросмотр устарел. Создай публикацию заново.", show_alert=True)
        return

    action = callback.data.removeprefix("post_preview:")
    if action == "edit":
        await callback.message.edit_reply_markup(reply_markup=None)
        await state.set_state(PostStates.waiting_for_post)
        await callback.message.answer(
            "Отправь изменённый текст или медиа для публикации.",
            reply_markup=return_to_menu_keyboard(),
        )
        await callback.answer()
        return

    if action == "cancel":
        order_id = data.get("order_id")
        notice = "Публикация отменена."
        if isinstance(order_id, int):
            order = get_pin_order(order_id)
            if order is not None and order["payment_submitted_at"] is not None:
                if order["payment_method"] == "giveaway":
                    notice += (
                        " Заказ с подтверждением победы не отменяется автоматически; "
                        "по вопросам напиши в поддержку."
                    )
                else:
                    notice += (
                        " Оплата не возвращается автоматически; "
                        "по вопросам напиши в поддержку."
                    )
        await state.clear()
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(notice, reply_markup=main_keyboard())
        await callback.answer()
        return

    if action != "submit":
        await callback.answer("Неизвестное действие.", show_alert=True)
        return

    user_id = callback.from_user.id
    source_chat_id = data.get("preview_chat_id")
    source_message_id = data.get("preview_source_message_id")
    if not isinstance(source_chat_id, int) or not isinstance(source_message_id, int):
        await callback.answer("Не удалось найти исходную публикацию.", show_alert=True)
        return

    order_id = data.get("order_id")
    username = f"@{data['username']}" if data.get("username") else "None"
    anonymous = "Да" if data.get("anonymous", False) else "Нет"

    order = None
    if order_id is not None:
        order = get_pin_order(order_id) if isinstance(order_id, int) else None
        if (
            order is None
            or order["user_id"] != user_id
            or order["status"] != "pending"
            or order["payment_submitted_at"] is None
        ):
            await callback.answer(
                "Не удалось найти заказ с подтверждённой оплатой или победой.",
                show_alert=True,
            )
            return
        if not update_pin_order_post(
            order_id=order_id,
            user_id=user_id,
            post_chat_id=source_chat_id,
            post_message_id=source_message_id,
        ):
            await callback.answer("Не удалось сохранить пост для заказа.", show_alert=True)
            return

    failure_stage = "подготовка карточки"
    try:
        if order is None:
            failure_stage = "отправка карточки модераторам"
            moderation_card = await bot.send_message(
                chat_id=MODERATION_GROUP_ID,
                text=RECIEVED_POST.format(
                    user_id=user_id,
                    username=username,
                    anonymous=anonymous,
                ),
            )
        else:
            is_giveaway = order["payment_method"] == "giveaway"
            stars_payment_text = (
                f"⭐️ Оплачено: {order['stars_amount']} Stars\n"
                if order["payment_method"] == "stars"
                else ""
            )
            payment_status_text = (
                "💳 ОПЛАТА: ПОДТВЕРЖДЕНА TELEGRAM STARS\n"
                if order["payment_method"] == "stars"
                else (
                    "🏆 ПОБЕДА В РОЗЫГРЫШЕ: ОЖИДАЕТ ПРОВЕРКИ\n"
                    if is_giveaway
                    else "💳 ОПЛАТА: ОЖИДАЕТ ПРОВЕРКИ\n"
                )
            )
            amount_text = (
                "🎁 Стоимость: бесплатно (победитель розыгрыша)\n"
                if is_giveaway
                else f"💰 Сумма: {order['amount']} грн\n"
            )
            moderator_note = {
                "giveaway": "Проверьте скриншот выигрыша и содержание поста.",
                "stars": "Оплата Telegram Stars подтверждена автоматически. "
                "Проверьте содержание поста.",
                "card": "Проверьте поступление денег и содержание поста. "
                "Скриншот сам по себе не подтверждает оплату.",
            }[order["payment_method"]]
            failure_stage = "отправка карточки заказа модераторам"
            moderation_card = await bot.send_message(
                chat_id=MODERATION_GROUP_ID,
                text=(
                    "📥 НОВЫЙ ПОСТ НА МОДЕРАЦИЮ\n\n"
                    f"👤 ID пользователя: {user_id}\n"
                    f"🔗 Username: {username}\n"
                    f"🧾 Номер заказа: №{order_id}\n"
                    f"{amount_text}"
                    f"{stars_payment_text}"
                    f"⏱ Срок закрепления: {order['hours']} ч.\n\n"
                    "📌 ЗАКРЕП: ДА\n"
                    f"{payment_status_text}"
                    f"🕶️ АНОНИМНО: {anonymous.upper()}\n\n"
                    f"{moderator_note}"
                ),
            )
            if order["payment_method"] in {"card", "giveaway"}:
                failure_stage = "отправка чека/скриншота модераторам"
                await bot.send_photo(
                    chat_id=MODERATION_GROUP_ID,
                    photo=order["payment_proof_file_id"],
                    caption=(
                        f"🏆 Скриншот победы по заказу №{order_id}"
                        if is_giveaway
                        else f"🧾 Чек по заказу №{order_id}"
                    ),
                )
        failure_stage = "сохранение карточки модерации"
        save_moderation_post(moderation_card.message_id, user_id)
        failure_stage = "пересылка поста модераторам"
        forwarded_post = await bot.forward_message(
            chat_id=MODERATION_GROUP_ID,
            from_chat_id=source_chat_id,
            message_id=source_message_id,
        )
        failure_stage = "сохранение пересланного поста"
        save_moderation_post(forwarded_post.message_id, user_id)
        failure_stage = "сохранение заявки"
        submission_id = create_post_submission(
            user_id=user_id,
            source_chat_id=source_chat_id,
            source_message_id=source_message_id,
            post_text=data.get("post_text"),
            post_entities=data.get("post_entities", []),
            post_content_type=data.get("post_content_type", "unknown"),
            anonymous=bool(data.get("anonymous", False)),
            author_label=(
                f"@{data['username']}"
                if data.get("username")
                else callback.from_user.full_name
            ),
            order_id=order_id if isinstance(order_id, int) else None,
            pin_hours=order["hours"] if order is not None else None,
        )
        failure_stage = "отправка кнопок модерации"
        review_message = await bot.send_message(
            chat_id=MODERATION_GROUP_ID,
            text=(
                f"🗳 Заявка №{submission_id} ожидает решения.\n"
                "Одобрить публикацию в канал или отклонить её."
            ),
            reply_markup=post_review_keyboard(submission_id),
        )
        failure_stage = "сохранение сообщения с кнопками модерации"
        if not save_post_review_message(
            submission_id,
            review_message.message_id,
        ):
            raise RuntimeError(
                f"Could not save review message for submission {submission_id}"
            )
    except Exception as error:
        logger.exception(
            "Could not send post submission %s to moderation at stage %s "
            "(moderation_chat_id=%s)",
            order_id,
            failure_stage,
            MODERATION_GROUP_ID,
        )
        error_detail = " ".join(str(error).split())[:240]
        await callback.message.answer(
            f"Не удалось передать заявку модераторам на этапе «{failure_stage}». "
            f"Ошибка: {type(error).__name__}"
            f"{f' — {error_detail}' if error_detail else ''}.\n"
            "Попробуй отправить публикацию ещё раз."
        )
        await callback.answer()
        return

    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "✅ Пост и подтверждение отправлены на модерацию!" if order_id is not None
        else "✅ Пост отправлен на модерацию!",
        reply_markup=main_keyboard(),
    )
    await callback.answer()


@router.message(
    F.text.in_({"Анонимно", "Публично"}),
    PostStates.choosing_anonymity,
)
async def choose_anonymity(message: Message, state: FSMContext):
    await state.update_data(
        anonymous=message.text == "Анонимно",
        user_id=message.from_user.id,
        username=message.from_user.username,
    )
    await state.set_state(PostStates.choosing_privilege)

    await message.answer(
        "Выбери вариант публикации:",
        reply_markup=privilege_keyboard(),
    )


@router.message(
    F.text == "Без привилегий ❌",
    PostStates.choosing_privilege)
async def no_privileges(
    message: Message,
    state: FSMContext,
    ):
    await state.set_state(PostStates.waiting_for_post)
    await message.answer(
        "Теперь отправь пост:",
        reply_markup=return_to_menu_keyboard(),
    )


@router.message(
    F.text == "Закрепить 📌",
    PostStates.choosing_privilege,
)
async def pin_post(message: Message, state: FSMContext):
    await state.set_state(PostStates.waiting_for_duration)

    await message.answer(
        "Выбери срок закрепления:",
        reply_markup=return_to_menu_keyboard(),
    )
    await message.answer(
        text=SET_TIME_TEXT,
        reply_markup=set_time_kb(),
    )

@router.message(F.text == 'Подробнее 📲')
async def send_more(message: Message):
    await message.answer(MORE)

@router.message(F.text == 'Условия возврата ⛓️')
async def send_more(message: Message):
    await message.answer(REFUND)


@router.message(PostStates.waiting_for_birthday, F.chat.type == "private")
async def save_birthday(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if text.lower() in {"/cancel", "отмена"}:
        await state.clear()
        await message.answer("Ввод даты рождения отменён.", reply_markup=main_keyboard())
        return

    birthday = parse_birthday_date(text)
    if birthday is None:
        await message.answer("Некорректная дата. Введи её в формате ДД.ММ.ГГГГ.")
        return

    if birthday > current_kyiv_date():
        await message.answer("Дата рождения не может быть в будущем.")
        return

    saved = set_user_birthday(
        telegram_id=message.from_user.id,
        birthday=birthday.isoformat(),
        name=message.from_user.first_name,
        username=message.from_user.username,
    )
    if not saved:
        await message.answer("Не удалось сохранить дату рождения. Попробуй ещё раз.")
        return

    await state.clear()
    await message.answer(
        f"✅ Дата рождения сохранена: {birthday.strftime('%d.%m.%Y')}.\n"
        f"{format_birthday_countdown(birthday)}",
        reply_markup=main_keyboard(),
    )


@router.message(F.text == "Поддержка 🛟")
async def support(message: Message, state: FSMContext):
    await state.set_state(PostStates.support_message)
    await message.answer(
        "🛟 Напиши своё обращение. Оно будет отправлено администрации.",
        reply_markup=return_to_menu_keyboard(),
    )


@router.message(F.text == "Идеи и объявления 💡", F.chat.type == "private")
async def show_ideas_and_listings(message: Message):
    await message.answer(
        "Что хочешь сделать?",
        reply_markup=ideas_and_listings_keyboard(),
    )


@router.callback_query(F.data.startswith("user_option:"))
async def choose_user_option(callback: CallbackQuery, state: FSMContext):
    if callback.message is None or callback.message.chat.type != "private":
        await callback.answer("Этот выбор доступен только в личном чате.", show_alert=True)
        return
    if callback.from_user.id != callback.message.chat.id:
        await callback.answer("Это меню предназначено для пользователя бота.", show_alert=True)
        return

    action = callback.data.removeprefix("user_option:")
    options = {
        "lost_item": (
            PostStates.lost_item,
            "Опиши потерянную или найденную вещь: что это, где и когда потерялась "
            "или была найдена, как с тобой связаться. Можно приложить фото.",
        ),
        "improvement": (
            PostStates.suggest_improvement,
            "Опиши, что ты предлагаешь улучшить в боте. "
            "Можно отправить текст или медиа.",
        ),
    }
    option = options.get(action)
    if option is None:
        await callback.answer("Неизвестный вариант.", show_alert=True)
        return

    await state.clear()
    await state.set_state(option[0])
    await callback.message.answer(
        option[1],
        reply_markup=return_to_menu_keyboard(),
    )
    await callback.answer()


async def forward_user_request(
    message: Message,
    state: FSMContext,
    bot: Bot,
    title: str,
    confirmation: str,
):
    user = message.from_user
    await bot.send_message(
        chat_id=MODERATION_GROUP_ID,
        text=(
            f"{title}\n\n"
            f"👤 Пользователь: {user.full_name}\n"
            f"🆔 Telegram ID: {user.id}\n"
            f"🔗 Username: @{user.username if user.username else 'отсутствует'}"
        ),
    )
    forwarded_message = await bot.forward_message(
        chat_id=MODERATION_GROUP_ID,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
    )
    save_support_request(
        group_message_id=forwarded_message.message_id,
        user_id=user.id,
    )
    await state.clear()
    await message.answer(confirmation, reply_markup=main_keyboard())


@router.message(PostStates.suggest_improvement, F.chat.type == "private")
async def receive_improvement(message: Message, state: FSMContext, bot: Bot):
    await forward_user_request(
        message,
        state,
        bot,
        "💡 ПРЕДЛОЖЕНИЕ ПО УЛУЧШЕНИЮ БОТА",
        "✅ Предложение отправлено администрации. Спасибо!",
    )


@router.message(PostStates.lost_item, F.chat.type == "private")
async def receive_lost_item(message: Message, state: FSMContext, bot: Bot):
    await forward_user_request(
        message,
        state,
        bot,
        "🔎 ПОТЕРЯННАЯ ИЛИ НАЙДЕННАЯ ВЕЩЬ",
        "✅ Информация отправлена администрации. Если появятся новости, мы свяжемся с тобой.",
    )


@router.message(PostStates.support_message)
async def receive_support_message(
    message: Message,
    state: FSMContext,
    bot: Bot,
):
    user = message.from_user

    await bot.send_message(
        chat_id=MODERATION_GROUP_ID,
        text=(
            "🛟 ОБРАЩЕНИЕ В ПОДДЕРЖКУ\n\n"
            f"👤 Пользователь: {user.full_name}\n"
            f"🆔 Telegram ID: {user.id}\n"
            f"🔗 Username: @{user.username if user.username else 'отсутствует'}"
        ),
    )

    forwarded_message = await bot.forward_message(
        chat_id=MODERATION_GROUP_ID,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
    )
    save_support_request(
        group_message_id=forwarded_message.message_id,
        user_id=user.id,
    )

    await message.answer(
        "✅ Обращение отправлено!",
        reply_markup=main_keyboard(),
    )
    await state.clear()
