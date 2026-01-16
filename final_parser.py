"""
ФИНАЛЬНЫЙ РАБОЧИЙ ПАРСЕР
Использует комбинацию методов для поиска работников
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
from telegram import Bot
import logging

BOT_TOKEN = "8302303298:AAGH3Nllv4JaQRoi8Em8rO1-L_zGinN-gVM"
CHAT_ID = "-1003407248691"
MESSAGE_THREAD_ID = int(os.getenv("MESSAGE_THREAD_ID", "187"))
# ТОЛЬКО эти ключевые слова
KEYWORDS = [
    "сварщик", "зварник", "сварювальник",
    "разнорабочий", "різноробочий", "подсобник", "підсобник",
    "шукаю роботу", "шукаю підробіток", "підробіток", "подработка"
]

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


async def search_telegram_via_google(query, session):
    """Поиск через Google site:t.me"""
    results = []
    
    # DuckDuckGo (меньше блокировок)
    import urllib.parse
    encoded = urllib.parse.quote(f'site:t.me {query} житомир')
    url = f"https://html.duckduckgo.com/html/?q={encoded}"
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        async with session.get(url, headers=headers, timeout=15) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                for result in soup.find_all('div', class_='result')[:10]:
                    try:
                        link_elem = result.find('a', class_='result__a')
                        if not link_elem:
                            continue
                        
                        link = link_elem.get('href', '')
                        title = link_elem.get_text(strip=True)
                        
                        snippet_elem = result.find('a', class_='result__snippet')
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                        
                        if 't.me' in link and link not in ['https://t.me/', 'https://telegram.me/']:
                            results.append({
                                'text': f"{title} - {snippet}"[:200],
                                'link': link,
                                'source': 'Поиск',
                                'keyword': query
                            })
                            logger.info(f"✓ Найдено: {title[:50]}...")
                    except:
                        continue
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
    
    return results


async def parse_public_channel(channel, session):
    """Парсинг публичного канала (если доступен)"""
    results = []
    url = f"https://t.me/s/{channel}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'uk-UA,uk;q=0.9',
    }
    
    try:
        async with session.get(url, headers=headers, timeout=15) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                messages = soup.select('div.tgme_widget_message_wrap')
                
                for msg in messages:
                    text_elem = msg.select_one('div.tgme_widget_message_text')
                    if not text_elem:
                        continue
                    
                    text = text_elem.get_text(strip=True).lower()
                    
                    for kw in KEYWORDS:
                        if kw in text:
                            link_elem = msg.select_one('a.tgme_widget_message_date')
                            link = link_elem.get('href', '') if link_elem else f"https://t.me/{channel}"
                            
                            results.append({
                                'text': text_elem.get_text(strip=True)[:200],
                                'link': link,
                                'source': f'@{channel}',
                                'keyword': kw
                            })
                            logger.info(f"✓ [{kw}] в @{channel}")
                            break
    except:
        pass
    
    return results


async def main():
    logger.info("🚀 ФИНАЛЬНЫЙ ПАРСЕР - Поиск работников")
    logger.info("🔍 Ключевые слова: сварщик, разнорабочий, підробіток\n")
    
    all_results = []
    
    async with aiohttp.ClientSession() as session:
        # 1. Поиск через поисковики
        logger.info("1️⃣ Поиск через DuckDuckGo...")
        for keyword in ["сварщик", "різноробочий", "шукаю роботу", "підробіток"]:
            results = await search_telegram_via_google(keyword, session)
            all_results.extend(results)
            await asyncio.sleep(2)
        
        # 2. Попытка парсинга публичных каналов
        logger.info("\n2️⃣ Проверка публичных каналов...")
        channels = ["zt_robota", "zhitomir_job", "robota_zhytomyr"]
        for ch in channels:
            results = await parse_public_channel(ch, session)
            all_results.extend(results)
            await asyncio.sleep(1)
    
    # Убираем дубликаты
    seen = set()
    unique = []
    for r in all_results:
        if r['link'] not in seen:
            seen.add(r['link'])
            unique.append(r)
    
    logger.info(f"\n📊 Всего найдено: {len(unique)} результатов")
    
    # Формируем сообщение
    if unique:
        message = f"👥 Найдено работников: {len(unique)}\n"
        message += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        message += "🔍 Сварщик | Разнорабочий | Підробіток\n\n"
        
        for i, r in enumerate(unique[:10], 1):
            message += f"{i}. [{r['keyword']}]\n"
            message += f"   {r['text'][:100]}...\n"
            message += f"   🔗 {r['link']}\n\n"
            
            if len(message) > 3500:
                break
        
        message += "\n💡 Также проверьте вручную:\n"
        message += "• t.me/zhitomir9\n"
        message += "• t.me/zhytomyr_olx"
    else:
        message = "🔍 Поиск работников\n\n"
        message += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        message += "❌ Автоматический поиск не дал результатов\n\n"
        message += "💡 Проверьте вручную группы:\n"
        message += "• t.me/zhitomir9 - Житомир Чат\n"
        message += "• t.me/zhytomyr_olx - Працевлаштування\n\n"
        message += "🔍 Ищите: сварщик, різноробочий, шукаю роботу"
    
    # Отправляем
    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=message, disable_web_page_preview=True)
    logger.info("✅ Сообщение отправлено!")


if __name__ == "__main__":
    asyncio.run(main())
