"""
Парсер Telegram групп через Telethon
Ищет: сварщиков, разнорабочих, людей ищущих подработку
"""
import asyncio
import os
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from telegram import Bot
import logging

# ============= НАСТРОЙКИ =============
API_ID = 34113723
API_HASH = "e110b2fa49ddcf1fbe30740264ad14a9"

BOT_TOKEN = "8302303298:AAGH3Nllv4JaQRoi8Em8rO1-L_zGinN-gVM"
CHAT_ID = "-1003407248691"

# Группы и каналы для мониторинга
CHANNELS = [
    "zhitomir9",        # Житомир Чат
    "zhytomyr_olx",     # Працевлаштування
    "zt_robota",        # Робота Житомир
]

# ТОЛЬКО эти ключевые слова (сварщик, разнорабочий, подработка)
KEYWORDS = [
    # Сварщик
    "сварщик", "зварник", "сварювальник", "зварювальник",
    # Разнорабочий
    "разнорабочий", "різноробочий", "подсобник", "підсобник",
    # Ищу работу/подработку
    "шукаю роботу", "шукаю підробіток", "шукаю работу", "шукаю підзаробіток",
    "ищу работу", "ищу подработку", "нужна подработка",
    "готовий до роботи", "готов к работе",
]

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    logger.info("🚀 Запуск Telethon парсера")
    
    # Создаём клиент
    client = TelegramClient('worker_session', API_ID, API_HASH)
    
    await client.start()
    logger.info("✅ Подключено к Telegram")
    
    # Проверяем авторизацию
    me = await client.get_me()
    logger.info(f"👤 Авторизован как: {me.first_name} (@{me.username})")
    
    all_results = []
    week_ago = datetime.now() - timedelta(days=7)
    
    for channel_name in CHANNELS:
        logger.info(f"\n📱 Проверяю: @{channel_name}")
        
        try:
            # Получаем канал/группу
            channel = await client.get_entity(channel_name)
            logger.info(f"   Название: {channel.title if hasattr(channel, 'title') else channel_name}")
            
            # Получаем историю сообщений
            messages = await client(GetHistoryRequest(
                peer=channel,
                limit=200,  # Последние 200 сообщений
                offset_date=None,
                offset_id=0,
                max_id=0,
                min_id=0,
                add_offset=0,
                hash=0
            ))
            
            logger.info(f"   Получено сообщений: {len(messages.messages)}")
            
            found_count = 0
            for msg in messages.messages:
                if not msg.message:
                    continue
                
                # Проверяем дату (за последнюю неделю)
                msg_date = msg.date.replace(tzinfo=None)
                if msg_date < week_ago:
                    continue
                
                text = msg.message.lower()
                
                # Ищем ключевые слова
                for keyword in KEYWORDS:
                    if keyword in text:
                        link = f"https://t.me/{channel_name}/{msg.id}"
                        preview = msg.message[:250].replace('\n', ' ')
                        
                        all_results.append({
                            'text': preview,
                            'link': link,
                            'source': f'@{channel_name}',
                            'date': msg_date.strftime('%d.%m.%Y %H:%M'),
                            'keyword': keyword
                        })
                        found_count += 1
                        logger.info(f"   ✓ [{keyword}] {preview[:60]}...")
                        break  # Одно сообщение - один результат
            
            logger.info(f"   Найдено совпадений: {found_count}")
            
        except Exception as e:
            logger.error(f"   Ошибка: {e}")
        
        await asyncio.sleep(1)
    
    # Убираем дубликаты
    seen = set()
    unique = []
    for r in all_results:
        if r['link'] not in seen:
            seen.add(r['link'])
            unique.append(r)
    
    logger.info(f"\n📊 Всего уникальных результатов: {len(unique)}")
    
    # Формируем и отправляем сообщение
    if unique:
        message = f"👥 Найдено работников: {len(unique)}\n"
        message += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        message += "🔍 Сварщик | Разнорабочий | Підробіток\n"
        message += "📆 За последние 7 дней\n\n"
        
        for i, r in enumerate(unique[:15], 1):
            message += f"{i}. [{r['keyword']}] {r['date']}\n"
            message += f"   {r['text'][:120]}...\n"
            message += f"   🔗 {r['link']}\n\n"
            
            if len(message) > 3800:
                message += f"... и ещё {len(unique) - i} результатов"
                break
    else:
        message = "🔍 Поиск работников за неделю\n\n"
        message += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        message += "❌ Не найдено объявлений по ключевым словам:\n"
        message += "сварщик, разнорабочий, шукаю роботу\n\n"
        message += "Проверенные группы:\n"
        for ch in CHANNELS:
            message += f"• t.me/{ch}\n"
    
    # Отправляем
    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=message, disable_web_page_preview=True)
    logger.info("✅ Сообщение отправлено!")
    
    await client.disconnect()
    
    return unique


if __name__ == "__main__":
    asyncio.run(main())
