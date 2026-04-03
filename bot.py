from __future__ import annotations

import os
from pathlib import Path

import telebot
from dotenv import load_dotenv
from telebot import types

from schedule_data import DAYS, SCHEDULES, letters_for_grade
from storage import init_db, save_class, save_user


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

BOT_TOKEN = os.getenv('BOT_TOKEN', '').strip()
if not BOT_TOKEN:
    raise RuntimeError('BOT_TOKEN is not set')

bot = telebot.TeleBot(BOT_TOKEN)
init_db()

MENU_SCHEDULE = 'Расписание уроков'
MENU_BELLS = 'Расписание звонков'
MENU_VACATIONS = 'Каникулы'
MENU_HOLIDAYS = 'Праздничные дни'
BACK_BUTTON = 'Назад'

GRADE_BUTTONS = [str(i) for i in range(1, 12)]
LESSON_SLOTS = [
    ('8:00', '8:40', '10 минут'),
    ('8:50', '9:30', '10 минут'),
    ('9:40', '10:20', '20 минут'),
    ('10:40', '11:20', '10 минут'),
    ('11:30', '12:10', '10 минут'),
    ('12:20', '13:00', '10 минут'),
    ('13:10', '13:50', '20 минут'),
    ('14:10', '14:50', '10 минут'),
    ('15:00', '15:40', '10 минут'),
    ('15:50', '16:30', '20 минут'),
    ('16:50', '17:30', '10 минут'),
    ('17:40', '18:20', '10 минут'),
    ('18:30', '19:10', None),
]

WELCOME_TEXT = (
    'Здравствуйте!\n\n'
    'Ученик ГБУ ОО ЗО «СОШ №15 им. Графа Е.Ф. Комаровского»,\n'
    'г. Мелитополь, этот бот создан для вашего удобства.\n\n'
    'Выберите нужный раздел с помощью кнопок ниже.'
)

BELL_SCHEDULE_TEXT = (
    '📚 Расписание звонков\n\n'
    '1) 8:00 — 8:40\nПеремена: 10 минут\n\n'
    '2) 8:50 — 9:30\nПеремена: 10 минут\n\n'
    '3) 9:40 — 10:20\nПеремена: 20 минут\n\n'
    '4) 10:40 — 11:20\nПеремена: 10 минут\n\n'
    '5) 11:30 — 12:10\nПеремена: 10 минут\n\n'
    '6) 12:20 — 13:00\nПеремена: 10 минут\n\n'
    '7) 13:10 — 13:50\nПеремена: 20 минут\n\n'
    '8) 14:10 — 14:50\nПеремена: 10 минут\n\n'
    '9) 15:00 — 15:40\nПеремена: 10 минут\n\n'
    '10) 15:50 — 16:30\nПеремена: 20 минут\n\n'
    '11) 16:50 — 17:30\nПеремена: 10 минут\n\n'
    '12) 17:40 — 18:20\nПеремена: 10 минут\n\n'
    '13) 18:30 — 19:10'
)

VACATIONS_TEXT = (
    '📚 Каникулы 2025–2026\n\n'
    '🍂 Осенние: 25.10.2025 — 04.11.2025 (11 дней)\n'
    '❄️ Зимние: 31.12.2025 — 11.01.2026 (12 дней)\n'
    '👦 1 классы: 16.02.2026 — 22.02.2026 (7 дней)\n'
    'или 21.02.2026 — 01.03.2026 (9 дней)\n'
    '🌸 Весенние: 28.03.2026 — 05.04.2026 (9 дней)\n'
    '☀️ Летние: 27.05.2026 — 31.08.2026 (97 дней)\n\n'
    'ℹ️ У 9 и 11 классов дата начала летних каникул может отличаться из-за экзаменов.'
)

HOLIDAYS_TEXT = (
    '🎉 Праздничные дни\n\n'
    '🎄 1–8 января — новогодние праздники\n'
    '🛡 23 февраля — День защитника Отечества\n'
    '🌷 8 марта — Международный женский день\n'
    '🌿 1 мая — Праздник Весны и Труда\n'
    '⭐ 9 мая — День Победы\n'
    '🇷🇺 12 июня — День России\n'
    '🤝 4 ноября — День народного единства\n'
    '📅 13 апреля — дополнительный нерабочий праздничный день\n'
    '☀️ 1 июня — дополнительный нерабочий праздничный день'
)

user_state: dict[int, dict[str, str | int]] = {}


def build_main_keyboard() -> types.ReplyKeyboardMarkup:
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        types.KeyboardButton(MENU_SCHEDULE),
        types.KeyboardButton(MENU_BELLS),
        types.KeyboardButton(MENU_VACATIONS),
        types.KeyboardButton(MENU_HOLIDAYS),
    )
    return keyboard


def build_grade_keyboard() -> types.ReplyKeyboardMarkup:
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    keyboard.add(*[types.KeyboardButton(text) for text in GRADE_BUTTONS])
    keyboard.add(types.KeyboardButton(BACK_BUTTON))
    return keyboard


def build_letter_keyboard(grade: int) -> types.ReplyKeyboardMarkup:
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    letters = letters_for_grade(grade)
    keyboard.add(*[types.KeyboardButton(letter) for letter in letters])
    keyboard.add(types.KeyboardButton(BACK_BUTTON))
    return keyboard


def build_weekday_keyboard() -> types.ReplyKeyboardMarkup:
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(*[types.KeyboardButton(day) for day in DAYS])
    keyboard.add(types.KeyboardButton(BACK_BUTTON))
    return keyboard


def set_state(user_id: int, **kwargs: str | int) -> None:
    state = user_state.setdefault(user_id, {})
    state.update(kwargs)


