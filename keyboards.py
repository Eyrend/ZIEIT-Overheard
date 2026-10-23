from aiogram.utils.keyboard import (ReplyKeyboardBuilder, InlineKeyboardMarkup,
                                    InlineKeyboardButton)


def main_keyboard():
    keyboard = ReplyKeyboardBuilder()

    keyboard.button(
        text='Предложить пост 🗒️'
    )
    keyboard.button(
        text='Подробнее 📲'
    )
    keyboard.button(
        text='Настройки ⚙️',
        style='red'
    )
    keyboard.adjust(1, 2)
    return keyboard.as_markup(resize_keyboard=True)