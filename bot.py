from __future__ import annotations

import os
from pathlib import Path

import telebot
from dotenv import load_dotenv
from telebot import types

from schedule_data import DAYS, SCHEDULES, letters_for_grade
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

MENU_SCHEDULE = "Расписание уроков"
MENU_BELLS = "Расписание звонков"
MENU_VACATIONS = "Каникулы"
MENU_HOLIDAYS = "Праздничные дни"
BACK_BUTTON = "Назад"

GRADE_BUTTONS = [str(i) for i in range(1, 12)]

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

VACATIONS_TEXT = (
    "?? ???????? 2025?2026

"
    "?? ???????: 25.10.2025 ? 04.11.2025 (11 ????)
"
    "?? ??????: 31.12.2025 ? 11.01.2026 (12 ????)
"
    "?? 1 ??????: 16.02.2026 ? 22.02.2026 (7 ????)
"
    "??? 21.02.2026 ? 01.03.2026 (9 ????)
"
    "?? ????????: 28.03.2026 ? 05.04.2026 (9 ????)
"
    "?? ??????: 27.05.2026 ? 31.08.2026 (97 ????)

"
    "?? ? 9 ? 11 ??????? ???? ?????? ?????? ??????? ????? ?????????? ??-?? ?????????."
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
    letters = letters_for_grade(grade)
    row: list[str] = []
    for letter in letters:
        row.append(letter)
        if len(row) == 3:
            keyboard.row(*row)
            row = []
    if row:
        keyboard.row(*row)
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


def format_schedule_text(class_name: str, day_label: str) -> str:
    subjects = SCHEDULES.get(class_name, {}).get(day_label, [])
    if not subjects:
        return f"Расписание для {class_name} на {day_label.lower()} пока не найдено."

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


@bot.message_handler(
    func=lambda message: (
        pending_grade.get(message.from_user.id) is not None
        and (message.text or "").strip() in letters_for_grade(pending_grade.get(message.from_user.id, ""))
    )
)
def class_choice_handler(message: types.Message) -> None:
    remember_user(message)
    grade = pending_grade.get(message.from_user.id)
    raw_text = (message.text or "").strip()
    if not grade or raw_text not in letters_for_grade(grade):
        bot.send_message(
            message.chat.id,
            "Выберите букву класса кнопками ниже.",
            reply_markup=build_letter_keyboard(grade or ""),
        )
        return
    class_name = f"{grade}{raw_text}"
    pending_grade.pop(message.from_user.id, None)
    pending_class[message.from_user.id] = class_name
    save_class(message.from_user.id, class_name)
    bot.send_message(
        message.chat.id,
        f"Вы выбрали {class_name}. Теперь выберите день недели.",
        reply_markup=build_weekday_keyboard(),
    )


@bot.message_handler(func=lambda message: (message.text or "").strip() in DAYS)
def weekday_choice_handler(message: types.Message) -> None:
    remember_user(message)
    class_name = pending_class.get(message.from_user.id) or get_class(message.from_user.id)
    if not class_name:
        bot.send_message(message.chat.id, "Сначала выберите класс.", reply_markup=build_grade_keyboard())
        return
    day_label = (message.text or "").strip()
    bot.send_message(message.chat.id, format_schedule_text(class_name, day_label), reply_markup=build_weekday_keyboard())


@bot.message_handler(func=lambda message: (message.text or "").strip() == MENU_BELLS)
def bell_schedule_handler(message: types.Message) -> None:
    remember_user(message)
    with BELL_SCHEDULE_IMAGE.open("rb") as image:
        bot.send_photo(message.chat.id, image, caption="Расписание звонков.")


@bot.message_handler(func=lambda message: (message.text or "").strip() == MENU_VACATIONS)
def vacations_handler(message: types.Message) -> None:
    remember_user(message)
    bot.send_message(message.chat.id, VACATIONS_TEXT)


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
    bot.reply_to(message, "Используйте кнопки меню ниже.", reply_markup=build_main_keyboard())


if __name__ == "__main__":
    print("School bot started.")
    bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
