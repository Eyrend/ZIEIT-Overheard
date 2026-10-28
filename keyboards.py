
from aiogram.utils.keyboard import (
    ReplyKeyboardBuilder,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from config import PIN_OPTIONS

MAIN_MENU_BUTTON = "🏠 В главное меню"


def main_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.button(text="Предложить пост 🗒️")
    keyboard.button(text="Дата рождения 🎂")
    keyboard.button(text="Подробнее 📲")
    keyboard.button(text="Идеи и объявления 💡")
    keyboard.button(text='Условия возврата ⛓️')
    keyboard.button(text='Поддержка 🛟')
    keyboard.adjust(1, 2, 2, 1)
    return keyboard.as_markup(resize_keyboard=True)


def ideas_and_listings_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔎 Потерял / нашёл вещь",
                    callback_data="user_option:lost_item",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💡 Предложить идею для бота",
                    callback_data="user_option:improvement",
                )
            ],
        ]
    )


def return_to_menu_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.button(text=MAIN_MENU_BUTTON)
    return keyboard.as_markup(resize_keyboard=True)


def birthday_input_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.button(text="📣 Напомнить модераторам")
    keyboard.button(text=MAIN_MENU_BUTTON)
    keyboard.adjust(1)
    return keyboard.as_markup(resize_keyboard=True)


def privilege_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.button(text="Закрепить 📌")
    keyboard.button(text="Без привилегий ❌")
    keyboard.button(text=MAIN_MENU_BUTTON)
    keyboard.adjust(2, 1)
    return keyboard.as_markup(resize_keyboard=True)


def anonymity_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.button(text="Анонимно")
    keyboard.button(text="Публично")
    keyboard.button(text=MAIN_MENU_BUTTON)
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


def post_preview_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить на модерацию", callback_data="post_preview:submit")],
            [InlineKeyboardButton(text="✏️ Редактировать пост", callback_data="post_preview:edit")],
            [InlineKeyboardButton(text="❌ Отменить публикацию", callback_data="post_preview:cancel")],
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
            [InlineKeyboardButton(text="📊 Статистика", callback_data="mod:stats")],
            [InlineKeyboardButton(text="🎂 ДР", callback_data="mod:birthdays")],
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


def birthday_list_keyboard(users, page: int, total_pages: int):
    rows = [
        [
            InlineKeyboardButton(
                text=(
                    f"{index}. @{user['username']}"
                    if user["username"]
                    else f"{index}. {user['name'] or 'Без username'}"
                )[:64],
                callback_data=f"birthday:user:{user['telegram_id']}:{page}",
            )
        ]
        for index, user in enumerate(users, start=page * 5 + 1)
    ]
    navigation = []
    if page > 0:
        navigation.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=f"birthday:page:{page - 1}",
            )
        )
    navigation.append(
        InlineKeyboardButton(
            text=f"{page + 1}/{total_pages}",
            callback_data="birthday:noop",
        )
    )
    if page + 1 < total_pages:
        navigation.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=f"birthday:page:{page + 1}",
            )
        )
    rows.append(navigation)
    rows.append(
        [InlineKeyboardButton(text="↩️ Назад в модерацию", callback_data="birthday:back")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def birthday_user_keyboard(user_id: int, page: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Изменить дату",
                    callback_data=f"birthday:edit:{user_id}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить дату",
                    callback_data=f"birthday:delete:{user_id}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К списку",
                    callback_data=f"birthday:page:{page}",
                )
            ],
        ]
    )


def birthday_delete_keyboard(user_id: int, page: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да, удалить",
                    callback_data=f"birthday:confirm_delete:{user_id}:{page}",
                ),
                InlineKeyboardButton(
                    text="Отмена",
                    callback_data=f"birthday:user:{user_id}:{page}",
                ),
            ]
        ]
    )
