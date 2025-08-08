import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from config import BOT_TOKEN
from handlers import router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Веб-сервер для healthcheck
async def healthcheck(request):
    """Эндпоинт для healthcheck Railway"""
    return web.json_response({
        "status": "healthy",
        "service": "telegram-summary-bot",
        "version": "1.0.0"
    })

async def root(request):
    """Корневой эндпоинт"""
    return web.json_response({
        "message": "Telegram Summary Bot is running!",
        "status": "active"
    })

async def start_web_server():
    """Запуск веб-сервера"""
    app = web.Application()
    app.router.add_get('/', root)
    app.router.add_get('/health', healthcheck)
    
    port = int(os.environ.get('PORT', 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"🌐 Веб-сервер запущен на порту {port}")
    return runner

async def start_bot():
    """Запуск бота"""
    try:
        bot = Bot(token=BOT_TOKEN)
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        dp.include_router(router)
        
        logger.info("🤖 Бот запускается...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")

async def main():
    """Основная функция запуска"""
    try:
        # Запуск веб-сервера
        web_runner = await start_web_server()
        
        # Запуск бота в отдельной задаче
        bot_task = asyncio.create_task(start_bot())
        
        # Ждем завершения бота
        await bot_task
        
    except Exception as e:
        logger.error(f"Ошибка при запуске: {e}")
    finally:
        logger.info("Приложение остановлено")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Приложение остановлено пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}") 