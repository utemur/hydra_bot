import re
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from db import Database
from llm import LLMService

logger = logging.getLogger(__name__)
router = Router()

# Состояния FSM
class SummaryStates(StatesGroup):
    waiting_for_group_selection = State()
    waiting_for_time_period = State()

# Инициализация сервисов
db = Database()
llm_service = LLMService()

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    welcome_text = """
🤖 Привет! Я бот для создания кратких пересказов обсуждений в группах.

📋 Доступные команды:
/summary - Выбрать группу для пересказа
/summary today - Пересказ обсуждения за сегодня
/summary 3h - Пересказ за последние 3 часа

💡 Как использовать:
1. Добавьте меня в группу
2. Я буду собирать сообщения
3. В личке вызовите /summary и выберите группу
4. Получите краткий пересказ обсуждения

🔧 Бот работает только в группах, где вы и я состоим вместе.
"""
    await message.answer(welcome_text)

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = """
📖 Справка по использованию бота:

🔹 /summary - Показать список групп и выбрать для пересказа
🔹 /summary today - Быстрый пересказ обсуждения за сегодня
🔹 /summary 3h - Пересказ за последние 3 часа
🔹 /summary 6h - Пересказ за последние 6 часов
🔹 /summary 12h - Пересказ за последние 12 часов

💡 Советы:
• Бот анализирует последние 200 сообщений
• Пересказ создается с помощью ИИ
• Работает только в группах, где вы состоите
"""
    await message.answer(help_text)

@router.message(Command("summary"))
async def cmd_summary(message: Message, state: FSMContext):
    """Обработчик команды /summary"""
    try:
        # Проверяем аргументы команды
        command_parts = message.text.split()
        
        if len(command_parts) > 1:
            # Обработка команд с параметрами времени
            time_param = command_parts[1].lower()
            
            if time_param == "today":
                await handle_today_summary(message)
                return
            elif time_param.endswith('h'):
                # Извлекаем количество часов
                try:
                    hours = int(time_param[:-1])
                    await handle_hours_summary(message, hours)
                    return
                except ValueError:
                    await message.answer("❌ Неверный формат времени. Используйте: /summary 3h")
                    return
        
        # Обычная команда /summary - показываем список групп
        await show_groups_list(message, state)
        
    except Exception as e:
        logger.error(f"Ошибка в обработке команды summary: {e}")
        await message.answer("❌ Произошла ошибка при обработке команды")

async def show_groups_list(message: Message, state: FSMContext):
    """Показать список групп пользователя"""
    try:
        user_id = message.from_user.id
        groups = await db.get_user_groups(user_id)
        
        if not groups:
            await message.answer("❌ Не найдено групп, где вы и я состоим вместе.\n\nДобавьте меня в группу и отправьте несколько сообщений.")
            return
        
        # Создаем клавиатуру с группами
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        
        for group in groups:
            chat_title = group['chat_title'] or f"Группа {group['chat_id']}"
            message_count = group['message_count']
            
            button_text = f"📋 {chat_title} ({message_count} сообщ.)"
            callback_data = f"group_{group['chat_id']}"
            
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(text=button_text, callback_data=callback_data)
            ])
        
        await message.answer(
            "📋 Выберите группу для создания пересказа:",
            reply_markup=keyboard
        )
        
        await state.set_state(SummaryStates.waiting_for_group_selection)
        
    except Exception as e:
        logger.error(f"Ошибка при показе списка групп: {e}")
        await message.answer("❌ Произошла ошибка при получении списка групп")

