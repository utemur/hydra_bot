#!/usr/bin/env python3
"""
Тестовый файл для проверки конфигурации
"""
import os
from dotenv import load_dotenv

def test_config():
    """Проверка конфигурации"""
    load_dotenv()
    
    print("🔍 Проверка переменных окружения:")
    print(f"BOT_TOKEN: {'✅ Установлен' if os.getenv('BOT_TOKEN') else '❌ Отсутствует'}")
    print(f"OPENAI_API_KEY: {'✅ Установлен' if os.getenv('OPENAI_API_KEY') else '❌ Отсутствует'}")
    print(f"PORT: {os.getenv('PORT', '8080')}")
    
    if not os.getenv('BOT_TOKEN'):
        print("❌ BOT_TOKEN не найден! Добавьте его в переменные окружения.")
        return False
    
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY не найден! Добавьте его в переменные окружения.")
        return False
    
    print("✅ Все переменные окружения настроены правильно!")
    return True

if __name__ == "__main__":
    test_config()
