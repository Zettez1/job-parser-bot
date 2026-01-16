"""
Прямой парсинг Telegram каналов через t.me/s/
С правильными заголовками и куками
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
from telegram import Bot
import re

BOT_TOKEN = "8302303298:AAGH3Nllv4JaQRoi8Em8rO1-L_zGinN-gVM"
CHAT_ID = "-1003407248691"

# Каналы Житомира (проверенные рабочие)
CHANNELS = [
    "zhitomir9",
    "zhytomyr_olx", 
    "zhitomir_chat",
    "zhytomyrjob",
    "zt_robota",
    "zhitomir_job",
    "robota_zt",
    "work_zhitomir"
]

# ТОЛЬКО эти ключевые слова
KEYWORDS = [
    "сварщик", "зварник", "сварювальник",
    "разнорабочий", "різноробочий", "подсобник", "підсобник",
    "шукаю роботу", "шукаю підробіток", "шукаю работу",
    "ищу работу", "ищу подработку", "підробіток", "подработка"
]

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


async def parse_telegram_channel(channel, session):
    """Парсинг публичного превью канала"""
    results = []
    url = f"https://t.me/s/{channel}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'uk-UA,uk;q=0.9,ru;q=0.8,en-US;q=0.7,en;q=0.6',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0'
    }
    
    try:
        async with session.get(url, headers=headers, timeout=20, allow_redirects=True) as response:
            logger.info(f"@{channel}: статус {response.status}")
            
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Пробуем разные селекторы
                messages = soup.select('div.tgme_widget_message_wrap')
                if not messages:
                    messages = soup.select('div.tgme_widget_message')
                if not messages:
                    messages = soup.select('[class*="message"]')
                
                logger.info(f"@{channel}: найдено {len(messages)} блоков сообщений")
                
                # Также пробуем найти текст напрямую
                all_text_divs = soup.find_all('div', class_=lambda x: x and 'text' in str(x).lower())
                logger.info(f"@{channel}: найдено {len(all_text_divs)} текстовых блоков")
                
                for msg in messages:
                    try:
                        # Ищем текст сообщения
                        text_elem = msg.select_one('div.tgme_widget_message_text')
                        if not text_elem:
                            text_elem = msg.select_one('[class*="text"]')
                        
                        if not text_elem:
                            continue
                            
                        text = text_elem.get_text(strip=True).lower()
                        
                        # Проверяем ключевые слова
                        found_keyword = None
                        for kw in KEYWORDS:
                            if kw in text:
                                found_keyword = kw
                                break
                        
                        if found_keyword:
                            # Ищем ссылку на сообщение
                            link_elem = msg.select_one('a.tgme_widget_message_date')
                            if not link_elem:
                                link_elem = msg.select_one('a[href*="/"]')
                            
                            link = link_elem.get('href', '') if link_elem else f"https://t.me/{channel}"
                            
                            preview = text_elem.get_text(strip=True)[:200]
                            
                            results.append({
                                'text': preview,
                                'link': link,
                                'source': f'@{channel}',
                                'keyword': found_keyword
                            })
                            logger.info(f"✓ [{found_keyword}] {preview[:50]}...")
                            
                    except Exception as e:
                        logger.debug(f"Ошибка сообщения: {e}")
                        
                # Если ничего не нашли в сообщениях, ищем по всему HTML
                if not results:
                    page_text = soup.get_text().lower()
                    for kw in KEYWORDS:
                        if kw in page_text:
                            logger.info(f"@{channel}: слово '{kw}' есть на странице, но не в структуре")
                            
    except asyncio.TimeoutError:
        logger.warning(f"@{channel}: таймаут")
    except Exception as e:
        logger.error(f"@{channel}: ошибка - {e}")
        
    return results


async def main():
    logger.info("🚀 Запуск прямого парсинга Telegram каналов")
    
    all_results = []
    
    # Используем одну сессию с куками
    jar = aiohttp.CookieJar()
    connector = aiohttp.TCPConnector(ssl=False)
    
    async with aiohttp.ClientSession(cookie_jar=jar, connector=connector) as session:
        for channel in CHANNELS:
            results = await parse_telegram_channel(channel, session)
            all_results.extend(results)
            await asyncio.sleep(2)
    
    # Убираем дубликаты
    seen = set()
    unique = []
    for r in all_results:
        if r['link'] not in seen:
            seen.add(r['link'])
            unique.append(r)
    
    logger.info(f"📊 Итого уникальных: {len(unique)}")
    
    # Формируем сообщение
    if unique:
        message = f"👥 Найдено работников: {len(unique)}\n"
        message += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        message += "🔍 Сварщик | Разнорабочий | Подработка\n\n"
        
        for i, r in enumerate(unique[:15], 1):
            message += f"{i}. [{r['keyword']}]\n"
            message += f"   {r['text'][:100]}...\n"
            message += f"   🔗 {r['link']}\n\n"
    else:
        message = "🔍 Поиск работников\n\n"
        message += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        message += "❌ Не найдено через прямой парсинг\n\n"
        message += "Проверьте вручную каналы:\n"
        for ch in CHANNELS[:4]:
            message += f"• t.me/{ch}\n"
    
    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=message, disable_web_page_preview=True)
    logger.info("✅ Отправлено")
    
    return unique


if __name__ == "__main__":
    asyncio.run(main())
