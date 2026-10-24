from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from fsm import PostStates
from keyboards import main_keyboard, privilege_keyboard, set_time_kb
from aiogram.types import ReplyKeyboardRemove
from message_text import WELCOME_MESSAGE, RECIEVED_POST, SET_TIME_TEXT, MORE, REFUND
from config import MODERATION_GROUP_ID
router = Router()

# Хэндлер команды старт
@router.message(CommandStart(), F.chat.type =='private')
async def welcome(message: Message, command: CommandObject):
    
    await message.answer(WELCOME_MESSAGE.format(name=message.from_user.first_name),
                         reply_markup=main_keyboard())

# Хэндлер Предложить пост 🗒️
@router.message(F.text == 'Предложить пост 🗒️', F.chat.type =='private')
async def suggest_post(message: Message, state: FSMContext):
    # Установка состояния 
    await state.set_state(PostStates.waiting_for_post)
    await message.answer("Отправь пост", reply_markup=ReplyKeyboardRemove())

@router.message(PostStates.waiting_for_post)
async def receive_post(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/"):
        await message.answer("Отправьте пост")
        return

    await state.update_data(
        chat_id=message.chat.id,
        message_id=message.message_id,
        user_id=message.from_user.id,
    )

    await state.set_state(PostStates.choosing_privilege)

    await message.answer(
        "Выбери вариант публикации:",
        reply_markup=privilege_keyboard(),
    )


@router.message(
    F.text == "Без привилегий ❌",
    PostStates.choosing_privilege)
async def no_privileges(
    message: Message,
    state: FSMContext,
    bot: Bot):
    data = await state.get_data()

    await bot.send_message(chat_id=MODERATION_GROUP_ID, text=RECIEVED_POST.format(user_id=data['user_id']))
    data = await state.get_data()
    await bot.forward_message(
        chat_id=MODERATION_GROUP_ID,
        from_chat_id=data["chat_id"],
        message_id=data["message_id"]
    )

    await message.answer("✅ Пост отправлен на модерацию!", reply_markup=main_keyboard())
    await state.clear()


@router.message(
    F.text == "Закрепить 📌",
    PostStates.choosing_privilege,
)
async def pin_post(message: Message, state: FSMContext):
    await state.set_state(PostStates.waiting_for_duration)

    await message.answer(
        text=SET_TIME_TEXT,
        reply_markup=set_time_kb(),
    )

@router.message(F.text == 'Подробнее 📲')
async def send_more(message: Message):
    await message.answer(MORE)

@router.message(F.text == 'Условия возврата ⛓️')
async def send_more(message: Message):
    await message.answer(REFUND)

@router.message(F.text == "Поддержка 🛟")
async def support(message: Message, state: FSMContext):
    await state.set_state(PostStates.support_message)
    await message.answer("🛟 Напиши своё обращение. Оно будет отправлено администрации.")


@router.message(PostStates.support_message)
async def receive_support_message(
    message: Message,
    state: FSMContext,
    bot: Bot,
):
    user = message.from_user

    await bot.send_message(
        chat_id=MODERATION_GROUP_ID,
        text=(
            "🛟 ОБРАЩЕНИЕ В ПОДДЕРЖКУ\n\n"
            f"👤 Пользователь: {user.full_name}\n"
            f"🆔 Telegram ID: {user.id}\n"
            f"🔗 Username: @{user.username if user.username else 'отсутствует'}"
        ),
    )

    await bot.forward_message(
        chat_id=MODERATION_GROUP_ID,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
    )

    await message.answer(
        "✅ Обращение отправлено!",
        reply_markup=main_keyboard(),
    )
    await state.clear()

