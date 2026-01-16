"""
Парсер резюме с Rabota.ua и Work.ua
Ищет: сварщиков, разнорабочих, людей ищущих работу
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
from telegram import Bot
import logging
import re

BOT_TOKEN = "8302303298:AAGH3Nllv4JaQRoi8Em8rO1-L_zGinN-gVM"
CHAT_ID = "-1003407248691"

KEYWORDS = ["сварщик", "зварник", "разнорабочий", "різноробочий", "підробіток"]

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


async def parse_rabotaua_resumes(session):
    """Парсинг резюме с Rabota.ua"""
    results = []
    
    urls = [
        "https://rabota.ua/candidates/zhitomir/%D1%81%D0%B2%D0%B0%D1%80%D1%89%D0%B8%D0%BA",  # сварщик
        "https://rabota.ua/candidates/zhitomir/%D1%80%D0%B0%D0%B1%D0%BE%D1%87%D0%B8%D0%B9",  # рабочий
        "https://rabota.ua/candidates/zhitomir",  # все резюме
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'uk-UA,uk;q=0.9',
    }
    
    for url in urls:
        try:
            logger.info(f"Проверяю: {url}")
            async with session.get(url, headers=headers, timeout=15) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Ищем карточки резюме
                    cards = soup.find_all('div', class_=re.compile('.*card.*|.*resume.*'))
                    logger.info(f"Найдено карточек: {len(cards)}")
                    
                    for card in cards[:15]:
                        try:
                            # Ищем заголовок
                            title_elem = card.find(['h2', 'h3', 'a'])
                            if not title_elem:
                                continue
                            
                            title = title_elem.get_text(strip=True)
                            link = title_elem.get('href', '') if title_elem.name == 'a' else ''
                            
                            if not link:
                                link_elem = card.find('a', href=True)
                                link = link_elem.get('href', '') if link_elem else ''
                            
                            if link and not link.startswith('http'):
                                link = 'https://rabota.ua' + link
                            
                            if title and len(title) > 10:
                                results.append({
                                    'text': title,
                                    'link': link or url,
                                    'source': 'Rabota.ua',
                                    'keyword': 'резюме'
                                })
                                logger.info(f"✓ {title[:60]}...")
                        except:
                            continue
                            
        except Exception as e:
            logger.error(f"Ошибка: {e}")
        
        await asyncio.sleep(2)
    
    return results


async def parse_workua_resumes(session):
    """Парсинг резюме с Work.ua"""
    results = []
    
    urls = [
        "https://www.work.ua/resumes-zhytomyr/",
        "https://www.work.ua/resumes-zhytomyr-%D1%81%D0%B2%D0%B0%D1%80%D1%89%D0%B8%D0%BA/",
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'uk-UA,uk;q=0.9',
    }
    
    for url in urls:
        try:
            logger.info(f"Проверяю: {url}")
            async with session.get(url, headers=headers, timeout=15) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Ищем резюме
                    resumes = soup.find_all(['div', 'article'], class_=re.compile('.*resume.*|.*card.*'))
                    logger.info(f"Найдено резюме: {len(resumes)}")
                    
                    for resume in resumes[:15]:
                        try:
                            title_elem = resume.find(['h2', 'h3', 'a'])
                            if not title_elem:
                                continue
                            
                            title = title_elem.get_text(strip=True)
                            link = title_elem.get('href', '') if title_elem.name == 'a' else ''
                            
                            if not link:
                                link_elem = resume.find('a', href=True)
                                link = link_elem.get('href', '') if link_elem else ''
                            
                            if link and not link.startswith('http'):
                                link = 'https://www.work.ua' + link
                            
                            if title and len(title) > 10:
                                results.append({
                                    'text': title,
                                    'link': link or url,
                                    'source': 'Work.ua',
                                    'keyword': 'резюме'
                                })
                                logger.info(f"✓ {title[:60]}...")
                        except:
                            continue
                            
        except Exception as e:
            logger.error(f"Ошибка: {e}")
        
        await asyncio.sleep(2)
    
    return results


async def main():
    logger.info("🚀 Парсинг резюме с сайтов вакансий")
    logger.info("🔍 Житомир: сварщик, разнорабочий\n")
    
    all_results = []
    
    async with aiohttp.ClientSession() as session:
        # Rabota.ua
        logger.info("1️⃣ Rabota.ua...")
        results = await parse_rabotaua_resumes(session)
        all_results.extend(results)
        
        # Work.ua
        logger.info("\n2️⃣ Work.ua...")
        results = await parse_workua_resumes(session)
        all_results.extend(results)
    
    # Убираем дубликаты
    seen = set()
    unique = []
    for r in all_results:
        if r['link'] not in seen:
            seen.add(r['link'])
            unique.append(r)
    
    logger.info(f"\n📊 Всего найдено: {len(unique)} резюме")
    
    # Формируем сообщение
    if unique:
        message = f"👥 Найдено резюме: {len(unique)}\n"
        message += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        message += "🔍 Житомир - Сварщик, Разнорабочий\n\n"
        
        for i, r in enumerate(unique[:10], 1):
            message += f"{i}. {r['text'][:80]}\n"
            message += f"   🔗 {r['link']}\n"
            message += f"   📱 {r['source']}\n\n"
            
            if len(message) > 3500:
                break
    else:
        message = "🔍 Поиск резюме\n\n"
        message += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        message += "❌ Резюме не найдены автоматически\n\n"
        message += "💡 Проверьте вручную:\n"
        message += "• rabota.ua/candidates/zhitomir\n"
        message += "• work.ua/resumes-zhytomyr/\n"
        message += "• t.me/zhitomir9\n"
        message += "• t.me/zhytomyr_olx"
    
    # Отправляем
    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=message, disable_web_page_preview=True)
    logger.info("✅ Отправлено!")


if __name__ == "__main__":
    asyncio.run(main())
