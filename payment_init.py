
import asyncio
import math
import re
import time

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from fsm import PostStates
from config import (
    IBAN,
    MODERATION_GROUP_ID,
    PAYMENT_RECIPIENT,
    PIN_OPTIONS,
)
from keyboards import (
    cancel_payment_kb,
    main_keyboard,
    payment_method_kb,
    return_to_menu_keyboard,
)
from sqlwork.orders import (
    create_pin_order,
    get_pin_order,
    cancel_pin_order,
    expire_pin_order,
    mark_payment_submitted,
    mark_stars_payment_submitted,
)

router = Router()
payment_countdown_tasks: dict[int, asyncio.Task] = {}


def stop_payment_countdown(order_id: int):
    task = payment_countdown_tasks.pop(order_id, None)
    if task is not None and not task.done():
        task.cancel()


async def _payment_countdown(
    bot: Bot,
    state: FSMContext,
    order_id: int,
    user_id: int,
    status_message_id: int,
    status_text: str,
    parse_mode: str | None = None,
):
    try:
        while True:
            order = get_pin_order(order_id)
            if (
                order is None
                or order["status"] != "pending"
                or order["payment_submitted_at"] is not None
            ):
                return

            remaining = math.ceil(order["expires_at"] - time.time())
            if remaining <= 0:
                if expire_pin_order(order_id):
                    try:
                        await bot.edit_message_text(
                            chat_id=user_id,
                            message_id=status_message_id,
                            text="⏰ Время оплаты истекло. Заказ отменён.",
                            reply_markup=None,
                        )
                    except Exception:
                        pass

                    data = await state.get_data()
                    if (
                        data.get("order_id") == order_id
                        and await state.get_state()
                        == PostStates.waiting_for_pay.state
                    ):
                        await state.clear()

                    await bot.send_message(
                        chat_id=user_id,
                        text=(
                            "Время оплаты вышло, заказ отменён. "
                            "Чтобы начать заново, нажми «Предложить пост 🗒️»."
                        ),
                        reply_markup=main_keyboard(),
                    )
                return

            minutes, seconds = divmod(remaining, 60)
            try:
                await bot.edit_message_text(
                    chat_id=user_id,
                    message_id=status_message_id,
                    text=(
                        f"{status_text}\n\n"
                        f"⏳ Осталось: {minutes:02d}:{seconds:02d}"
                    ),
                    reply_markup=cancel_payment_kb(order_id),
                    parse_mode=parse_mode,
                )
            except Exception:
                pass

            await asyncio.sleep(1)
    except asyncio.CancelledError:
        raise
    finally:
        payment_countdown_tasks.pop(order_id, None)


def start_payment_countdown(
    bot: Bot,
    state: FSMContext,
    order_id: int,
    user_id: int,
    status_message_id: int,
    status_text: str,
    parse_mode: str | None = None,
):
    stop_payment_countdown(order_id)
    payment_countdown_tasks[order_id] = asyncio.create_task(
        _payment_countdown(
            bot=bot,
            state=state,
            order_id=order_id,
            user_id=user_id,
            status_message_id=status_message_id,
            status_text=status_text,
            parse_mode=parse_mode,
        )
    )


@router.callback_query(
    PostStates.waiting_for_duration,
    F.data.in_(PIN_OPTIONS),
)
async def choose_duration(
    callback: CallbackQuery,
    state: FSMContext,
):
    data = await state.get_data()

    if "user_id" not in data:
        await callback.answer(
            "Не удалось найти данные заказа",
            show_alert=True,
        )
        await state.clear()
        return

    if callback.from_user.id != data["user_id"]:
        await callback.answer("Это не твой заказ.", show_alert=True)
        return

    hours, amount, stars_amount = PIN_OPTIONS[callback.data]
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.update_data(
        hours=hours,
        amount=amount,
        stars_amount=stars_amount,
    )
    await state.set_state(PostStates.choosing_payment_method)
    await callback.message.answer(
        f"Закреп на {hours} ч.\nВыбери способ оплаты:",
        reply_markup=payment_method_kb(),
    )
    await callback.answer()


async def create_payment_order(
    callback: CallbackQuery,
    state: FSMContext,
    payment_method: str,
):
    data = await state.get_data()
    if data.get("user_id") != callback.from_user.id:
        await callback.answer("Не удалось найти заказ.", show_alert=True)
        await state.clear()
        return None

    order_id = create_pin_order(
        user_id=callback.from_user.id,
        post_chat_id=0,
        post_message_id=0,
        hours=data["hours"],
        amount=data["amount"],
        payment_method=payment_method,
        stars_amount=data["stars_amount"],
    )
    await state.update_data(order_id=order_id)
    await state.set_state(PostStates.waiting_for_pay)
    return get_pin_order(order_id)


