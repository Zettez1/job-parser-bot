"""
Отладочный скрипт для проверки парсинга Telegram каналов
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup

async def test_channel(channel):
    url = f"https://t.me/s/{channel}"
    print(f"\n🔍 Проверяю канал: {url}")
    
    async with aiohttp.ClientSession() as session:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        async with session.get(url, headers=headers, timeout=15) as response:
            print(f"Статус: {response.status}")
            
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Пробуем разные селекторы
                messages1 = soup.find_all('div', class_='tgme_widget_message_text')
                messages2 = soup.find_all('div', class_='tgme_widget_message')
                messages3 = soup.find_all('div', {'class': lambda x: x and 'message' in x.lower()})
                
                print(f"tgme_widget_message_text: {len(messages1)}")
                print(f"tgme_widget_message: {len(messages2)}")
                print(f"любые message: {len(messages3)}")
                
                # Выводим первые 3 сообщения
                for i, msg in enumerate(messages2[:3], 1):
                    text_elem = msg.find('div', class_='tgme_widget_message_text')
                    if text_elem:
                        text = text_elem.get_text(strip=True)
                        print(f"\nСообщение {i}: {text[:100]}...")

async def main():
    await test_channel("zhitomir9")
    await test_channel("zhytomyr_olx")

if __name__ == "__main__":
    asyncio.run(main())
