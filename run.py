
from config import BOT_TOKEN
import asyncio
from aiogram import Bot, Dispatcher
from middleware import BaseMiddleware
from app.handlers import router

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def main():
    router.message.middleware(BaseMiddleware())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())