@router.callback_query(
    PostStates.choosing_payment_method,
    F.data == "pin_pay_card",
)
async def choose_card_payment(
    callback: CallbackQuery,
    state: FSMContext,
):
    order = await create_payment_order(callback, state, "card")
    if order is None:
        return

    status_text = (
        f"📌 Заказ на закрепление №{order['id']}\n\n"
        f"⏱ Длительность: {order['hours']} ч.\n"
        f"💳 К оплате: {order['amount']} грн\n\n"
        f"Получатель: {PAYMENT_RECIPIENT}\n"
        f"IBAN:\n<code>{IBAN}</code>\n\n"
        "Переведи указанную сумму на этот счёт.\n"
        "После перевода отправь сюда фотографию чека.\n"
        "После чека нужно будет написать пост."
    )
    status_message = await callback.message.answer(
        f"{status_text}\n\n⏳ Осталось: 15:00",
        reply_markup=cancel_payment_kb(order["id"]),
        parse_mode="HTML",
    )
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.update_data(payment_status_message_id=status_message.message_id)
    start_payment_countdown(
        callback.bot,
        state,
        order["id"],
        callback.from_user.id,
        status_message.message_id,
        status_text,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(
    PostStates.choosing_payment_method,
    F.data == "pin_pay_stars",
)
async def choose_stars_payment(
    callback: CallbackQuery,
    state: FSMContext,
):
    order = await create_payment_order(callback, state, "stars")
    if order is None:
        return

    try:
        await callback.bot.send_invoice(
            chat_id=callback.from_user.id,
            title=f"Закрепление на {order['hours']} ч.",
            description="Закрепление поста в Подслушано ЗИЕИТ",
            payload=f"pin_order:{order['id']}",
            provider_token="",
            currency="XTR",
            prices=[
                LabeledPrice(
                    label=f"Закрепление на {order['hours']} ч.",
                    amount=order["stars_amount"],
                )
            ],
        )
    except Exception:
        cancel_pin_order(order["id"])
        await state.clear()
        await callback.answer(
            "Не удалось выставить счёт Stars. Попробуй выбрать карту.",
            show_alert=True,
        )
        return
    await callback.message.edit_reply_markup(reply_markup=None)
    status_text = (
        f"⭐️ Заказ №{order['id']} на {order['hours']} ч.\n"
        f"К оплате: {order['stars_amount']} Stars.\n"
        "Оплати счёт выше. После оплаты бот попросит написать пост."
    )
    status_message = await callback.message.answer(
        f"{status_text}\n\n⏳ Осталось: 15:00",
        reply_markup=cancel_payment_kb(order["id"]),
    )
    await state.update_data(payment_status_message_id=status_message.message_id)
    start_payment_countdown(
        callback.bot,
        state,
        order["id"],
        callback.from_user.id,
        status_message.message_id,
        status_text,
    )
    await callback.answer()


@router.callback_query(
    PostStates.choosing_payment_method,
    F.data == "cancel_pin_selection",
)
async def cancel_pin_selection(
    callback: CallbackQuery,
    state: FSMContext,
):
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Выбор закрепления отменён.",
        reply_markup=main_keyboard(),
    )
    await callback.answer()


@router.pre_checkout_query()
async def validate_stars_payment(query: PreCheckoutQuery):
    match = re.fullmatch(r"pin_order:(\d+)", query.invoice_payload)
    order = get_pin_order(int(match.group(1))) if match else None
    valid = (
        order is not None
        and order["user_id"] == query.from_user.id
        and order["status"] == "pending"
        and order["payment_method"] == "stars"
        and order["payment_submitted_at"] is None
        and order["expires_at"] > int(time.time())
        and query.currency == "XTR"
        and query.total_amount == order["stars_amount"]
    )
    await query.answer(
        ok=valid,
        error_message=None if valid else "Счёт истёк или больше не действителен.",
    )


@router.message(F.successful_payment)
async def receive_stars_payment(
    message: Message,
    state: FSMContext,
    bot: Bot,
):
    payment = message.successful_payment
    match = re.fullmatch(r"pin_order:(\d+)", payment.invoice_payload)
    order = get_pin_order(int(match.group(1))) if match else None
    if (
        order is None
        or order["user_id"] != message.from_user.id
        or order["payment_method"] != "stars"
        or order["stars_amount"] != payment.total_amount
        or payment.currency != "XTR"
    ):
        await message.answer(
            "Платёж получен, но не удалось найти заказ. Напиши в поддержку."
        )
        await bot.send_message(
            chat_id=MODERATION_GROUP_ID,
            text=(
                "⚠️ Не удалось автоматически связать платёж Stars\n"
                f"👤 ID пользователя: {message.from_user.id}\n"
                f"🧾 Payload: {payment.invoice_payload}\n"
                f"🔖 Charge ID: {payment.telegram_payment_charge_id}"
            ),
        )
        return

    if not mark_stars_payment_submitted(
        order["id"],
        message.from_user.id,
        payment.telegram_payment_charge_id,
    ):
        await message.answer(
            "Оплата получена, но срок заказа уже истёк. Напиши в поддержку."
        )
        await state.clear()
        return

    stop_payment_countdown(order["id"])
    data = await state.get_data()
    status_message_id = data.get("payment_status_message_id")
    if status_message_id is not None:
        try:
            await bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=status_message_id,
                reply_markup=None,
            )
        except Exception:
            pass
    await state.update_data(order_id=order["id"])
    await state.set_state(PostStates.waiting_for_post)
    await message.answer(
        "✅ Оплата Stars получена. Теперь отправь пост для модерации.",
        reply_markup=return_to_menu_keyboard(),
    )


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
        if expire_pin_order(order_id):
            stop_payment_countdown(order_id)
            await state.clear()
            await message.answer(
                "Время оплаты вышло, заказ отменён. "
                "Чтобы начать заново, нажми «Предложить пост 🗒️».",
                reply_markup=main_keyboard(),
            )
            return
        await message.answer(
            "Чек уже отправлен или заказ отменён."
        )
        return

    stop_payment_countdown(order_id)
    status_message_id = data.get("payment_status_message_id")
    if status_message_id is not None:
        try:
            await bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=status_message_id,
                reply_markup=None,
            )
        except Exception:
            pass

    await state.set_state(PostStates.waiting_for_post)
    await message.answer(
        "✅ Чек получен. Теперь отправь текст или медиа поста для модерации.",
        reply_markup=return_to_menu_keyboard(),
    )


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

    stop_payment_countdown(order_id)
    await state.clear()

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"❌ Заказ №{order_id} отменён.",
        reply_markup=main_keyboard(),
    )
    await callback.answer("Оплата отменена.")
