# Файл который инциализирует работу бота
from config import BOT_TOKEN
import asyncio
from aiogram import Bot, Dispatcher
from middleware import UserMiddleWare
from sqlwork.setup import create_table 
from app.handlers import router

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def main():
    create_table()
    router.message.middleware(UserMiddleWare())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())