"""
РАБОЧИЙ ПАРСЕР РЕЗЮМЕ
Ищет сварщиков, разнорабочих на Work.ua и Rabota.ua
"""
import asyncio
import logging
import os
from datetime import datetime, time
import aiohttp
from aiohttp import web
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.error import TelegramError
import re

# ============= НАСТРОЙКИ =============
# Переменные окружения для безопасности (настройте на Render)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8302303298:AAGH3Nllv4JaQRoi8Em8rO1-L_zGinN-gVM")
CHAT_ID = os.getenv("CHAT_ID", "-1003686632666")  # Новая группа
MESSAGE_THREAD_ID = os.getenv("MESSAGE_THREAD_ID", None)  # ID темы HR(AI)
SEND_STARTUP_MSG = os.getenv("SEND_STARTUP_MSG", "false").lower() == "true"  # Отправлять приветствие
SEARCH_TIME = time(hour=11, minute=0)  # 11:00 UTC = 13:00 Киев (1 час дня)
PORT = int(os.getenv("PORT", 10000))

# Telegram каналы для мониторинга (публичные ссылки)
TELEGRAM_CHANNELS = [
    "zhitomir9",  # Житомир Чат (1 707 участников)
    "zhytomyr_olx",  # Працевлаштування
]

# =====================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class JobParser:
    """Парсер для поиска людей, которые ищут работу"""
    
    def __init__(self):
        self.city = "житомир"
        # Ключевые фразы для поиска людей, ищущих работу
        self.job_search_keywords = [
            # Украинский
            "шукаю роботу", "шукаю робот", "шукаю підробіток", "шукаю підзаробіток",
            "шукаю работу", "шукаю подработку",
            "потрібна робота", "потрібна работа", "треба робота",
            "готовий до роботи", "готовий працювати", "готов працювати",
            "хочу працювати", "можу працювати", "розгляну пропозиції",
            # Русский
            "ищу работу", "ищу подработку", "ищу заработок", "ищу робот",
            "нужна работа", "нужна подработка", "надо работу",
            "готов к работе", "готов работать", "хочу работать", "могу работать",
            "рассмотрю предложения", "рассмотрю варианты",
            # Короткие варианты
            "шукаю", "ищу", "треба", "нужна", "надо"
        ]
        
        # Профессии и навыки (расширенный список)
        self.professions = [
            # Сварщики
            "сварщик", "зварник", "сварювальник", "сварочник",
            # Разнорабочие
            "разнорабочий", "різноробочий", "подсобник", "підсобник",
            "робітник", "рабочий", "працівник", "работник",
            # Строители
            "будівельник", "строитель", "будівник", "монтажник", "монтажер",
            # Водители
            "водій", "водитель", "шофер", "водитель категории",
            # Грузчики
            "вантажник", "грузчик", "погрузчик",
            # Специалисты
            "слюсар", "слесарь", "токар", "токарь",
            "електрик", "электрик", "електромонтер",
            "зварювальник", "сварювальник",
            # Другие рабочие специальности
            "столяр", "маляр", "штукатур", "плиточник",
            "механік", "механик", "автослюсар", "автослесарь",
            "оператор", "різник", "мясник"
        ]
        
    async def parse_workua_resumes(self):
        """Парсинг резюме с Work.ua - ТОЛЬКО сварщики и разнорабочие"""
        results = []
        
        # ТОЛЬКО профильные запросы
        urls = [
            "https://www.work.ua/resumes-zhytomyr-%D1%81%D0%B2%D0%B0%D1%80%D1%89%D0%B8%D0%BA/",  # сварщик
            "https://www.work.ua/resumes-zhytomyr-%D1%80%D0%B0%D0%B1%D0%BE%D1%87%D0%B8%D0%B9/",  # рабочий
        ]
        
        # Ключевые слова для фильтрации (ТОЛЬКО нужные профессии)
        target_keywords = [
            "сварщик", "зварник", "сварювальник", "зварювальник", "електрозварник", "электрозварщик",
            "разнорабочий", "різноробочий", "подсобник", "підсобник", "робітник", "рабочий"
        ]
        
        async with aiohttp.ClientSession() as session:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept-Language': 'uk-UA,uk;q=0.9',
            }
            
            for url in urls:
                try:
                    logger.info(f"Work.ua: {url}")
                    async with session.get(url, headers=headers, timeout=15) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Ищем резюме
                            resumes = soup.find_all(['div', 'article'], class_=re.compile('.*resume.*|.*card.*'))
                            logger.info(f"Work.ua: найдено {len(resumes)} резюме")
                            
                            for resume in resumes[:20]:
                                try:
                                    title_elem = resume.find(['h2', 'h3', 'a'])
                                    if not title_elem:
                                        continue
                                    
                                    title = title_elem.get_text(strip=True)
                                    title_lower = title.lower()
                                    
                                    # ФИЛЬТР: только если есть нужные ключевые слова
                                    if not any(kw in title_lower for kw in target_keywords):
                                        continue
                                    
                                    link = title_elem.get('href', '') if title_elem.name == 'a' else ''
                                    
                                    if not link:
                                        link_elem = resume.find('a', href=True)
                                        link = link_elem.get('href', '') if link_elem else ''
                                    
                                    if link and not link.startswith('http'):
                                        link = 'https://www.work.ua' + link
                                    
                                    if title and len(title) > 10:
                                        results.append({
                                            'name': title,
                                            'link': link or url,
                                            'source': 'Work.ua'
                                        })
                                        logger.info(f"✓ {title[:60]}...")
                                except:
                                    continue
                                    
                except Exception as e:
                    logger.error(f"Ошибка Work.ua: {e}")
                
                await asyncio.sleep(2)
        
        return results
    
    async def parse_olx(self):
        """Парсинг OLX - раздел резюме (люди ищут работу)"""
        results = []
        try:
            # Раздел "Резюме" на OLX
            url = "https://www.olx.ua/d/uk/robota/rezyume/zhitomir/"
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Ищем объявления (увеличиваем до 30)
                        ads = soup.find_all('div', {'data-cy': 'l-card'})[:30]
                        logger.info(f"OLX: найдено {len(ads)} объявлений в разделе резюме")
                        
                        for ad in ads:
                            try:
                                title_elem = ad.find('h6')
                                link_elem = ad.find('a')
                                
                                if title_elem and link_elem:
                                    title = title_elem.get_text(strip=True)
                                    link = link_elem.get('href', '')
                                    
                                    if not link.startswith('http'):
                                        link = 'https://www.olx.ua' + link
                                    
                                    # Проверяем ключевые слова и профессии
                                    text_lower = title.lower()
                                    has_job_search = any(kw in text_lower for kw in self.job_search_keywords)
                                    has_profession = any(prof in text_lower for prof in self.professions)
                                    
                                    # В разделе резюме все объявления релевантны, но приоритет по ключевым словам
                                    if has_job_search or has_profession or len(results) < 10:
                                        logger.info(f"✓ Найдено на OLX: {title[:70]}...")
                                        results.append({
                                            'name': title,
                                            'link': link,
                                            'source': 'OLX Резюме'
                                        })
                            except Exception as e:
                                logger.debug(f"Ошибка обработки OLX карточки: {e}")
                                
        except Exception as e:
            logger.error(f"Ошибка парсинга OLX: {e}")
            
        return results
    
    async def parse_rabotaua_lite(self):
        """Попытка парсинга Robota.ua (облегчённая версия)"""
        results = []
        try:
            url = "https://rabota.ua/zapros/zhitomir/%D1%81%D0%B2%D0%B0%D1%80%D1%89%D0%B8%D0%BA"
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Базовый поиск ссылок на вакансии
                        links = soup.find_all('a', href=re.compile(r'/company\d+/vacancy\d+'))
                        
                        for link in links[:5]:
                            try:
                                title = link.get_text(strip=True)
                                href = link.get('href', '')
                                
                                if not href.startswith('http'):
                                    href = 'https://rabota.ua' + href
                                
                                if title and len(title) > 10:
                                    results.append({
                                        'name': title,
                                        'link': href,
                                        'source': 'Rabota.ua'
                                    })
                            except Exception as e:
                                logger.debug(f"Ошибка обработки: {e}")
                                
        except Exception as e:
            logger.error(f"Ошибка парсинга Rabota.ua: {e}")
            
        return results
    
    async def parse_workua_lite(self):
        """Попытка парсинга Work.ua"""
        results = []
        try:
            url = "https://www.work.ua/jobs-zhytomyr/"
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        jobs = soup.find_all('div', class_='job-link')
                        
                        for job in jobs[:5]:
                            try:
                                link_elem = job.find('a')
                                if link_elem:
                                    title = link_elem.get_text(strip=True)
                                    link = 'https://www.work.ua' + link_elem.get('href', '')
                                    
                                    results.append({
                                        'name': title,
                                        'link': link,
                                        'source': 'Work.ua'
                                    })
                            except Exception as e:
                                logger.debug(f"Ошибка обработки: {e}")
                                
        except Exception as e:
            logger.error(f"Ошибка парсинга Work.ua: {e}")
            
        return results
    
    async def parse_olx_search(self):
        """Парсинг OLX через поиск - РАБОЧИЙ МЕТОД"""
        results = []
        
        # Поисковые запросы
        queries = [
            "сварщик житомир",
            "різноробочий житомир",
        ]
        
        async with aiohttp.ClientSession() as session:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept-Language': 'uk-UA,uk;q=0.9',
            }
            
            for query in queries:
                try:
                    import urllib.parse
                    encoded = urllib.parse.quote(query)
                    url = f"https://www.olx.ua/uk/list/q-{encoded}/"
                    
                    logger.info(f"OLX: поиск '{query}'")
                    async with session.get(url, headers=headers, timeout=15) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            ads = soup.find_all('div', {'data-cy': 'l-card'})
                            logger.info(f"OLX: найдено {len(ads)} объявлений")
                            
                            for ad in ads[:10]:
                                try:
                                    title_elem = ad.find('h6')
                                    if not title_elem:
                                        continue
                                    
                                    title = title_elem.get_text(strip=True)
                                    
                                    # Ссылка
                                    link_elem = ad.find('a', href=True)
                                    link = link_elem.get('href', '') if link_elem else ''
                                    if link and not link.startswith('http'):
                                        link = 'https://www.olx.ua' + link
                                    
                                    # Фильтр: только сварщики и разнорабочие
                                    title_lower = title.lower()
                                    target_words = ["сварщик", "зварник", "зварювальник", "різноробочий", "разнорабочий"]
                                    
                                    if any(w in title_lower for w in target_words):
                                        results.append({
                                            'name': title,
                                            'link': link,
                                            'source': 'OLX'
                                        })
                                        logger.info(f"✓ {title[:60]}...")
                                        
                                except:
                                    continue
                                    
                except Exception as e:
                    logger.error(f"Ошибка OLX: {e}")
                
                await asyncio.sleep(2)
        
        return results
    
    async def get_all_candidates(self):
        """Собрать всех кандидатов из всех источников"""
        all_candidates = []
        
        # Парсим Work.ua (РАБОТАЕТ!)
        logger.info("🔍 Парсинг Work.ua...")
        workua_results = await self.parse_workua_resumes()
        all_candidates.extend(workua_results)
        
        # Парсим OLX (РАБОТАЕТ!)
        logger.info("🔍 Парсинг OLX...")
        olx_results = await self.parse_olx_search()
        all_candidates.extend(olx_results)
        
        # Удаляем дубликаты по ссылкам
        seen = set()
        unique_candidates = []
        for candidate in all_candidates:
            if candidate['link'] not in seen:
                seen.add(candidate['link'])
                unique_candidates.append(candidate)
        
        return unique_candidates


