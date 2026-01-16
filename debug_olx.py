"""
Отладочный скрипт для проверки парсинга OLX
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup

async def test_olx():
    # Пробуем разные варианты URL
    urls = [
        "https://www.olx.ua/d/uk/robota/zhytomyr/",
        "https://www.olx.ua/uk/robota/zhytomyr/",
        "https://www.olx.ua/d/uk/robota/",
        "https://www.olx.ua/uk/robota/"
    ]
    
    async with aiohttp.ClientSession() as session:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        for url in urls:
            print(f"\n🔍 Проверяю: {url}")
            
            async with session.get(url, headers=headers, timeout=15) as response:
                print(f"Статус: {response.status}")
                
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Пробуем разные селекторы
                    ads1 = soup.find_all('div', {'data-cy': 'l-card'})
                    ads2 = soup.find_all('div', class_='css-1sw7q4x')
                    ads3 = soup.find_all('a', href=lambda x: x and '/d/uk/obyavlenie/' in x)
                    
                    print(f"data-cy='l-card': {len(ads1)}")
                    print(f"class='css-1sw7q4x': {len(ads2)}")
                    print(f"ссылки на объявления: {len(ads3)}")
                    
                    if ads3:
                        print("\n📋 Первые объявления:")
                        for i, ad in enumerate(ads3[:3], 1):
                            title = ad.get_text(strip=True)
                            link = ad.get('href', '')
                            print(f"{i}. {title[:80]}")
                            print(f"   {link}")
                        break

if __name__ == "__main__":
    asyncio.run(test_olx())
