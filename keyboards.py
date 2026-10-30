
from aiogram.types import ForceReply
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
    keyboard.button(text="Поддержать проект 💙")
    keyboard.button(text="Поддержка 🛟")
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
            [InlineKeyboardButton(text=f"📌 {labels[key]}", callback_data=key)]
            for key in PIN_OPTIONS
        ]
    )


def project_support_method_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Картой", callback_data="support_card")],
            [InlineKeyboardButton(text="⭐️ Telegram Stars", callback_data="support_stars")],
            [InlineKeyboardButton(text="🏠 Вернуться в главное меню", callback_data="support_home")],
        ]
    )


def cancel_project_support_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="❌ Отменить и вернуться", callback_data="support_cancel")
        ]]
    )


def payment_method_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏆 Я победитель розыгрыша",
                    callback_data="pin_pay_giveaway",
                )
            ],
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


def post_review_keyboard(submission_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Одобрить",
                    callback_data=f"post_review:approve:{submission_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"post_review:reject:{submission_id}",
                ),
            ]
        ]
    )


def rejection_reason_reply():
    return ForceReply(
        input_field_placeholder="Причина отказа",
    )


def cancel_payment_kb(order_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отменить заказ",
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
