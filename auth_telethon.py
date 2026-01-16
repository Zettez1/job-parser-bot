"""
Авторизация Telethon - запусти один раз
После авторизации создастся файл session, и парсер будет работать автоматически
"""
from telethon.sync import TelegramClient

API_ID = 34113723
API_HASH = "e110b2fa49ddcf1fbe30740264ad14a9"
PHONE = "+380969061900"

print("="*50)
print("АВТОРИЗАЦИЯ TELETHON")
print("="*50)
print(f"\nТелефон: {PHONE}")
print("Запрашиваем код...\n")

# Синхронный клиент
with TelegramClient('worker_session', API_ID, API_HASH) as client:
    client.start(phone=PHONE)
    
    me = client.get_me()
    print(f"\n✅ Авторизация успешна!")
    print(f"Аккаунт: {me.first_name}")
    if me.username:
        print(f"Username: @{me.username}")
    print(f"\nФайл сессии создан: worker_session.session")
    print("Теперь парсер будет работать автоматически!")
