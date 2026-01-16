"""
Проверка структуры HTML канала
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup

async def check_channel(channel):
    url = f"https://t.me/s/{channel}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'uk-UA,uk;q=0.9',
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            print(f"=== @{channel} ===\n")
            
            # Найдём все сообщения
            messages = soup.select('div.tgme_widget_message_wrap')
            print(f"tgme_widget_message_wrap: {len(messages)}")
            
            # Выведем первые 3 сообщения
            for i, msg in enumerate(messages[:5]):
                text_elem = msg.select_one('div.tgme_widget_message_text')
                if text_elem:
                    text = text_elem.get_text(strip=True)
                    print(f"\n{i+1}. {text[:150]}...")
                    
                    # Проверим на ключевые слова
                    keywords = ["сварщик", "зварник", "разнорабочий", "різноробочий", 
                               "шукаю роботу", "шукаю підробіток", "підробіток", "подработка"]
                    for kw in keywords:
                        if kw in text.lower():
                            print(f"   ✓ НАЙДЕНО: {kw}")
                    
                    # Ссылка
                    link = msg.select_one('a.tgme_widget_message_date')
                    if link:
                        print(f"   Ссылка: {link.get('href')}")

# Проверим несколько каналов
channels = ["zhitomir9", "zhytomyr_olx", "zt_robota"]
for ch in channels:
    asyncio.run(check_channel(ch))
    print("\n" + "="*50 + "\n")
