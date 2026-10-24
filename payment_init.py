
import re

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from fsm import PostStates
from config import (
    MODERATION_GROUP_ID,
    IBAN,
    PAYMENT_RECIPIENT,
    PIN_OPTIONS,
)
from keyboards import (
    cancel_payment_kb,
    main_keyboard,
)
from sqlwork.orders import (
    create_pin_order,
    get_pin_order,
    cancel_pin_order,
    mark_payment_submitted,
)

router = Router()


@router.callback_query(
    PostStates.waiting_for_duration,
    F.data.in_(PIN_OPTIONS),
)
async def choose_duration(
    callback: CallbackQuery,
    state: FSMContext,
):
    data = await state.get_data()

    if not all(
        key in data for key in ("chat_id", "message_id", "user_id")
    ):
        await callback.answer(
            "Не удалось найти исходный пост",
            show_alert=True,
        )
        await state.clear()
        return

    if callback.from_user.id != data["user_id"]:
        await callback.answer("Это не твой заказ.", show_alert=True)
        return

    hours, amount = PIN_OPTIONS[callback.data]

    order_id = create_pin_order(
        user_id=callback.from_user.id,
        post_chat_id=data["chat_id"],
        post_message_id=data["message_id"],
        hours=hours,
        amount=amount,
    )

    await state.update_data(order_id=order_id)
    await state.set_state(PostStates.waiting_for_pay)

    payment_text = (
        f"📌 Заказ на закрепление №{order_id}\n\n"
        f"⏱ Длительность: {hours} ч.\n"
        f"💳 К оплате: {amount} грн\n\n"
        f"Получатель: {PAYMENT_RECIPIENT}\n"
        f"IBAN:\n<code>{IBAN}</code>\n\n"
        "Переведи указанную сумму на этот счёт.\n"
        "После перевода отправь сюда фотографию чека.\n\n"
        "Отменить заказ можно кнопкой ниже.\n"
        "Отправленный чек будет проверен модераторами."
    )

    await callback.message.answer(
        payment_text,
        reply_markup=cancel_payment_kb(order_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(
    PostStates.waiting_for_pay,
    F.photo,
)
async def receive_payment_photo(
    message: Message,
    state: FSMContext,
    bot: Bot,
):
    data = await state.get_data()
    order_id = data.get("order_id")

    if order_id is None:
        await message.answer(
            "Не удалось найти заказ."
        )
        return

    order = get_pin_order(order_id)

    if (
        order is None
        or order["user_id"] != message.from_user.id
        or order["status"] != "pending"
    ):
        await message.answer(
            "Этот заказ больше не ожидает подтверждения чека."
        )
        await state.clear()
        return

    photo_file_id = message.photo[-1].file_id

    saved = mark_payment_submitted(
        order_id=order_id,
        user_id=message.from_user.id,
        file_id=photo_file_id,
    )

    if not saved:
        await message.answer(
            "Чек уже отправлен или заказ отменён."
        )
        return


    try:
        # 1. Пересылаем исходный пост пользователя
        await bot.forward_message(
            chat_id=MODERATION_GROUP_ID,
            from_chat_id=order["post_chat_id"],
            message_id=order["post_message_id"],
        )

        # 2. Отправляем фотографию чека
        await bot.send_photo(
            chat_id=MODERATION_GROUP_ID,
            photo=photo_file_id,
            caption=f"🧾 Чек по заказу №{order_id}",
        )

        # 3. Отправляем информацию для модераторов
        await bot.send_message(
            chat_id=MODERATION_GROUP_ID,
            text=(
                "📥 НОВЫЙ ПОСТ НА МОДЕРАЦИЮ\n\n"
                f"👤 ID пользователя: {message.from_user.id}\n"
                f"🧾 Номер заказа: №{order_id}\n"
                f"💰 Сумма: {order['amount']} грн\n"
                f"⏱ Срок закрепления: {order['hours']} ч.\n\n"
                "📌 НУЖНО ЗАКРЕПИТЬ\n"
                "💳 ОПЛАТА: ОЖИДАЕТ ПРОВЕРКИ\n\n"
                "Проверьте поступление денег и содержание поста. "
                "Скриншот сам по себе не подтверждает оплату."
            ),
        )

    except Exception:
        await message.answer(
            "Не удалось передать все материалы модераторам. "
            f"Номер заказа: №{order_id}. Сообщи администратору."
        )
        return


    await message.answer(
        "✅ Фотография чека получена и отправлена модераторам.\n"
        "Оплата пока не подтверждена — дождись проверки.",
        reply_markup=main_keyboard(),
    )
    await state.clear()


@router.message(PostStates.waiting_for_pay)
async def payment_requires_photo(message: Message):
    await message.answer(
        "Ожидаю фотографию чека.\n"
        "Отправь её как фото или нажми «Отменить оплату» "
        "под сообщением с реквизитами."
    )


@router.callback_query(F.data.startswith("cancel_payment:"))
async def cancel_payment(
    callback: CallbackQuery,
    state: FSMContext,
):
    match = re.fullmatch(r"cancel_payment:(\d+)", callback.data)

    if match is None:
        await callback.answer("Некорректный номер заказа.")
        return

    order_id = int(match.group(1))
    order = get_pin_order(order_id)

    if order is None or order["user_id"] != callback.from_user.id:
        await callback.answer(
            "Заказ не найден.",
            show_alert=True,
        )
        return

    data = await state.get_data()

    if (
        await state.get_state() != PostStates.waiting_for_pay.state
        or data.get("order_id") != order_id
    ):
        await callback.answer(
            "Этот заказ сейчас нельзя отменить.",
            show_alert=True,
        )
        return

    if not cancel_pin_order(order_id):
        await callback.answer(
            "Заказ уже отменён или чек уже отправлен.",
            show_alert=True,
        )
        return

    await state.clear()

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"❌ Заказ №{order_id} отменён.",
        reply_markup=main_keyboard(),
    )
    await callback.answer("Оплата отменена.")
