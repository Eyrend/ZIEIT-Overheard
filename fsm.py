from aiogram.fsm.state import State, StatesGroup

# Создание состояний кода 
class PostStates(StatesGroup):
    support_message = State()
    donation_amount = State()
    donation_card_proof = State()
    waiting_for_post = State()
    choosing_anonymity = State()
    choosing_privilege = State()
    choosing_payment_method = State()
    waiting_for_duration = State()
    waiting_for_pay = State()
    moderation_target = State()
    moderation_birthday_edit = State()
    waiting_for_birthday = State()
    post_preview = State()
    suggest_improvement = State()
    lost_item = State()