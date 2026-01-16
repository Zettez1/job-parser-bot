"""
Тест разных способов парсинга OLX
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json

async def test_olx_methods():
    """Тестируем разные методы доступа к OLX"""
    
    # Попробуем мобильную версию
    urls_to_test = [
        ("Desktop", "https://www.olx.ua/d/uk/zhitomir/q-%D1%81%D0%B2%D0%B0%D1%80%D1%89%D0%B8%D0%BA/"),
        ("Mobile", "https://m.olx.ua/uk/zhitomir/q-%D1%81%D0%B2%D0%B0%D1%80%D1%89%D0%B8%D0%BA/"),
        ("Search", "https://www.olx.ua/uk/list/q-%D1%81%D0%B2%D0%B0%D1%80%D1%89%D0%B8%D0%BA-%D0%B6%D0%B8%D1%82%D0%BE%D0%BC%D0%B8%D1%80/"),
    ]
    
    headers_desktop = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'uk-UA,uk;q=0.9,ru;q=0.8,en;q=0.7',
        'Referer': 'https://www.olx.ua/',
    }
    
    headers_mobile = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'uk-UA,uk;q=0.9',
    }
    
    async with aiohttp.ClientSession() as session:
        for name, url in urls_to_test:
            print(f"\n{'='*60}")
            print(f"Тест: {name}")
            print(f"URL: {url}")
            print('='*60)
            
            headers = headers_mobile if 'm.olx' in url else headers_desktop
            
            try:
                async with session.get(url, headers=headers, timeout=15, allow_redirects=True) as response:
                    print(f"Статус: {response.status}")
                    print(f"Финальный URL: {response.url}")
                    
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Ищем объявления разными способами
                        ads1 = soup.find_all('div', {'data-cy': 'l-card'})
                        ads2 = soup.find_all('div', class_=lambda x: x and 'offer' in str(x).lower())
                        ads3 = soup.find_all('a', href=lambda x: x and '/d/uk/obyavlenie/' in str(x))
                        
                        print(f"data-cy='l-card': {len(ads1)}")
                        print(f"class*='offer': {len(ads2)}")
                        print(f"href*='/d/uk/obyavlenie/': {len(ads3)}")
                        
                        # Выводим первые найденные
                        if ads1:
                            print("\nПервое объявление (data-cy):")
                            print(ads1[0].get_text(strip=True)[:200])
                        elif ads3:
                            print("\nПервая ссылка:")
                            print(ads3[0].get('href'))
                            print(ads3[0].get_text(strip=True)[:100])
                        else:
                            print("\n⚠️ Объявления не найдены")
                            # Проверим, есть ли вообще контент
                            if len(html) < 5000:
                                print(f"HTML слишком короткий: {len(html)} байт")
                            else:
                                print(f"HTML размер: {len(html)} байт")
                    else:
                        print(f"❌ Ошибка: статус {response.status}")
                        
            except Exception as e:
                print(f"❌ Исключение: {e}")
            
            await asyncio.sleep(2)

asyncio.run(test_olx_methods())
