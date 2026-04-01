from __future__ import annotations

import json
import os
from pathlib import Path

import telebot
from dotenv import load_dotenv
from telebot import types

from storage import get_class, init_db, save_class, save_user


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

bot = telebot.TeleBot(BOT_TOKEN)
init_db()

ASSETS_DIR = BASE_DIR / "assets"
BELL_SCHEDULE_IMAGE = ASSETS_DIR / "images" / "raspisanie_zvonkov.png"
VACATIONS_IMAGE = ASSETS_DIR / "images" / "kanikuly.png"
SCHEDULES_PATH = ASSETS_DIR / "schedules.json"

SCHEDULES = json.loads(SCHEDULES_PATH.read_text(encoding="utf-8")) if SCHEDULES_PATH.exists() else {}

MENU_SCHEDULE = "Расписание уроков"
MENU_BELLS = "Расписание звонков"
MENU_VACATIONS = "Каникулы"
MENU_HOLIDAYS = "Праздничные дни"
BACK_BUTTON = "Назад"

GRADE_BUTTONS = [str(i) for i in range(1, 12)]
LETTER_BUTTONS = ["А", "Б", "В", "Г", "Д"]
WEEKDAY_BUTTONS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]

DAY_KEY_MAP = {
    "Понедельник": "monday",
    "Вторник": "tuesday",
    "Среда": "wednesday",
    "Четверг": "thursday",
    "Пятница": "friday",
}

SUBJECT_NAMES = {
    "algebra": "Алгебра",
    "art": "ИЗО",
    "biology": "Биология",
    "chemistry": "Химия",
    "choreo": "Хореография",
    "english": "Английский язык",
    "geography": "География",
    "geometry": "Геометрия",
    "history": "История",
    "horizons": "Россия — мои горизонты",
    "informatics": "Информатика",
    "labor": "Труд (технология)",
    "lit_reading": "Литературное чтение",
    "literature": "Литература",
    "math": "Математика",
    "music": "Музыка",
    "obzr": "ОБЗР",
    "pe": "Физкультура",
    "pe_full": "Физическая культура",
    "physics": "Физика",
    "probability": "Вероятность и статистика",
    "project": "Индивидуальный проект",
    "reading": "Чтение",
    "russian": "Русский язык",
    "social": "Обществознание",
    "talks": "Разговоры о важном",
    "vis": "ВИС",
    "world": "Окружающий мир",
    "writing": "Письмо",
}

LESSON_SLOTS = [
    ("8:00", "8:40", "10 минут"),
    ("8:50", "9:30", "10 минут"),
    ("9:40", "10:20", "20 минут"),
    ("10:40", "11:20", "10 минут"),
    ("11:30", "12:10", "10 минут"),
    ("12:20", "13:00", "10 минут"),
    ("13:10", "13:50", "20 минут"),
    ("14:10", "14:50", "10 минут"),
    ("15:00", "15:40", "10 минут"),
    ("15:50", "16:30", "20 минут"),
    ("16:50", "17:30", "10 минут"),
    ("17:40", "18:20", "10 минут"),
    ("18:30", "19:10", None),
]

WELCOME_TEXT = (
    "Здравствуйте!\n\n"
    "Ученик ГБУ ОО ЗО «СОШ №15 им. Графа Е.Ф. Комаровского»,\n"
    "г. Мелитополь, этот бот создан для вашего удобства.\n\n"
    "Выберите нужный раздел кнопками ниже."
)

HOLIDAYS_TEXT = (
    "1–8 января — новогодние праздники\n"
    "23 февраля — День защитника Отечества\n"
    "8 марта — Международный женский день\n"
    "1 мая — Праздник Весны и Труда\n"
    "9 мая — День Победы\n"
    "12 июня — День России\n"
    "4 ноября — День народного единства\n"
    "13 апреля — дополнительный нерабочий праздничный день\n"
    "1 июня — дополнительный нерабочий праздничный день"
)

pending_grade: dict[int, str] = {}
pending_class: dict[int, str] = {}


def build_main_keyboard() -> types.ReplyKeyboardMarkup:
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(MENU_SCHEDULE, MENU_BELLS)
    keyboard.row(MENU_VACATIONS, MENU_HOLIDAYS)
    return keyboard


def build_grade_keyboard() -> types.ReplyKeyboardMarkup:
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("1", "2", "3", "4")
    keyboard.row("5", "6", "7", "8")
    keyboard.row("9", "10", "11")
    keyboard.row(BACK_BUTTON)
    return keyboard


def build_letter_keyboard(grade: str) -> types.ReplyKeyboardMarkup:
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(f"{grade}А", f"{grade}Б", f"{grade}В")
    keyboard.row(f"{grade}Г", f"{grade}Д")
    keyboard.row(BACK_BUTTON)
    return keyboard


def build_weekday_keyboard() -> types.ReplyKeyboardMarkup:
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("Понедельник", "Вторник")
    keyboard.row("Среда", "Четверг")
    keyboard.row("Пятница")
    keyboard.row(BACK_BUTTON)
    return keyboard


def remember_user(message: types.Message) -> None:
    save_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )


def parse_class_choice(text: str) -> tuple[str, str] | None:
    raw = (text or "").strip().upper().replace(" ", "")
    if len(raw) < 2:
        return None
    grade = raw[:-1]
    letter = raw[-1]
    if grade not in GRADE_BUTTONS or letter not in LETTER_BUTTONS:
        return None
    return grade, letter


