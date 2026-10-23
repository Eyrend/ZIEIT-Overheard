from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from fsm import PostStates
from keyboards import main_keyboard, privilege_keyboard
router = Router()

# Хэндлер команды старт
@router.message(CommandStart())
async def welcome(message: Message, command: CommandObject):
    hello_message = f"""Привет, {message.from_user.first_name}! 👋 
Добро пожаловать в нашего бота! Здесь ты можешь:

• Предложить свою историю 📖
• Поделиться новостью 📰
• Опубликовать пост в сообществе ✍️

Выберите нужное действие в меню ниже 👇"""
    
    await message.answer(hello_message, reply_markup=main_keyboard())

# Хэндлер Предложить пост 🗒️
@router.message(F.text == 'Предложить пост 🗒️')
async def suggest_post(message: Message, state: FSMContext):
    # Установка состояния 
    await state.set_state(PostStates.waiting_for_post)
    await message.answer("Отправь пост")


@router.message(PostStates.waiting_for_post)
async def receive_post(message: Message, state: FSMContext):
    # Установка данных для состояния
    await state.update_data(
        chat_id=message.chat.id,
        message_id=message.message_id,
        user_id=message.from_user.id
    )


    await state.set_state(PostStates.choosing_privilege)
    await message.answer(
        "Выбери привилегию:",
        reply_markup=privilege_keyboard()
    )


@router.message(
    F.text == "Без привилегий ❌",
    PostStates.choosing_privilege)
async def no_privileges(
    message: Message,
    state: FSMContext,
    bot: Bot):
    data = await state.get_data()

    data = await state.get_data()
    await bot.copy_message(
        chat_id=-1004425653871,
        from_chat_id=data["chat_id"],
        message_id=data["message_id"]
    )
    message.answer(f"Сообщение отправлено пользователем {data["user_id"]}")   

    await message.answer("✅ Пост отправлен на модерацию!", reply_markup=main_keyboard())
    await state.clear()


@router.message(
    F.text == "Закрепить 📌",
    PostStates.choosing_privilege
)
async def pin_post(message: Message):
    await message.answer(
        "📌 Закрепление поста пока находится в разработке. "
        "Попробуй выбрать «Без привилегий».", reply_markup=main_keyboard()
    )