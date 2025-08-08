from aiohttp import web
import os

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
        "status": "active",
        "endpoints": {
            "health": "/health",
            "root": "/"
        }
    })

def create_app():
    """Создание веб-приложения"""
    app = web.Application()
    app.router.add_get('/', root)
    app.router.add_get('/health', healthcheck)
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 8080))
    web.run_app(app, port=port)
