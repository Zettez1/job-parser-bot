# Job Parser Bot

Telegram бот для поиска людей, которые ищут работу в Житомире.

## Источники парсинга
- Telegram каналы: @zhitomir9, @zhytomyr_olx

## Что ищет бот
Сообщения с фразами:
- "шукаю роботу", "шукаю підробіток"
- "ищу работу", "ищу подработку"
- "готовий до роботи", "готов к работе"
- "потрібна робота", "нужна работа"

## Деплой на Render

### 1. Загрузите на GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <ваш-репозиторий>
git push -u origin main
```

### 2. Создайте сервис на Render
1. Зайдите на [render.com](https://render.com)
2. Нажмите **New** → **Background Worker**
3. Подключите ваш GitHub репозиторий
4. Настройки:
   - **Name**: job-parser-bot
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python job_parser_bot.py`

### 3. Добавьте переменные окружения (Environment Variables)
В настройках сервиса добавьте:
- `BOT_TOKEN` = ваш токен бота
- `CHAT_ID` = ID вашего чата/канала

### 4. Деплой
Нажмите **Create Background Worker** — бот запустится автоматически.

## Расписание
Бот отправляет отчет каждый день в 07:00 UTC (09:00 по Киеву).

## Локальный запуск
```bash
pip install -r requirements.txt
python job_parser_bot.py
```
