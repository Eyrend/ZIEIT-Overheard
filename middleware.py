from aiogram import BaseMiddleware
from typing import Any, Callable, Awaitable
from aiogram.types import TelegramObject
from sqlwork.user import (
    get_or_create_user,
    get_user,
    unban_user,
    unmute_user,
)
from config import ADMIN_IDS
from aiogram.fsm.context import FSMContext
from fsm import PostStates
from keyboards import MAIN_MENU_BUTTON
import time

# Получение данных о пользователе 
class UserMiddleWare(BaseMiddleware):
    async def __call__(self, handler, event, data):
        state: FSMContext = data.get("state")

        if state is not None:
            current_state = await state.get_state()

            if current_state == PostStates.waiting_for_pay.state:
                event_text = (getattr(event, "text", None) or "").strip()
                is_start_command = (
                    event_text == "/start"
                    or event_text.startswith("/start ")
                )
                is_main_menu = event_text == MAIN_MENU_BUTTON
                if not getattr(event, "photo", None) and not getattr(
                    event, "successful_payment", None
                ) and not is_start_command and not is_main_menu:
                    await event.answer(
                        "Сначала заверши оплату или отмени заказ "
                        "кнопкой под сообщением об оплате."
                    )
                    return
        user_id = event.from_user.id

        user, is_new_user = get_or_create_user(
            telegram_id=user_id,
            name=event.from_user.first_name,
            username=event.from_user.username,
        )

        if user_id not in ADMIN_IDS and user["is_banned"]:
            ban_until = user['ban_until']

            if ban_until is not None and ban_until <= int(time.time()):
                unban_user(user_id)
                user = get_user(user_id)
            else:
                reason = user["ban_reason"] or "не указана"
                duration = "навсегда" if ban_until is None else "временно"
                await event.answer(
                    f"🔨 Вы заблокированы в боте ({duration}).\n"
                    f"Причина: {reason}"
                )
                return

        if user_id not in ADMIN_IDS and user["is_muted"]:
            mute_until = user["mute_until"]
            if mute_until is not None and mute_until <= int(time.time()):
                unmute_user(user_id)
                user = get_user(user_id)
            else:
                until_text = time.strftime(
                    "%d.%m.%Y %H:%M",
                    time.localtime(mute_until),
                )
                reason = user["mute_reason"] or "не указана"
                await event.answer(
                    f"🔇 Вам временно ограничили отправку сообщений боту.\n"
                    f"Мут действует до {until_text}.\n"
                    f"Причина: {reason}"
                )
                return


        data['user'] = user
        data['is_new_user'] = is_new_user
        data["is_admin"] = user_id in ADMIN_IDS

        return await handler(event, data)