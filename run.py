import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from bot import router
import logging
import os
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

async def main():
    bot = Bot(token=os.getenv('TOKEN'), parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Error')
