
from aiogram.utils.keyboard import (
    ReplyKeyboardBuilder,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from config import PIN_OPTIONS


def main_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.button(text="Предложить пост 🗒️")
    keyboard.button(text="Подробнее 📲")
    # keyboard.button(text="Настройки ⚙️")
    keyboard.button(text='Условия возврата ⛓️')
    keyboard.button(text='Поддержка 🛟')
    keyboard.adjust(1, 2, 1)
    return keyboard.as_markup(resize_keyboard=True)


def privilege_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.button(text="Закрепить 📌")
    keyboard.button(text="Без привилегий ❌")
    keyboard.adjust(2)
    return keyboard.as_markup(resize_keyboard=True)


def anonymity_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.button(text="Анонимно")
    keyboard.button(text="Публично")
    keyboard.adjust(2)
    return keyboard.as_markup(resize_keyboard=True)


def set_time_kb():
    labels = {
        "pin_6": "6 часов",
        "pin_12": "12 часов",
        "pin_24": "24 часа",
    }
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{labels[key]} — {uah} грн / {stars}⭐️",
                    callback_data=key,
                )
            ]
            for key, (_, uah, stars) in PIN_OPTIONS.items()
        ]
    )


def payment_method_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить картой", callback_data="pin_pay_card")],
            [InlineKeyboardButton(text="⭐️ Оплатить Telegram Stars", callback_data="pin_pay_stars")],
            [InlineKeyboardButton(text="❌ Отменить заказ", callback_data="cancel_pin_selection")],
        ]
    )


def cancel_payment_kb(order_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отменить оплату",
                    callback_data=f"cancel_payment:{order_id}",
                )
            ]
        ]
    )


def support_answer_kb(answer_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Посмотреть",
                    callback_data=f"support_answer:{answer_id}",
                )
            ]
        ]
    )


def moderation_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔨 Бан навсегда", callback_data="mod:ban_forever")],
            [
                InlineKeyboardButton(text="⏳ Бан на время", callback_data="mod:ban_temporary"),
                InlineKeyboardButton(text="🔇 Мут на время", callback_data="mod:mute_temporary"),
            ],
            [InlineKeyboardButton(text="⚠️ Выдать варн", callback_data="mod:warn")],
            [
                InlineKeyboardButton(text="♻️ Разбанить", callback_data="mod:unban"),
                InlineKeyboardButton(text="🔊 Снять мут", callback_data="mod:unmute"),
            ],
            [InlineKeyboardButton(text="✅ Снять последний варн", callback_data="mod:unwarn")],
        ]
    )
