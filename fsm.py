from aiogram.fsm.state import State, StatesGroup

# Создание состояний кода 
class PostStates(StatesGroup):
    waiting_for_post = State()
    choosing_privilege = State()
    waiting_for_duration = State()
    waiting_for_pay = State()