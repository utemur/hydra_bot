import openai
import logging
from typing import List, Dict
from config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        try:
            self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
        except Exception as e:
            logger.error(f"Ошибка инициализации OpenAI клиента: {e}")
            raise
    
    def format_messages_for_summary(self, messages: List[Dict]) -> str:
        """Форматирование сообщений для отправки в LLM"""
        if not messages:
            return "Нет сообщений для анализа."
        
        formatted_text = "Обсуждение в группе:\n\n"
        
        for msg in messages:
            username = msg.get('username', f"User{msg.get('user_id', 'Unknown')}")
            text = msg.get('message_text', '').strip()
            timestamp = msg.get('timestamp', '')
            
            if text:  # Пропускаем пустые сообщения
                formatted_text += f"[{timestamp}] {username}: {text}\n\n"
        
        return formatted_text
    
    async def generate_summary(self, messages: List[Dict], time_period: str = "общее") -> str:
        """Генерация краткого пересказа обсуждения"""
        try:
            if not messages:
                return "Нет сообщений для анализа в указанный период."
            
            formatted_messages = self.format_messages_for_summary(messages)
            
            # Подсчитываем количество сообщений и участников
            unique_users = len(set(msg.get('user_id') for msg in messages))
            total_messages = len(messages)
            
            prompt = f"""
Ты - помощник для создания кратких пересказов обсуждений в Telegram-группах.

Создай краткий и информативный пересказ обсуждения за {time_period} период.

Статистика:
- Количество сообщений: {total_messages}
- Участников: {unique_users}

Обсуждение:
{formatted_messages}

Создай структурированный пересказ, который включает:
1. Основные темы обсуждения
2. Ключевые моменты и решения
3. Важные вопросы или проблемы
4. Общий тон и атмосфера обсуждения

Пересказ должен быть на русском языке, лаконичным (не более 300-400 слов) и информативным.
"""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Ты - помощник для создания кратких пересказов обсуждений в Telegram-группах. Отвечай на русском языке."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            summary = response.choices[0].message.content.strip()
            
            # Добавляем статистику в конец
            summary += f"\n\n📊 Статистика: {total_messages} сообщений от {unique_users} участников"
            
            return summary
            
        except Exception as e:
            logger.error(f"Ошибка при генерации пересказа: {e}")
            return f"Произошла ошибка при создании пересказа: {str(e)}"
    
    async def generate_group_summary(self, messages: List[Dict], group_title: str, 
                                   time_period: str = "общее") -> str:
        """Генерация пересказа с указанием группы"""
        summary = await self.generate_summary(messages, time_period)
        
        header = f"📋 Пересказ обсуждения в группе «{group_title}»\n"
        if time_period != "общее":
            header += f"⏰ Период: {time_period}\n"
        header += "─" * 50 + "\n\n"
        
        return header + summary 