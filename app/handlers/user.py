from aiogram import Router
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import Message
from keyboards import main_keyboard
router = Router()

@router.message(CommandStart())
async def welcome(message: Message, command: CommandObject):
    hello_message = f"""Привет, {message.from_user.first_name}! 👋 
Добро пожаловать в нашего бота! Здесь ты можешь:

• Предложить свою историю 📖
• Поделиться новостью 📰
• Опубликовать пост в сообществе ✍️

Выберите нужное действие в меню ниже 👇"""
    
    await message.answer(hello_message, reply_markup=main_keyboard())
    
                    