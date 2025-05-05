import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession

from config import BOT_TOKEN
from database import init_db, get_session
from handlers import start, test, upload, phishing, progress, password


async def main():
    # Настраиваем логирование
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout
    )
    
    # Устанавливаем уровень логирования для наших модулей
    logging.getLogger('services').setLevel(logging.DEBUG)
    logging.getLogger('handlers').setLevel(logging.DEBUG)
    
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN не найден в переменных окружения")
        return
    
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    @asynccontextmanager
    async def session_middleware():
        async for session in get_session():
            yield session
    
    # Регистрация обработчиков
    dp.include_router(start.router)
    dp.include_router(test.router)
    dp.include_router(upload.router)
    dp.include_router(phishing.router)
    dp.include_router(progress.router)
    dp.include_router(password.router)
    
    # Middleware для передачи сессии БД в хендлеры
    async def db_session_middleware(handler, event, data):
        async with session_middleware() as session:
            data["session"] = session
            return await handler(event, data)
    
    dp.update.middleware(db_session_middleware)
    
    # Инициализация базы данных
    await init_db()
    
    logging.info("Бот запущен")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main()) 