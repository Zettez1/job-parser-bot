"""
Скрипт для тестирования бота локально
Запускает парсинг и отправляет результаты один раз
"""
import asyncio
import os
from job_parser_bot import TelegramJobBot, BOT_TOKEN, CHAT_ID

async def test():
    print("🧪 Запуск тестового парсинга...")
    bot = TelegramJobBot(BOT_TOKEN, CHAT_ID)
    await bot.send_daily_report()
    print("✅ Готово!")

if __name__ == "__main__":
    asyncio.run(test())