@router.callback_query(lambda c: c.data.startswith('group_'))
async def process_group_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора группы"""
    try:
        chat_id = int(callback.data.split('_')[1])
        
        # Сохраняем выбранную группу
        await state.update_data(selected_group_id=chat_id)
        
        # Показываем опции времени
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📅 Последние 200 сообщений", callback_data="time_recent")],
            [InlineKeyboardButton(text="📅 За сегодня", callback_data="time_today")],
            [InlineKeyboardButton(text="⏰ За последние 3 часа", callback_data="time_3h")],
            [InlineKeyboardButton(text="⏰ За последние 6 часов", callback_data="time_6h")],
            [InlineKeyboardButton(text="⏰ За последние 12 часов", callback_data="time_12h")]
        ])
        
        await callback.message.edit_text(
            "⏰ Выберите период для пересказа:",
            reply_markup=keyboard
        )
        
        await state.set_state(SummaryStates.waiting_for_time_period)
        
    except Exception as e:
        logger.error(f"Ошибка при выборе группы: {e}")
        await callback.answer("❌ Произошла ошибка при выборе группы")

@router.callback_query(lambda c: c.data.startswith('time_'))
async def process_time_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора периода времени"""
    try:
        time_option = callback.data.split('_')[1]
        user_data = await state.get_data()
        chat_id = user_data.get('selected_group_id')
        
        if not chat_id:
            await callback.answer("❌ Группа не выбрана")
            return
        
        # Показываем сообщение о начале обработки
        await callback.message.edit_text("🔄 Создаю пересказ... Это может занять несколько секунд.")
        
        # Получаем сообщения в зависимости от выбранного периода
        if time_option == "recent":
            messages = await db.get_recent_messages(chat_id, limit=200)
            time_period = "последние 200 сообщений"
        elif time_option == "today":
            messages = await db.get_today_messages(chat_id)
            time_period = "сегодня"
        else:
            # Извлекаем количество часов
            hours = int(time_option[:-1])
            messages = await db.get_recent_messages(chat_id, limit=200, hours=hours)
            time_period = f"последние {hours} часов"
        
        if not messages:
            await callback.message.edit_text("❌ Нет сообщений для анализа в указанный период.")
            await state.clear()
            return
        
        # Получаем название группы
        group_title = messages[0].get('chat_title', f"Группа {chat_id}") if messages else f"Группа {chat_id}"
        
        # Генерируем пересказ
        summary = await llm_service.generate_group_summary(messages, group_title, time_period)
        
        # Отправляем результат
        await callback.message.edit_text(summary)
        
        # Очищаем состояние
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при обработке выбора времени: {e}")
        await callback.message.edit_text("❌ Произошла ошибка при создании пересказа")
        await state.clear()

async def handle_today_summary(message: Message):
    """Обработка команды /summary today"""
    try:
        user_id = message.from_user.id
        groups = await db.get_user_groups(user_id)
        
        if not groups:
            await message.answer("❌ Не найдено групп для анализа.")
            return
        
        # Берем первую группу (самую активную)
        group = groups[0]
        chat_id = group['chat_id']
        group_title = group['chat_title'] or f"Группа {chat_id}"
        
        await message.answer("🔄 Создаю пересказ за сегодня...")
        
        messages = await db.get_today_messages(chat_id)
        
        if not messages:
            await message.answer("❌ Нет сообщений за сегодня в этой группе.")
            return
        
        summary = await llm_service.generate_group_summary(messages, group_title, "сегодня")
        await message.answer(summary)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке today summary: {e}")
        await message.answer("❌ Произошла ошибка при создании пересказа")

async def handle_hours_summary(message: Message, hours: int):
    """Обработка команды /summary Nh"""
    try:
        user_id = message.from_user.id
        groups = await db.get_user_groups(user_id)
        
        if not groups:
            await message.answer("❌ Не найдено групп для анализа.")
            return
        
        # Берем первую группу (самую активную)
        group = groups[0]
        chat_id = group['chat_id']
        group_title = group['chat_title'] or f"Группа {chat_id}"
        
        await message.answer(f"🔄 Создаю пересказ за последние {hours} часов...")
        
        messages = await db.get_recent_messages(chat_id, limit=200, hours=hours)
        
        if not messages:
            await message.answer(f"❌ Нет сообщений за последние {hours} часов в этой группе.")
            return
        
        time_period = f"последние {hours} часов"
        summary = await llm_service.generate_group_summary(messages, group_title, time_period)
        await message.answer(summary)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке hours summary: {e}")
        await message.answer("❌ Произошла ошибка при создании пересказа")

@router.message()
async def handle_all_messages(message: Message):
    """Обработчик всех сообщений для сохранения в базу данных"""
    try:
        # Сохраняем только текстовые сообщения из групп
        if (message.chat.type in ['group', 'supergroup'] and 
            message.text and 
            not message.text.startswith('/')):
            
            chat_id = message.chat.id
            chat_title = message.chat.title
            user_id = message.from_user.id
            username = message.from_user.username or message.from_user.first_name
            message_text = message.text
            
            await db.save_message(chat_id, chat_title, user_id, username, message_text)
            
    except Exception as e:
        logger.error(f"Ошибка при сохранении сообщения: {e}") 