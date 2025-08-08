import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "bot_database.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных и создание таблиц"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица для хранения сообщений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                chat_title TEXT,
                user_id INTEGER,
                username TEXT,
                message_text TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица для хранения информации о группах
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                chat_id INTEGER PRIMARY KEY,
                chat_title TEXT,
                member_count INTEGER,
                last_activity DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("База данных инициализирована")
    
    async def save_message(self, chat_id: int, chat_title: str, user_id: int, 
                          username: str, message_text: str):
        """Сохранение сообщения в базу данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO messages (chat_id, chat_title, user_id, username, message_text)
                VALUES (?, ?, ?, ?, ?)
            ''', (chat_id, chat_title, user_id, username, message_text))
            
            # Обновляем информацию о группе
            cursor.execute('''
                INSERT OR REPLACE INTO groups (chat_id, chat_title, last_activity)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (chat_id, chat_title))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Ошибка при сохранении сообщения: {e}")
    
    async def get_user_groups(self, user_id: int) -> List[Dict]:
        """Получение списка групп, где пользователь и бот состоят вместе"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT DISTINCT g.chat_id, g.chat_title, g.last_activity,
                       COUNT(m.id) as message_count
                FROM groups g
                LEFT JOIN messages m ON g.chat_id = m.chat_id
                WHERE g.chat_id IN (
                    SELECT DISTINCT chat_id FROM messages 
                    WHERE user_id = ? OR chat_id IN (
                        SELECT chat_id FROM messages 
                        WHERE user_id = ?
                    )
                )
                GROUP BY g.chat_id, g.chat_title, g.last_activity
                ORDER BY g.last_activity DESC
            ''', (user_id, user_id))
            
            groups = []
            for row in cursor.fetchall():
                groups.append({
                    'chat_id': row[0],
                    'chat_title': row[1],
                    'last_activity': row[2],
                    'message_count': row[3]
                })
            
            conn.close()
            return groups
        except Exception as e:
            logger.error(f"Ошибка при получении групп пользователя: {e}")
            return []
    
    async def get_recent_messages(self, chat_id: int, limit: int = 200, 
                                 hours: Optional[int] = None) -> List[Dict]:
        """Получение последних сообщений из группы"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if hours:
                # Получаем сообщения за последние N часов
                time_filter = datetime.now() - timedelta(hours=hours)
                cursor.execute('''
                    SELECT user_id, username, message_text, timestamp
                    FROM messages
                    WHERE chat_id = ? AND timestamp >= ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (chat_id, time_filter, limit))
            else:
                # Получаем последние N сообщений
                cursor.execute('''
                    SELECT user_id, username, message_text, timestamp
                    FROM messages
                    WHERE chat_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (chat_id, limit))
            
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'user_id': row[0],
                    'username': row[1],
                    'message_text': row[2],
                    'timestamp': row[3]
                })
            
            conn.close()
            return messages[::-1]  # Возвращаем в хронологическом порядке
        except Exception as e:
            logger.error(f"Ошибка при получении сообщений: {e}")
            return []
    
    async def get_today_messages(self, chat_id: int) -> List[Dict]:
        """Получение сообщений за сегодня"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            today = datetime.now().date()
            cursor.execute('''
                SELECT user_id, username, message_text, timestamp
                FROM messages
                WHERE chat_id = ? AND DATE(timestamp) = ?
                ORDER BY timestamp ASC
            ''', (chat_id, today))
            
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'user_id': row[0],
                    'username': row[1],
                    'message_text': row[2],
                    'timestamp': row[3]
                })
            
            conn.close()
            return messages
        except Exception as e:
            logger.error(f"Ошибка при получении сообщений за сегодня: {e}")
            return [] 