"""
Парсер для поиска работников через Telegram (Telethon)
Ищет: сварщиков, разнорабочих, людей ищущих подработку
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from telegram import Bot

# ============= НАСТРОЙКИ =============
# Telegram Bot для отправки результатов
BOT_TOKEN = os.getenv("BOT_TOKEN", "8302303298:AAGH3Nllv4JaQRoi8Em8rO1-L_zGinN-gVM")
CHAT_ID = os.getenv("CHAT_ID", "-1003407248691")
MESSAGE_THREAD_ID = os.getenv("MESSAGE_THREAD_ID", None)  # ID темы (топика) для отправки

# Telethon API (получить на my.telegram.org)
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

# Каналы для мониторинга
CHANNELS = [
    "zhitomir9",
    "zhytomyr_olx",
    "zhitomir_robota",
    "zhytomyr_job",
    "robota_zhytomyr",
    "zhitomir_work"
]

# Ключевые слова (ТОЛЬКО сварщик, разнорабочий, подработка)
KEYWORDS = [
    # Сварщик
    "сварщик", "зварник", "сварювальник", "зварювальник",
    # Разнорабочий
    "разнорабочий", "різноробочий", "подсобник", "підсобник",
    "разнорабочего", "різноробочого",
    # Подработка/ищу работу
    "шукаю роботу", "шукаю підробіток", "шукаю работу",
    "ищу работу", "ищу подработку", "нужна работа",
    "потрібна робота", "підробіток", "подработка",
    "готовий до роботи", "готов к работе", "готов работать"
]

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TelethonParser:
    """Парсер Telegram каналов через Telethon API"""
    
    def __init__(self, api_id, api_hash):
        self.api_id = api_id
        self.api_hash = api_hash
        self.client = None
        
    async def connect(self):
        """Подключение к Telegram"""
        self.client = TelegramClient('session', self.api_id, self.api_hash)
        await self.client.start()
        logger.info("✅ Подключено к Telegram")
        
    async def disconnect(self):
        """Отключение"""
        if self.client:
            await self.client.disconnect()
            
    async def get_messages_from_channel(self, channel_username, days=7, limit=100):
        """Получить сообщения из канала за последние N дней"""
        results = []
        
        try:
            # Получаем entity канала
            try:
                channel = await self.client.get_entity(channel_username)
            except Exception as e:
                logger.warning(f"Канал @{channel_username} не найден: {e}")
                return results
            
            # Дата за неделю назад
            week_ago = datetime.now() - timedelta(days=days)
            
            # Получаем историю сообщений
            messages = await self.client(GetHistoryRequest(
                peer=channel,
                limit=limit,
                offset_date=None,
                offset_id=0,
                max_id=0,
                min_id=0,
                add_offset=0,
                hash=0
            ))
            
            logger.info(f"📱 @{channel_username}: получено {len(messages.messages)} сообщений")
            
            for msg in messages.messages:
                if not msg.message:
                    continue
                    
                # Проверяем дату
                if msg.date.replace(tzinfo=None) < week_ago:
                    continue
                
                text = msg.message.lower()
                
                # Проверяем ключевые слова
                for keyword in KEYWORDS:
                    if keyword in text:
                        link = f"https://t.me/{channel_username}/{msg.id}"
                        
                        # Берём первые 200 символов текста
                        preview = msg.message[:200]
                        if len(msg.message) > 200:
                            preview += "..."
                        
                        results.append({
                            'text': preview,
                            'link': link,
                            'source': f'@{channel_username}',
                            'date': msg.date.strftime('%d.%m.%Y %H:%M'),
                            'keyword': keyword
                        })
                        logger.info(f"✓ Найдено [{keyword}]: {preview[:50]}...")
                        break  # Одно сообщение - один результат
                        
        except Exception as e:
            logger.error(f"Ошибка при парсинге @{channel_username}: {e}")
            
        return results
    
    async def search_all_channels(self, days=7):
        """Поиск по всем каналам"""
        all_results = []
        
        for channel in CHANNELS:
            results = await self.get_messages_from_channel(channel, days=days)
            all_results.extend(results)
            await asyncio.sleep(1)  # Пауза между каналами
            
        # Удаляем дубликаты по ссылкам
        seen = set()
        unique_results = []
        for r in all_results:
            if r['link'] not in seen:
                seen.add(r['link'])
                unique_results.append(r)
                
        return unique_results


async def send_results(results):
    """Отправить результаты в Telegram канал"""
    bot = Bot(token=BOT_TOKEN)
    
    if not results:
        message = "🔍 Поиск работников за неделю\n\n"
        message += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        message += "❌ Новых объявлений не найдено\n\n"
        message += "Искали: сварщик, разнорабочий, подработка"
    else:
        message = f"👥 Найдено работников: {len(results)}\n"
        message += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        message += "🔍 Ключевые слова: сварщик, разнорабочий, підробіток\n\n"
        
        for i, r in enumerate(results[:15], 1):  # Максимум 15 результатов
            message += f"{i}. [{r['keyword']}] {r['date']}\n"
            message += f"   {r['text'][:100]}...\n"
            message += f"   🔗 {r['link']}\n"
            message += f"   📱 {r['source']}\n\n"
            
            if len(message) > 3500:
                break
                
    # Отправляем в тему если указан MESSAGE_THREAD_ID
    thread_id = int(MESSAGE_THREAD_ID) if MESSAGE_THREAD_ID else None
    await bot.send_message(
        chat_id=CHAT_ID, 
        text=message, 
        disable_web_page_preview=True,
        message_thread_id=thread_id
    )
    logger.info(f"✅ Сообщение отправлено" + (f" в тему {thread_id}" if thread_id else ""))


async def main():
    """Главная функция"""
    logger.info("🚀 Запуск парсера работников")
    
    if not API_ID or not API_HASH:
        logger.error("❌ Не указаны API_ID и API_HASH!")
        logger.info("Получите их на https://my.telegram.org")
        logger.info("Установите переменные окружения API_ID и API_HASH")
        return
    
    parser = TelethonParser(API_ID, API_HASH)
    
    try:
        await parser.connect()
        
        # Ищем за последние 7 дней
        results = await parser.search_all_channels(days=7)
        
        logger.info(f"📊 Всего найдено: {len(results)} объявлений")
        
        # Отправляем результаты
        await send_results(results)
        
    finally:
        await parser.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
