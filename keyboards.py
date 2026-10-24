
from aiogram.utils.keyboard import (
    ReplyKeyboardBuilder,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


def main_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.button(text="Предложить пост 🗒️")
    keyboard.button(text="Подробнее 📲")
    keyboard.button(text="Настройки ⚙️")
    keyboard.adjust(1, 2)
    return keyboard.as_markup(resize_keyboard=True)


def privilege_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.button(text="Закрепить 📌")
    keyboard.button(text="Без привилегий ❌")
    keyboard.adjust(2)
    return keyboard.as_markup(resize_keyboard=True)


def set_time_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="6 часов — 20 грн",
                    callback_data="pin_6",
                )
            ],
            [
                InlineKeyboardButton(
                    text="12 часов — 40 грн",
                    callback_data="pin_12",
                )
            ],
            [
                InlineKeyboardButton(
                    text="24 часа — 50 грн",
                    callback_data="pin_24",
                )
            ],
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
