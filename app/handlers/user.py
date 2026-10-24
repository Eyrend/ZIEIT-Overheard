from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from fsm import PostStates
from keyboards import (
    anonymity_keyboard,
    main_keyboard,
    privilege_keyboard,
    set_time_kb,
)
from aiogram.types import ReplyKeyboardRemove
from message_text import WELCOME_MESSAGE, RECIEVED_POST, SET_TIME_TEXT, MORE, REFUND
from config import MODERATION_GROUP_ID
from sqlwork.support import save_moderation_post, save_support_request
from sqlwork.orders import get_pin_order, update_pin_order_post
router = Router()

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
    username = f"@{data['username']}" if data.get("username") else "None"
    anonymous = "Да" if data.get("anonymous", False) else "Нет"

    if order_id is None:
        moderation_card = await bot.send_message(
            chat_id=MODERATION_GROUP_ID,
            text=RECIEVED_POST.format(
                user_id=data["user_id"],
                username=username,
                anonymous=anonymous,
            ),
        )
        forwarded_post = await bot.forward_message(
            chat_id=MODERATION_GROUP_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
        save_moderation_post(moderation_card.message_id, data["user_id"])
        save_moderation_post(forwarded_post.message_id, data["user_id"])
        await message.answer(
            "✅ Пост отправлен на модерацию!",
            reply_markup=main_keyboard(),
        )
        await state.clear()
        return

    order = get_pin_order(order_id)
    if (
        order is None
        or order["user_id"] != message.from_user.id
        or order["status"] != "pending"
        or order["payment_submitted_at"] is None
    ):
        await message.answer("Не удалось найти оплаченный заказ. Обратись в поддержку.")
        await state.clear()
        return

    if not update_pin_order_post(
        order_id=order_id,
        user_id=message.from_user.id,
        post_chat_id=message.chat.id,
        post_message_id=message.message_id,
    ):
        await message.answer("Не удалось сохранить пост для заказа. Отправь его ещё раз.")
        return

    try:
        stars_payment_text = (
            f"⭐️ Оплачено: {order['stars_amount']} Stars\n"
            if order["payment_method"] == "stars"
            else ""
        )
        payment_status_text = (
            "💳 ОПЛАТА: ПОДТВЕРЖДЕНА TELEGRAM STARS\n"
            if order["payment_method"] == "stars"
            else "💳 ОПЛАТА: ОЖИДАЕТ ПРОВЕРКИ\n"
        )
        moderation_card = await bot.send_message(
            chat_id=MODERATION_GROUP_ID,
            text=(
                "📥 НОВЫЙ ПОСТ НА МОДЕРАЦИЮ\n\n"
                f"👤 ID пользователя: {message.from_user.id}\n"
                f"🔗 Username: {username}\n"
                f"🧾 Номер заказа: №{order_id}\n"
                f"💰 Сумма: {order['amount']} грн\n"
                f"{stars_payment_text}"
                f"⏱ Срок закрепления: {order['hours']} ч.\n\n"
                "📌 ЗАКРЕП: ДА\n"
                f"{payment_status_text}"
                f"🕶️ АНОНИМНО: {anonymous.upper()}\n\n"
                "Проверьте поступление денег и содержание поста. "
                "Скриншот сам по себе не подтверждает оплату."
            ),
        )
        if order["payment_method"] == "card":
            await bot.send_photo(
                chat_id=MODERATION_GROUP_ID,
                photo=order["payment_proof_file_id"],
                caption=f"🧾 Чек по заказу №{order_id}",
            )
        forwarded_post = await bot.forward_message(
            chat_id=MODERATION_GROUP_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
    except Exception:
        await message.answer(
            "Не удалось передать пост и чек модераторам. "
            "Попробуй отправить пост ещё раз."
        )
        return

    save_moderation_post(forwarded_post.message_id, message.from_user.id)
    await message.answer(
        "✅ Пост и чек отправлены на модерацию!",
        reply_markup=main_keyboard(),
    )
    await state.clear()


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
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(
    F.text == "Закрепить 📌",
    PostStates.choosing_privilege,
)
async def pin_post(message: Message, state: FSMContext):
    await state.set_state(PostStates.waiting_for_duration)

    await message.answer(
        "Выбери срок закрепления:",
        reply_markup=ReplyKeyboardRemove(),
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

@router.message(F.text == "Поддержка 🛟")
async def support(message: Message, state: FSMContext):
    await state.set_state(PostStates.support_message)
    await message.answer("🛟 Напиши своё обращение. Оно будет отправлено администрации.")


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