class TelegramJobBot:
    """Telegram бот для отправки результатов"""
    
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.parser = JobParser()
        
    async def send_daily_report(self):
        """Отправить ежедневный отчет"""
        logger.info("Начинаю поиск кандидатов...")
        
        candidates = await self.parser.get_all_candidates()
        
        if not candidates:
            message = f"🔍 Поиск работников\n\n"
            message += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            message += "❌ Резюме не найдены\n\n"
            message += "💡 Проверьте вручную:\n"
            message += "• work.ua/resumes-zhytomyr/\n"
            message += "• t.me/zhitomir9\n"
            message += "• t.me/zhytomyr_olx"
        else:
            message = f"👥 Найдено резюме: {len(candidates)}\n"
            message += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            message += f"🔍 Сварщик | Разнорабочий | Підробіток\n\n"
            
            for i, candidate in enumerate(candidates, 1):
                message += f"{i}. {candidate['name'][:80]}\n"
                message += f"   🔗 {candidate['link']}\n"
                message += f"   📱 {candidate['source']}\n\n"
                
                if len(message) > 3500:
                    message += f"... и ещё {len(candidates) - i} резюме"
                    break
            
            message += "\n💼 Источники: Work.ua, OLX"
        
        try:
            bot = Bot(token=self.token)
            thread_id = int(MESSAGE_THREAD_ID) if MESSAGE_THREAD_ID else None
            await bot.send_message(
                chat_id=self.chat_id, 
                text=message, 
                disable_web_page_preview=True,
                message_thread_id=thread_id
            )
            logger.info(f"Сообщение успешно отправлено" + (f" в тему {thread_id}" if thread_id else ""))
        except Exception as e:
            logger.error(f"Ошибка отправки: {e}")
    
    async def scheduled_task(self):
        """Задача по расписанию"""
        while True:
            now = datetime.now().time()
            target = SEARCH_TIME
            
            current_seconds = now.hour * 3600 + now.minute * 60 + now.second
            target_seconds = target.hour * 3600 + target.minute * 60
            
            if current_seconds < target_seconds:
                wait_seconds = target_seconds - current_seconds
            else:
                wait_seconds = 86400 - current_seconds + target_seconds
            
            logger.info(f"Следующий запуск через {wait_seconds // 3600} ч {(wait_seconds % 3600) // 60} мин")
            
            await asyncio.sleep(wait_seconds)
            await self.send_daily_report()
    
    async def send_startup_message(self):
        """Отправить сообщение о запуске"""
        message = "🤖 AI Head Hunter deployed\n\n"
        message += "✅ Бот успешно запущен на Render\n"
        message += f"📅 Время отправки: 13:00 Киев (каждый день)\n"
        message += f"🔍 Источники: Work.ua, OLX\n"
        message += f"💼 Ищу: Сварщики, Разнорабочие\n\n"
        message += f"Следующий отчёт: сегодня в 13:00"
        
        try:
            bot = Bot(token=self.token)
            thread_id = int(MESSAGE_THREAD_ID) if MESSAGE_THREAD_ID else None
            await bot.send_message(
                chat_id=self.chat_id, 
                text=message,
                message_thread_id=thread_id
            )
            logger.info("✅ Приветственное сообщение отправлено")
        except Exception as e:
            logger.error(f"Ошибка отправки приветствия: {e}")
    
    async def run(self):
        """Запустить бота"""
        logger.info("Бот запущен!")
        logger.info(f"Время отправки: {SEARCH_TIME} (13:00 Киев)")
        logger.info(f"Chat ID: {self.chat_id}")
        logger.info(f"Мониторинг каналов: {', '.join(['@' + ch for ch in TELEGRAM_CHANNELS])}")
        
        # Проверяем переменную окружения для тестового запуска
        test_mode = os.getenv("TEST_MODE", "false").lower() == "true"
        
        if test_mode:
            logger.info("🧪 ТЕСТОВЫЙ РЕЖИМ: Отправляю сообщение и завершаю работу...")
            await self.send_daily_report()
            logger.info("✅ Тестовое сообщение отправлено. Завершение работы.")
            return
        
        # Отправляем приветственное сообщение только если SEND_STARTUP_MSG=true
        if SEND_STARTUP_MSG:
            await self.send_startup_message()
        else:
            logger.info("Приветственное сообщение отключено (SEND_STARTUP_MSG=false)")
        
        # Ждём расписания
        logger.info("Ожидаю расписания (13:00 Киев)...")
        
        await self.scheduled_task()


async def health_check(request):
    """Health check endpoint для Render"""
    return web.Response(text="OK")


async def start_web_server():
    """Запуск веб-сервера для health check"""
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Web сервер запущен на порту {PORT}")


async def main():
    """Главная функция"""
    # Запускаем веб-сервер для health check
    await start_web_server()
    
    # Запускаем бота
    bot = TelegramJobBot(BOT_TOKEN, CHAT_ID)
    await bot.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")