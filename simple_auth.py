from telethon.sync import TelegramClient

API_ID = 34113723
API_HASH = "e110b2fa49ddcf1fbe30740264ad14a9"

print("="*60)
print("АВТОРИЗАЦИЯ TELETHON")
print("="*60)
print("\nИНСТРУКЦИЯ:")
print("1. Введи номер: +380969061900")
print("2. Код придёт в Telegram (проверь Saved Messages)")
print("3. Если код не пришёл - попроси отправить через SMS")
print("4. Введи код из Telegram или SMS")
print("5. Если есть 2FA пароль - введи его")
print("\n" + "="*60 + "\n")

try:
    client = TelegramClient('worker_session', API_ID, API_HASH)
    
    # Запуск с возможностью выбора SMS
    client.start(
        phone=lambda: input('Телефон (или Enter для +380969061900): ') or '+380969061900',
        code_callback=lambda: input('Код из Telegram/SMS: '),
        password=lambda: input('2FA пароль (если есть): ') if input('Есть 2FA? (y/n): ').lower() == 'y' else None
    )
    
    me = client.get_me()
    print("\n" + "="*60)
    print("✅ АВТОРИЗАЦИЯ УСПЕШНА!")
    print("="*60)
    print(f"Аккаунт: {me.first_name}")
    if me.username:
        print(f"Username: @{me.username}")
    print(f"Телефон: {me.phone}")
    print(f"\nФайл сессии: worker_session.session")
    print("\nТеперь запусти парсер:")
    print("  python telethon_parser.py")
    print("="*60)
    
    client.disconnect()
    
except KeyboardInterrupt:
    print("\n\n❌ Отменено пользователем")
except Exception as e:
    print(f"\n\n❌ Ошибка: {e}")
    print("\nПопробуй ещё раз или проверь:")
    print("- Правильность номера телефона")
    print("- Интернет соединение")
    print("- Код не истёк (действует 5 минут)")