def clean_subjects(subjects: list[str], grade: str) -> list[str]:
    max_lessons = 6 if int(grade) <= 4 else 8
    cleaned: list[str] = []
    seen_pairs: set[tuple[int, str]] = set()
    last_subject = ""
    for subject_key in subjects:
        subject = SUBJECT_NAMES.get(subject_key, subject_key)
        pair = (len(cleaned), subject)
        if subject == last_subject or pair in seen_pairs:
            continue
        cleaned.append(subject)
        seen_pairs.add(pair)
        last_subject = subject
        if len(cleaned) >= max_lessons:
            break
    return cleaned


def format_schedule_text(class_name: str, day_label: str) -> str:
    day_key = DAY_KEY_MAP[day_label]
    class_schedule = SCHEDULES.get(class_name, {})
    subjects = clean_subjects(class_schedule.get(day_key, []), class_name[:-1])
    if not subjects:
        return (
            f"Расписание для {class_name} на {day_label.lower()} пока не найдено.\n"
            "Попробуйте выбрать другой день."
        )

    lines = [f"Расписание для {class_name} на {day_label}:", ""]
    for index, subject in enumerate(subjects, start=1):
        start, end, break_time = LESSON_SLOTS[index - 1]
        lines.append(f"{index}. {subject}")
        lines.append(f"   {start}–{end}")
        if break_time:
            lines.append(f"   Перемена {break_time}")
        lines.append("")
    return "\n".join(lines).strip()


@bot.message_handler(commands=["start", "help"])
def start_handler(message: types.Message) -> None:
    remember_user(message)
    pending_grade.pop(message.from_user.id, None)
    pending_class.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, WELCOME_TEXT, reply_markup=build_main_keyboard())


@bot.message_handler(func=lambda message: (message.text or "").strip() == MENU_SCHEDULE)
def lessons_schedule_handler(message: types.Message) -> None:
    remember_user(message)
    pending_grade.pop(message.from_user.id, None)
    pending_class.pop(message.from_user.id, None)
    saved_class = get_class(message.from_user.id)
    text = "Выберите номер класса."
    if saved_class:
        text = f"Последний выбранный класс: {saved_class}.\n\nВыберите номер класса."
    bot.send_message(message.chat.id, text, reply_markup=build_grade_keyboard())


@bot.message_handler(func=lambda message: (message.text or "").strip() in GRADE_BUTTONS)
def grade_choice_handler(message: types.Message) -> None:
    remember_user(message)
    grade = (message.text or "").strip()
    pending_grade[message.from_user.id] = grade
    pending_class.pop(message.from_user.id, None)
    bot.send_message(
        message.chat.id,
        f"Теперь выберите букву для {grade} класса.",
        reply_markup=build_letter_keyboard(grade),
    )


@bot.message_handler(func=lambda message: parse_class_choice(message.text or "") is not None)
def class_choice_handler(message: types.Message) -> None:
    remember_user(message)
    parsed = parse_class_choice(message.text or "")
    if parsed is None:
        return
    grade, letter = parsed
    class_name = f"{grade}{letter}"
    pending_grade.pop(message.from_user.id, None)
    pending_class[message.from_user.id] = class_name
    save_class(message.from_user.id, class_name)
    bot.send_message(
        message.chat.id,
        f"Вы выбрали {class_name}. Теперь выберите день недели.",
        reply_markup=build_weekday_keyboard(),
    )


@bot.message_handler(func=lambda message: (message.text or "").strip() in WEEKDAY_BUTTONS)
def weekday_choice_handler(message: types.Message) -> None:
    remember_user(message)
    class_name = pending_class.get(message.from_user.id) or get_class(message.from_user.id)
    if not class_name:
        bot.send_message(
            message.chat.id,
            "Сначала выберите класс.",
            reply_markup=build_grade_keyboard(),
        )
        return
    day_label = (message.text or "").strip()
    bot.send_message(
        message.chat.id,
        format_schedule_text(class_name, day_label),
        reply_markup=build_weekday_keyboard(),
    )


@bot.message_handler(func=lambda message: (message.text or "").strip() == MENU_BELLS)
def bell_schedule_handler(message: types.Message) -> None:
    remember_user(message)
    with BELL_SCHEDULE_IMAGE.open("rb") as image:
        bot.send_photo(message.chat.id, image, caption="Расписание звонков.")


@bot.message_handler(func=lambda message: (message.text or "").strip() == MENU_VACATIONS)
def vacations_handler(message: types.Message) -> None:
    remember_user(message)
    with VACATIONS_IMAGE.open("rb") as image:
        bot.send_photo(message.chat.id, image, caption="Каникулы.")


@bot.message_handler(func=lambda message: (message.text or "").strip() == MENU_HOLIDAYS)
def holidays_handler(message: types.Message) -> None:
    remember_user(message)
    bot.send_message(message.chat.id, HOLIDAYS_TEXT)


@bot.message_handler(func=lambda message: (message.text or "").strip() == BACK_BUTTON)
def back_handler(message: types.Message) -> None:
    remember_user(message)
    if message.from_user.id in pending_class:
        class_name = pending_class.pop(message.from_user.id)
        grade = class_name[:-1]
        pending_grade[message.from_user.id] = grade
        bot.send_message(message.chat.id, "Выберите букву класса.", reply_markup=build_letter_keyboard(grade))
        return
    if message.from_user.id in pending_grade:
        pending_grade.pop(message.from_user.id, None)
        bot.send_message(message.chat.id, "Выберите номер класса.", reply_markup=build_grade_keyboard())
        return
    bot.send_message(message.chat.id, "Главное меню.", reply_markup=build_main_keyboard())


@bot.message_handler(func=lambda message: True)
def fallback_handler(message: types.Message) -> None:
    remember_user(message)
    bot.reply_to(
        message,
        "Используйте кнопки меню ниже.",
        reply_markup=build_main_keyboard(),
    )


if __name__ == "__main__":
    print("School bot started.")
    bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
