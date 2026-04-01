from __future__ import annotations

import os
import re
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

PDF_1_4 = BASE_DIR / "assets" / "pdf" / "Raspisanie_1_4_klassy.pdf"
PDF_5_9 = BASE_DIR / "assets" / "pdf" / "Raspisanie_5_9_klassy.pdf"
PDF_10_11 = BASE_DIR / "assets" / "pdf" / "Raspisanie_10_11_klassy.pdf"

BELL_SCHEDULE_IMAGE = BASE_DIR / "assets" / "images" / "raspisanie_zvonkov.png"
VACATIONS_IMAGE = BASE_DIR / "assets" / "images" / "kanikuly.png"

MENU_SCHEDULE = "Расписание уроков"
MENU_BELLS = "Расписание звонков"
MENU_VACATIONS = "Каникулы"
MENU_HOLIDAYS = "Праздничные дни"

WELCOME_TEXT = (
    "Здравствуйте!\n\n"
    "Ученик ГБУ ОО ЗО «СОШ №15 им. Графа Е.Ф. Комаровского»,\n"
    "г. Мелитополь, этот бот создан для вашего удобства.\n\n"
    "Выберите нужный раздел кнопками ниже."
)

CLASS_PROMPT = (
    "Напишите, в каком классе вы учитесь.\n\n"
    "Примеры:\n"
    "• 3 класс\n"
    "• 7\n"
    "• 10А"
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
    "1 июня — дополнительный нерабочий праздничный ден"
)

pending_class_request: set[int] = set()


def build_main_keyboard() -> types.ReplyKeyboardMarkup:
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(MENU_SCHEDULE, MENU_BELLS)
    keyboard.row(MENU_VACATIONS, MENU_HOLIDAYS)
    return keyboard


def remember_user(message: types.Message) -> None:
    save_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )


def normalize_class_input(text: str) -> str | None:
    cleaned = (text or "").strip().lower()
    cleaned = cleaned.replace("класс", "").replace(" ", "")
    match = re.search(r"(\d{1,2})([а-яa-z]?)", cleaned, re.IGNORECASE)
    if not match:
        return None

    grade = int(match.group(1))
    letter = match.group(2).upper()
    if not (1 <= grade <= 11):
        return None
    return f"{grade}{letter}"


def resolve_schedule_pdf(class_name: str) -> Path | None:
    match = re.match(r"(\d{1,2})", class_name)
    if not match:
        return None

    grade = int(match.group(1))
    if 1 <= grade <= 4:
        return PDF_1_4
    if 5 <= grade <= 9:
        return PDF_5_9
    if 10 <= grade <= 11:
        return PDF_10_11
    return None


def send_schedule_for_class(message: types.Message, class_name: str) -> None:
    pdf_path = resolve_schedule_pdf(class_name)
    if not pdf_path or not pdf_path.exists():
        bot.reply_to(
            message,
            "Не удалось найти файл с расписанием для этого класса.",
            reply_markup=build_main_keyboard(),
        )
        return

    save_class(message.from_user.id, class_name)
    with pdf_path.open("rb") as pdf_file:
        bot.send_document(
            message.chat.id,
            pdf_file,
            visible_file_name=pdf_path.name,
            caption=f"Расписание уроков для {class_name} класса.",
        )


@bot.message_handler(commands=["start", "help"])
def start_handler(message: types.Message) -> None:
    remember_user(message)
    pending_class_request.discard(message.from_user.id)
    bot.send_message(
        message.chat.id,
        WELCOME_TEXT,
        reply_markup=build_main_keyboard(),
    )


@bot.message_handler(func=lambda message: (message.text or "").strip() == MENU_SCHEDULE)
def lessons_schedule_handler(message: types.Message) -> None:
    remember_user(message)
    saved_class = get_class(message.from_user.id)
    if saved_class:
        text = (
            f"У вас сохранен {saved_class} класс.\n"
            "Если хотите получить расписание для другого класса, просто напишите новый класс.\n\n"
            f"{CLASS_PROMPT}"
        )
    else:
        text = CLASS_PROMPT

    pending_class_request.add(message.from_user.id)
    bot.send_message(message.chat.id, text, reply_markup=build_main_keyboard())


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


@bot.message_handler(func=lambda message: message.from_user.id in pending_class_request)
def class_input_handler(message: types.Message) -> None:
    remember_user(message)
    class_name = normalize_class_input(message.text or "")
    if not class_name:
        bot.reply_to(
            message,
            "Не удалось распознать класс. Напишите, например: 5 класс, 8 или 10А.",
            reply_markup=build_main_keyboard(),
        )
        return

    pending_class_request.discard(message.from_user.id)
    send_schedule_for_class(message, class_name)


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
