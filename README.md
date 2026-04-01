# School Bot

Telegram-бот для школьной информации:

- расписание уроков
- расписание звонков
- каникулы
- праздничные дни

## Запуск

1. Создайте `.env` рядом с `bot.py`
2. Добавьте:

```env
BOT_TOKEN=...
```

3. Установите зависимости:

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

4. Запустите бота:

```powershell
.\.venv\Scripts\python bot.py
```
