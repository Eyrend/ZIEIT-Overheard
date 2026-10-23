from aiogram import BaseMiddleware
from typing import Any, Callable, Awaitable
from aiogram.types import TelegramObject
from sqlwork.user import get_user, create_user
from config import ADMIN_IDS

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
            await event.answer("Вы заблокированы и не можете пользоваться ботом.")
            return


        data['user'] = user
        data['is_new_user'] = is_new_user
        data["is_admin"] = user_id in ADMIN_IDS

        return await handler(event, data)