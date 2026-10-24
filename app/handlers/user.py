from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from fsm import PostStates
from keyboards import main_keyboard, privilege_keyboard
from aiogram.types import ReplyKeyboardRemove
from message_text import WELCOME_MESSAGE, RECIEVED_POST
router = Router()

# Хэндлер команды старт
@router.message(CommandStart())
async def welcome(message: Message, command: CommandObject):
    
    await message.answer(WELCOME_MESSAGE.format(name=message.from_user.first_name),
                         reply_markup=main_keyboard())

# Хэндлер Предложить пост 🗒️
@router.message(F.text == 'Предложить пост 🗒️')
async def suggest_post(message: Message, state: FSMContext):
    # Установка состояния 
    await state.set_state(PostStates.waiting_for_post)
    await message.answer("Отправь пост", reply_markup=ReplyKeyboardRemove())


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

    await bot.send_message(chat_id=-1004425653871, text=RECIEVED_POST.format(user_id=data['user_id']))
    data = await state.get_data()
    await bot.forward_message(
        chat_id=-1004425653871,
        from_chat_id=data["chat_id"],
        message_id=data["message_id"]
    )

    await message.answer("✅ Пост отправлен на модерацию!", reply_markup=main_keyboard())
    await state.clear()


@router.message(
    F.text == "Закрепить 📌",
    PostStates.choosing_privilege
)
async def pin_post(message: Message):
    await message.answer(
        "Отправьте на какое количество времени вы хотите закрепить пост:" \
        "6 часов – 20 ⭐️" \
        "12 часов – 20 ⭐️" \
        "24 часов – 30 ⭐️"
    )