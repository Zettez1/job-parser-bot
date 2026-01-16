"""
Поиск работников через Google
Ищет в Telegram и на сайтах объявления о поиске работы
"""
import asyncio
import logging
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
from telegram import Bot
import re
import urllib.parse

# Настройки
BOT_TOKEN = "8302303298:AAGH3Nllv4JaQRoi8Em8rO1-L_zGinN-gVM"
CHAT_ID = "-1003407248691"

# Поисковые запросы
SEARCH_QUERIES = [
    'site:t.me "шукаю роботу" житомир',
    'site:t.me "шукаю підробіток" житомир',
    'site:t.me сварщик житомир "шукаю"',
    'site:t.me різноробочий житомир',
    'site:olx.ua "шукаю роботу" житомир',
    'site:olx.ua сварщик житомир резюме',
]

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def search_google(query, session):
    """Поиск в Google"""
    results = []
    
    # Кодируем запрос
    encoded_query = urllib.parse.quote(query)
    url = f"https://www.google.com/search?q={encoded_query}&num=20&hl=uk"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    
    try:
        async with session.get(url, headers=headers, timeout=15) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Ищем результаты поиска
                for g in soup.find_all('div', class_='g'):
                    try:
                        # Ссылка
                        link_elem = g.find('a')
                        if not link_elem:
                            continue
                        link = link_elem.get('href', '')
                        
                        # Заголовок
                        title_elem = g.find('h3')
                        title = title_elem.get_text(strip=True) if title_elem else ''
                        
                        # Описание
                        desc_elem = g.find('div', class_='VwiC3b')
                        desc = desc_elem.get_text(strip=True) if desc_elem else ''
                        
                        if link and (title or desc):
                            # Фильтруем только Telegram и OLX
                            if 't.me' in link or 'olx.ua' in link:
                                results.append({
                                    'title': title,
                                    'link': link,
                                    'description': desc[:200],
                                    'query': query
                                })
                                logger.info(f"✓ Найдено: {title[:50]}...")
                    except Exception as e:
                        continue
                        
            elif response.status == 429:
                logger.warning("⚠️ Google заблокировал (429). Ждём...")
                await asyncio.sleep(30)
            else:
                logger.warning(f"Google статус: {response.status}")
                
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        
    return results


async def search_duckduckgo(query, session):
    """Альтернативный поиск через DuckDuckGo HTML"""
    results = []
    
    encoded_query = urllib.parse.quote(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        async with session.get(url, headers=headers, timeout=15) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                for result in soup.find_all('div', class_='result'):
                    try:
                        link_elem = result.find('a', class_='result__a')
                        if not link_elem:
                            continue
                            
                        link = link_elem.get('href', '')
                        title = link_elem.get_text(strip=True)
                        
                        snippet_elem = result.find('a', class_='result__snippet')
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                        
                        if link and ('t.me' in link or 'olx.ua' in link):
                            results.append({
                                'title': title,
                                'link': link,
                                'description': snippet[:200],
                                'query': query
                            })
                            logger.info(f"✓ DDG: {title[:50]}...")
                    except:
                        continue
                        
    except Exception as e:
        logger.error(f"DuckDuckGo ошибка: {e}")
        
    return results


async def main():
    """Главная функция"""
    logger.info("🚀 Запуск поиска работников через поисковики")
    
    all_results = []
    
    async with aiohttp.ClientSession() as session:
        for query in SEARCH_QUERIES:
            logger.info(f"🔍 Поиск: {query}")
            
            # Пробуем DuckDuckGo (меньше блокировок)
            results = await search_duckduckgo(query, session)
            all_results.extend(results)
            
            await asyncio.sleep(2)  # Пауза между запросами
    
    # Убираем дубликаты
    seen = set()
    unique_results = []
    for r in all_results:
        if r['link'] not in seen:
            seen.add(r['link'])
            unique_results.append(r)
    
    logger.info(f"📊 Всего найдено уникальных: {len(unique_results)}")
    
    # Формируем сообщение
    if not unique_results:
        message = "🔍 Поиск работников\n\n"
        message += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        message += "❌ Через поисковики ничего не найдено\n\n"
        message += "💡 Попробуйте вручную:\n"
        message += "• t.me/zhitomir9\n"
        message += "• t.me/zhytomyr_olx"
    else:
        message = f"👥 Найдено: {len(unique_results)} результатов\n"
        message += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        
        for i, r in enumerate(unique_results[:10], 1):
            message += f"{i}. {r['title'][:60]}\n"
            message += f"   {r['description'][:80]}...\n"
            message += f"   🔗 {r['link']}\n\n"
            
            if len(message) > 3500:
                break
    
    # Отправляем
    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=message, disable_web_page_preview=True)
    logger.info("✅ Отправлено")


if __name__ == "__main__":
    asyncio.run(main())
