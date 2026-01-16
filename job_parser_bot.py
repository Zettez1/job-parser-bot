import asyncio
import logging
import os
from datetime import datetime, time
import aiohttp
from bs4 import BeautifulSoup
from telegram import Bot
import re

# ============= НАСТРОЙКИ =============
# Переменные окружения для безопасности (настройте на Render)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8302303298:AAGH3Nllv4JaQRoi8Em8rO1-L_zGinN-gVM")
CHAT_ID = os.getenv("CHAT_ID", "-1003407248691")
SEARCH_TIME = time(hour=7, minute=0)  # 07:00 UTC = 09:00 Киев

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
    """Парсер для поиска работников"""
    
    def __init__(self):
        self.city = "житомир"
        # Ключевые слова для поиска
        self.keywords = [
            "сварщик", "зварник", "сварювальник",
            "робота", "работа", "робочі", "рабочие",
            "шукаю роботу", "ищу работу",
            "чоловік", "мужчина", "парень", "хлопець"
        ]
        
    async def parse_telegram_preview(self, channel):
        """Парсинг превью Telegram канала через t.me"""
        results = []
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
                        messages = soup.find_all('div', class_='tgme_widget_message_text')[:20]
                        
                        for msg in messages:
                            try:
                                text = msg.get_text(strip=True).lower()
                                
                                # Проверяем наличие города и ключевых слов
                                if self.city in text:
                                    if any(kw in text for kw in self.keywords):
                                        # Получаем ссылку на сообщение
                                        parent = msg.find_parent('div', class_='tgme_widget_message')
                                        if parent:
                                            link_elem = parent.find('a', class_='tgme_widget_message_date')
                                            if link_elem:
                                                link = link_elem.get('href', '')
                                                
                                                # Обрезаем текст для превью
                                                preview = text[:150] + '...' if len(text) > 150 else text
                                                
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
        """Парсинг OLX - раздел работы"""
        results = []
        try:
            url = "https://www.olx.ua/d/uk/robota/zhitomir/"
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Ищем объявления
                        ads = soup.find_all('div', {'data-cy': 'l-card'})[:15]
                        
                        for ad in ads:
                            try:
                                title_elem = ad.find('h6')
                                link_elem = ad.find('a')
                                
                                if title_elem and link_elem:
                                    title = title_elem.get_text(strip=True)
                                    link = link_elem.get('href', '')
                                    
                                    if not link.startswith('http'):
                                        link = 'https://www.olx.ua' + link
                                    
                                    # Проверяем ключевые слова
                                    text_lower = title.lower()
                                    if any(kw in text_lower for kw in self.keywords):
                                        results.append({
                                            'name': title,
                                            'link': link,
                                            'source': 'OLX'
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
        
        # Добавляем другие источники
        tasks.extend([
            self.parse_olx(),
            self.parse_rabotaua_lite(),
            self.parse_workua_lite(),
        ])
        
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
            message = f"🔍 Поиск работников в Житомире\n\n"
            message += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            message += "❌ Новых объявлений не найдено\n\n"
            message += "💡 Рекомендую проверить вручную:\n"
            message += "• t.me/zhitomir9\n"
            message += "• t.me/zhytomyr_olx\n"
            message += "• OLX - olx.ua/d/uk/robota/zhitomir/\n"
            message += "• Work.ua - work.ua/jobs-zhytomyr/"
        else:
            message = f"🔍 Найдено объявлений: {len(candidates)}\n"
            message += f"📍 Город: Житомир\n"
            message += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            message += f"👥 Ищем: сварщики, рабочие, мужчины 17-50 лет\n\n"
            
            for i, candidate in enumerate(candidates, 1):
                message += f"{i}. {candidate['name']}\n"
                message += f"   🔗 {candidate['link']}\n"
                message += f"   📱 {candidate['source']}\n\n"
                
                if len(message) > 3500:
                    break
            
            message += "\n💼 Полезные каналы и сайты:\n"
            message += "• Житомир Чат - t.me/zhitomir9\n"
            message += "• Працевлаштування - t.me/zhytomyr_olx\n"
            message += "• OLX - olx.ua/d/uk/robota/zhitomir/\n"
            message += "• Work.ua - work.ua/jobs-zhytomyr/"
        
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
        
        # Первая отправка сразу для теста
        logger.info("Отправляю тестовое сообщение...")
        await self.send_daily_report()
        
        await self.scheduled_task()


async def main():
    """Главная функция"""
    bot = TelegramJobBot(BOT_TOKEN, CHAT_ID)
    await bot.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")