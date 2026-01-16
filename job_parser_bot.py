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
CHAT_ID = os.getenv("CHAT_ID", "-1003407248691")
SEARCH_TIME = time(hour=7, minute=0)  # 07:00 UTC = 09:00 Киев
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
        
    async def parse_telegram_preview(self, channel):
        """
        Парсинг превью Telegram канала через t.me
        ВНИМАНИЕ: Telegram ограничивает доступ к публичному preview.
        Для полноценного парсинга нужен Telegram API или бот должен быть в канале.
        """
        results = []
        logger.warning(f"⚠️ Парсинг Telegram каналов через публичный preview ограничен")
        logger.info(f"💡 Рекомендация: Проверяйте каналы вручную - t.me/{channel}")
        
        # Оставляем код для будущего использования, но он может не работать
        try:
            url = f"https://t.me/s/{channel}"
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Ищем последние сообщения
                        messages = soup.find_all('div', class_='tgme_widget_message_text')[:50]
                        logger.info(f"Канал @{channel}: найдено {len(messages)} сообщений")
                        
                        for msg in messages:
                            try:
                                text = msg.get_text(strip=True).lower()
                                
                                # Проверяем наличие фраз "ищу работу" ИЛИ профессий
                                has_job_search = any(kw in text for kw in self.job_search_keywords)
                                has_profession = any(prof in text for prof in self.professions)
                                
                                # Дополнительная проверка: если короткое слово, проверяем контекст
                                if has_job_search and len(text) < 20:
                                    continue
                                
                                if has_job_search or has_profession:
                                    parent = msg.find_parent('div', class_='tgme_widget_message')
                                    if parent:
                                        link_elem = parent.find('a', class_='tgme_widget_message_date')
                                        if link_elem:
                                            link = link_elem.get('href', '')
                                            preview = text[:200] + '...' if len(text) > 200 else text
                                            
                                            logger.info(f"✓ Найдено совпадение в @{channel}: {preview[:50]}...")
                                            
                                            results.append({
                                                'name': preview.capitalize(),
                                                'link': link,
                                                'source': f'Telegram: @{channel}'
                                            })
                            except Exception as e:
                                logger.debug(f"Ошибка обработки сообщения: {e}")
                                
        except Exception as e:
            logger.error(f"Ошибка парсинга канала {channel}: {e}")
            
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
    
    async def get_all_candidates(self):
        """Собрать всех кандидатов из всех источников"""
        tasks = []
        
        # Добавляем парсинг Telegram каналов
        for channel in TELEGRAM_CHANNELS:
            tasks.append(self.parse_telegram_preview(channel))
        
        # Добавляем OLX (раздел резюме)
        tasks.append(self.parse_olx())
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_candidates = []
        for result in results:
            if isinstance(result, list):
                all_candidates.extend(result)
        
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
            message = f"🔍 Поиск людей, ищущих работу\n\n"
            message += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            message += "❌ Автоматический парсинг не нашел объявлений\n\n"
            message += "⚠️ ВАЖНО: Telegram и OLX ограничивают автоматический парсинг.\n"
            message += "Проверьте вручную:\n\n"
            message += "📱 Telegram каналы:\n"
            message += "• t.me/zhitomir9 - Житомир Чат\n"
            message += "• t.me/zhytomyr_olx - Працевлаштування\n\n"
            message += "🌐 Сайты:\n"
            message += "• olx.ua - поиск по \"шукаю роботу житомир\"\n"
            message += "• work.ua/resumes-zhytomyr/\n"
            message += "• robota.ua/candidates/zhitomir\n\n"
            message += "🔍 Ключевые слова для поиска:\n"
            message += "\"шукаю роботу\", \"шукаю підробіток\", \"сварщик\", \"різноробочий\""
        else:
            message = f"👥 Найдено людей, ищущих работу: {len(candidates)}\n"
            message += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            message += f"🔍 Ключевые фразы: \"шукаю роботу\", \"шукаю підробіток\", \"готовий до роботи\"\n\n"
            
            for i, candidate in enumerate(candidates, 1):
                message += f"{i}. {candidate['name']}\n"
                message += f"   🔗 {candidate['link']}\n"
                message += f"   📱 {candidate['source']}\n\n"
                
                if len(message) > 3500:
                    break
            
            message += "\n💼 Мониторим каналы:\n"
            message += "• Житомир Чат - t.me/zhitomir9\n"
            message += "• Працевлаштування - t.me/zhytomyr_olx"
        
        try:
            bot = Bot(token=self.token)
            await bot.send_message(chat_id=self.chat_id, text=message, disable_web_page_preview=True)
            logger.info("Сообщение успешно отправлено")
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
    
    async def run(self):
        """Запустить бота"""
        logger.info("Бот запущен!")
        logger.info(f"Время отправки: {SEARCH_TIME}")
        logger.info(f"Мониторинг каналов: {', '.join(['@' + ch for ch in TELEGRAM_CHANNELS])}")
        
        # Проверяем переменную окружения для тестового запуска
        test_mode = os.getenv("TEST_MODE", "false").lower() == "true"
        
        if test_mode:
            logger.info("🧪 ТЕСТОВЫЙ РЕЖИМ: Отправляю сообщение и завершаю работу...")
            await self.send_daily_report()
            logger.info("✅ Тестовое сообщение отправлено. Завершение работы.")
            return
        
        # Первая отправка сразу при запуске
        logger.info("Отправляю первое сообщение...")
        await self.send_daily_report()
        
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