def clear_state(user_id: int) -> None:
    user_state.pop(user_id, None)


def format_schedule_text(class_name: str, day: str, lessons: list[str]) -> str:
    lines = [f'📚 Расписание для {class_name} на {day}', '']
    for index, lesson in enumerate(lessons):
        if index >= len(LESSON_SLOTS):
            lines.append(f'{index + 1}) {lesson}')
            lines.append('')
            continue
        start, end, break_time = LESSON_SLOTS[index]
        lines.append(f'{index + 1}) {lesson}')
        lines.append(f'⏰ {start} — {end}')
        if break_time:
            lines.append(f'Перемена: {break_time}')
        lines.append('')
    return '\n'.join(lines).strip()


def send_main_menu(chat_id: int, text: str = WELCOME_TEXT) -> None:
    bot.send_message(chat_id, text, reply_markup=build_main_keyboard())


@bot.message_handler(commands=['start', 'help'])
def handle_start(message: types.Message) -> None:
    save_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    clear_state(message.from_user.id)
    send_main_menu(message.chat.id)


@bot.message_handler(func=lambda m: m.text == MENU_SCHEDULE)
def handle_schedule(message: types.Message) -> None:
    save_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    set_state(message.from_user.id, step='grade')
    bot.send_message(message.chat.id, 'Выберите номер класса.', reply_markup=build_grade_keyboard())


@bot.message_handler(func=lambda m: m.text == MENU_BELLS)
def handle_bells(message: types.Message) -> None:
    bot.send_message(message.chat.id, BELL_SCHEDULE_TEXT, reply_markup=build_main_keyboard())


@bot.message_handler(func=lambda m: m.text == MENU_VACATIONS)
def handle_vacations(message: types.Message) -> None:
    bot.send_message(message.chat.id, VACATIONS_TEXT, reply_markup=build_main_keyboard())


@bot.message_handler(func=lambda m: m.text == MENU_HOLIDAYS)
def handle_holidays(message: types.Message) -> None:
    bot.send_message(message.chat.id, HOLIDAYS_TEXT, reply_markup=build_main_keyboard())


@bot.message_handler(func=lambda m: m.text == BACK_BUTTON)
def handle_back(message: types.Message) -> None:
    state = user_state.get(message.from_user.id, {})
    step = state.get('step')
    if step == 'letter':
        set_state(message.from_user.id, step='grade')
        bot.send_message(message.chat.id, 'Выберите номер класса.', reply_markup=build_grade_keyboard())
        return
    if step == 'day':
        grade = state.get('grade')
        if isinstance(grade, int):
            set_state(message.from_user.id, step='letter')
            bot.send_message(message.chat.id, f'Теперь выберите букву для {grade} класса.', reply_markup=build_letter_keyboard(grade))
            return
    clear_state(message.from_user.id)
    send_main_menu(message.chat.id)


@bot.message_handler(func=lambda m: m.text in GRADE_BUTTONS)
def handle_grade(message: types.Message) -> None:
    state = user_state.get(message.from_user.id, {})
    if state.get('step') != 'grade':
        return
    grade = int(message.text)
    letters = letters_for_grade(grade)
    if not letters:
        bot.send_message(message.chat.id, f'Для {grade} класса расписание пока не добавлено.', reply_markup=build_grade_keyboard())
        return
    set_state(message.from_user.id, step='letter', grade=grade)
    bot.send_message(message.chat.id, f'Теперь выберите букву для {grade} класса.', reply_markup=build_letter_keyboard(grade))


@bot.message_handler(func=lambda m: len((m.text or '').strip()) == 1 and (m.text or '').strip().upper() in {'А', 'Б', 'В', 'Г', 'Д', 'К', 'Е'})
def handle_letter(message: types.Message) -> None:
    state = user_state.get(message.from_user.id, {})
    if state.get('step') != 'letter':
        return
    grade = state.get('grade')
    if not isinstance(grade, int):
        bot.send_message(message.chat.id, 'Сначала выберите номер класса.', reply_markup=build_grade_keyboard())
        return
    letter = message.text.strip().upper()
    class_name = f'{grade}{letter}'
    if class_name not in SCHEDULES:
        bot.send_message(message.chat.id, f'Расписание для класса {class_name} пока не найдено. Выберите другую букву.', reply_markup=build_letter_keyboard(grade))
        return
    save_class(message.from_user.id, class_name)
    set_state(message.from_user.id, step='day', class_name=class_name)
    bot.send_message(message.chat.id, f'Вы выбрали {class_name}. Теперь выберите день недели.', reply_markup=build_weekday_keyboard())


@bot.message_handler(func=lambda m: m.text in DAYS)
def handle_day(message: types.Message) -> None:
    state = user_state.get(message.from_user.id, {})
    if state.get('step') != 'day':
        return
    class_name = state.get('class_name')
    if not isinstance(class_name, str):
        bot.send_message(message.chat.id, 'Сначала выберите класс.', reply_markup=build_main_keyboard())
        return
    day = message.text
    lessons = SCHEDULES.get(class_name, {}).get(day)
    if not lessons:
        bot.send_message(message.chat.id, f'Расписание для {class_name} на {day.lower()} пока не найдено.\nПопробуйте выбрать другой день.', reply_markup=build_weekday_keyboard())
        return
    bot.send_message(message.chat.id, format_schedule_text(class_name, day, lessons), reply_markup=build_weekday_keyboard())


@bot.message_handler(func=lambda m: True, content_types=['text'])
def fallback(message: types.Message) -> None:
    send_main_menu(message.chat.id)


if __name__ == '__main__':
    bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=20)
