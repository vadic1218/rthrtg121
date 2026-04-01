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
CLASS_GROUP_1_4 = "1–4 классы"
CLASS_GROUP_5_9 = "5–9 классы"
CLASS_GROUP_10_11 = "10–11 классы"
CLASS_GROUP_BACK = "Назад"

WELCOME_TEXT = (
    "Здравствуйте!\n\n"
    "Ученик ГБУ ОО ЗО «СОШ №15 им. Графа Е.Ф. Комаровского»,\n"
    "г. Мелитополь, этот бот создан для вашего удобства.\n\n"
    "Выберите нужный раздел кнопками ниже."
)

CLASS_PROMPT = (
    "Выберите, к какой группе относится ваш класс."
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

def build_main_keyboard() -> types.ReplyKeyboardMarkup:
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(MENU_SCHEDULE, MENU_BELLS)
    keyboard.row(MENU_VACATIONS, MENU_HOLIDAYS)
    return keyboard


def build_schedule_keyboard() -> types.ReplyKeyboardMarkup:
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(CLASS_GROUP_1_4, CLASS_GROUP_5_9)
    keyboard.row(CLASS_GROUP_10_11)
    keyboard.row(CLASS_GROUP_BACK)
    return keyboard


def remember_user(message: types.Message) -> None:
    save_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )


def send_schedule_for_group(message: types.Message, group_name: str, pdf_path: Path) -> None:
    if not pdf_path.exists():
        bot.reply_to(
            message,
            "Не удалось найти файл с расписанием.",
            reply_markup=build_main_keyboard(),
        )
        return

    save_class(message.from_user.id, group_name)
    with pdf_path.open("rb") as pdf_file:
        bot.send_document(
            message.chat.id,
            pdf_file,
            visible_file_name=pdf_path.name,
            caption=f"Расписание уроков для группы {group_name}.",
        )


@bot.message_handler(commands=["start", "help"])
def start_handler(message: types.Message) -> None:
    remember_user(message)
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
            f"У вас сохранена группа {saved_class}.\n"
            "Если хотите открыть другое расписание, выберите другую группу.\n\n"
            f"{CLASS_PROMPT}"
        )
    else:
        text = CLASS_PROMPT

    bot.send_message(message.chat.id, text, reply_markup=build_schedule_keyboard())


@bot.message_handler(func=lambda message: (message.text or "").strip() == CLASS_GROUP_1_4)
def schedule_group_1_4_handler(message: types.Message) -> None:
    remember_user(message)
    send_schedule_for_group(message, CLASS_GROUP_1_4, PDF_1_4)


@bot.message_handler(func=lambda message: (message.text or "").strip() == CLASS_GROUP_5_9)
def schedule_group_5_9_handler(message: types.Message) -> None:
    remember_user(message)
    send_schedule_for_group(message, CLASS_GROUP_5_9, PDF_5_9)


@bot.message_handler(func=lambda message: (message.text or "").strip() == CLASS_GROUP_10_11)
def schedule_group_10_11_handler(message: types.Message) -> None:
    remember_user(message)
    send_schedule_for_group(message, CLASS_GROUP_10_11, PDF_10_11)


@bot.message_handler(func=lambda message: (message.text or "").strip() == CLASS_GROUP_BACK)
def schedule_back_handler(message: types.Message) -> None:
    remember_user(message)
    bot.send_message(
        message.chat.id,
        "Главное меню.",
        reply_markup=build_main_keyboard(),
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
