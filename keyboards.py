from aiogram.utils.keyboard import (ReplyKeyboardBuilder, InlineKeyboardMarkup,
                                    InlineKeyboardButton, InlineKeyboardBuilder)


def main_keyboard():
    keyboard = ReplyKeyboardBuilder()

    keyboard.button(
        text='Предложить пост 🗒️'
    )
    keyboard.button(
        text='Подробнее 📲'
    )
    keyboard.button(
        text='Настройки ⚙️'
        )
    keyboard.adjust(1, 2)
    return keyboard.as_markup(resize_keyboard=True)

def privilege_keyboard():
    keyboard = ReplyKeyboardBuilder()

    keyboard.button(
        text='Закрепить 📌'
    )

    keyboard.button(
        text='Без привилегий ❌'
    )
    keyboard.adjust(2)
    return keyboard.as_markup(resize_keyboard=True)

# def pin_keyboard():
#     keyboard = InlineKeyboardBuilder()

#     keyboard.button(text=)