"""
Поиск резюме (людей ищущих работу) на OLX
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup

async def search_olx_resumes():
    """Ищем людей которые ищут работу"""
    
    # Поисковые запросы для резюме
    queries = [
        "шукаю роботу житомир",
        "шукаю підробіток житомир",
        "сварщик шукаю роботу житомир",
        "різноробочий шукаю роботу житомир",
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'uk-UA,uk;q=0.9',
    }
    
    all_results = []
    
    async with aiohttp.ClientSession() as session:
        for query in queries:
            import urllib.parse
            encoded = urllib.parse.quote(query)
            url = f"https://www.olx.ua/uk/list/q-{encoded}/"
            
            print(f"\n🔍 Поиск: {query}")
            print(f"URL: {url}")
            
            try:
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        ads = soup.find_all('div', {'data-cy': 'l-card'})
                        print(f"Найдено объявлений: {len(ads)}")
                        
                        for ad in ads[:10]:
                            try:
                                # Заголовок
                                title_elem = ad.find('h6')
                                if not title_elem:
                                    continue
                                
                                title = title_elem.get_text(strip=True)
                                
                                # Ссылка
                                link_elem = ad.find('a', href=True)
                                link = link_elem.get('href', '') if link_elem else ''
                                if link and not link.startswith('http'):
                                    link = 'https://www.olx.ua' + link
                                
                                # Выводим ВСЕ объявления для анализа
                                print(f"  {title[:100]}...")
                                
                                # Проверяем что это резюме (ищут работу)
                                text_lower = title.lower()
                                resume_keywords = ["шукаю", "ищу", "потрібна", "нужна", "готовий", "готов"]
                                
                                if any(kw in text_lower for kw in resume_keywords):
                                    all_results.append({
                                        'title': title,
                                        'link': link,
                                        'query': query
                                    })
                                    print(f"    ✓ РЕЗЮМЕ!")
                                    
                            except Exception as e:
                                continue
                                
            except Exception as e:
                print(f"❌ Ошибка: {e}")
            
            await asyncio.sleep(2)
    
    print(f"\n📊 Всего найдено резюме: {len(all_results)}")
    for i, r in enumerate(all_results, 1):
        print(f"{i}. {r['title']}")
        print(f"   {r['link']}\n")

asyncio.run(search_olx_resumes())
