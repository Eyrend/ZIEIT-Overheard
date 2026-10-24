from aiogram import BaseMiddleware
from typing import Any, Callable, Awaitable
from aiogram.types import TelegramObject
from sqlwork.user import get_user, create_user, unban_user
from config import ADMIN_IDS
import time

# Получение данных о пользователе 
class UserMiddleWare(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = event.from_user.id

        user = get_user(user_id)
        is_new_user = False
        if user is None:
            create_user(
                user_id,
                event.from_user.first_name,
                is_banned=0)
            user = get_user(user_id)
            is_new_user = True

        if user['is_banned']:
            ban_until = user['ban_until']
            
            await event.answer("Вы заблокированы и не можете пользоваться ботом.")
            if ban_until is not None and ban_until <= int(time.time()):
                unban_user(user_id)
                user = get_user(user_id)
            else:
                return


        data['user'] = user
        data['is_new_user'] = is_new_user
        data["is_admin"] = user_id in ADMIN_IDS

        return await handler(event, data)