from __future__ import annotations

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
CLASS_IMAGES_DIR = ASSETS_DIR / "images" / "classes"
BELL_SCHEDULE_IMAGE = ASSETS_DIR / "images" / "raspisanie_zvonkov.png"
VACATIONS_IMAGE = ASSETS_DIR / "images" / "kanikuly.png"

MENU_SCHEDULE = "Расписание уроков"
MENU_BELLS = "Расписание звонков"
MENU_VACATIONS = "Каникулы"
MENU_HOLIDAYS = "Праздничные дни"
BACK_BUTTON = "Назад"

GRADE_BUTTONS = [str(i) for i in range(1, 12)]
LETTER_BUTTONS = ["А", "Б", "В", "Г", "Д"]
LETTER_TO_FILE = {"А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D"}

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
    if grade not in GRADE_BUTTONS or letter not in LETTER_TO_FILE:
        return None
    return grade, letter


def class_image_path(grade: str, letter: str) -> Path:
    return CLASS_IMAGES_DIR / f"{grade}{LETTER_TO_FILE[letter]}.png"


def send_class_schedule(message: types.Message, grade: str, letter: str) -> None:
    class_name = f"{grade}{letter}"
    image_path = class_image_path(grade, letter)
    if not image_path.exists():
        bot.send_message(
            message.chat.id,
            f"Расписание для класса {class_name} пока не найдено.\n"
            "Попробуйте выбрать другую букву.",
            reply_markup=build_letter_keyboard(grade),
        )
        return

    save_class(message.from_user.id, class_name)
    with image_path.open("rb") as image_file:
        bot.send_photo(
            message.chat.id,
            image_file,
            caption=f"Расписание уроков для класса {class_name}.",
            reply_markup=build_main_keyboard(),
        )


@bot.message_handler(commands=["start", "help"])
def start_handler(message: types.Message) -> None:
    remember_user(message)
    pending_grade.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, WELCOME_TEXT, reply_markup=build_main_keyboard())


@bot.message_handler(func=lambda message: (message.text or "").strip() == MENU_SCHEDULE)
def lessons_schedule_handler(message: types.Message) -> None:
    remember_user(message)
    pending_grade.pop(message.from_user.id, None)
    saved_class = get_class(message.from_user.id)
    text = "Выберите номер класса."
    if saved_class:
        text = f"У вас сохранен последний выбранный класс: {saved_class}.\n\nВыберите номер класса."
    bot.send_message(message.chat.id, text, reply_markup=build_grade_keyboard())


@bot.message_handler(func=lambda message: (message.text or "").strip() in GRADE_BUTTONS)
def grade_choice_handler(message: types.Message) -> None:
    remember_user(message)
    grade = (message.text or "").strip()
    pending_grade[message.from_user.id] = grade
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
    pending_grade.pop(message.from_user.id, None)
    send_class_schedule(message, grade, letter)


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
    pending_grade.pop(message.from_user.id, None)
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
