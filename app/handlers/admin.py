from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, CommandStart, CommandObject
from sqlwork.user import ban_user, create_user, get_user


router = Router()

@router.message(Command('ban'))
async def ban_command(message: Message, is_admin: bool, user):
    if not is_admin:
        return
    
    arguments = message.text.split(" ")
    if len(arguments) != 2:
        await message.answer("Использование: /ban ID")
        return
    user_id = arguments[1]

    try:
        user_id = int(user_id)
    except ValueError:
        await message.answer("Неккоретный тип данных")
        return
    if get_user(user_id) is None:
        await message.answer(f"Пользователь {user_id} не найден в базе данных")
        return
    ban_user(1, user_id)
    await message.answer(f"Пользователь {user_id} забанен")
