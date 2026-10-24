# Файл который инциализирует работу бота
from config import BOT_TOKEN
import asyncio
from aiogram import Bot, Dispatcher
from middleware import UserMiddleWare
from sqlwork.setup import create_table, add_ban_reason_column
from app.handlers import router
from sqlwork.orders import init_orders_table
from sqlwork.support import init_support_tables

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def main():
    create_table()
    add_ban_reason_column()
    init_orders_table()
    init_support_tables()
    router.message.middleware(UserMiddleWare())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())