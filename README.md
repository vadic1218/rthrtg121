# School Bot

Telegram-бот для школьной информации:

- расписание уроков
- расписание звонков
- каникулы
- праздничные дни

## Локальный запуск

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

## Railway

Для Railway нужен только один обязательный секрет:

```env
BOT_TOKEN=...
```

Деплой идет через `Dockerfile`, бот запускается в режиме long polling.
