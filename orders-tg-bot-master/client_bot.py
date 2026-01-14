# client_bot.py — продвинутый бот для пользователей (клиентов)

import telebot
from telebot import types
import config
import random

bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode="HTML")

client_ids = config.CLIENT_CHAT_ID[:]


# === Главное меню клиента ===
def send_main_menu(message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("❓ Частые вопросы и ответы", "🆘 Получить помощь")
    kb.add("💬 Оставить отзыв", "📁 Другое")
    kb.add("📞 Получить консультацию", "💼 Трудоустройство")
    bot.send_message(message.chat.id, "📋 Добро пожаловать! Выберите нужный раздел:", reply_markup=kb)

# === Приветствие при /start ===
@bot.message_handler(commands=['start'])
def handle_start(message):
    greetings = [
        "Приветствуем вас в справочном боте!",
        "Здравствуйте! Я помогу вам найти нужную информацию.",
        "Рады вас видеть. Чем могу помочь?",
    ]
    bot.send_message(message.chat.id, random.choice(greetings))
    send_main_menu(message.chat.id)

# === Обработка кнопок меню ===
@bot.message_handler(func=lambda m: True)
def handle_user_input(message):
    text = message.text.strip().lower()

    if text == "❓ частые вопросы и ответы":
        show_faq(message.chat.id)
    elif text == "🆘 получить помощь":
        start_help_request(message.chat.id)
    elif text == "💬 оставить отзыв":
        request_feedback(message.chat.id)
    elif text == "📁 другое":
        show_other_options(message.chat.id)
    elif text == "📞 получить консультацию":
        request_consultation(message.chat.id)
    elif text == "💼 трудоустройство":
        show_employment(message.chat.id)
    elif text == "назад":
        send_main_menu(message.chat.id)
    elif text == "подключиться к оператору":
        bot.send_message(message.chat.id, "🔄 Ваш запрос передан оператору. Ожидайте связи.")
    elif text == "запросить помощь":
        send_main_menu(message.chat.id)
    else:
        handle_unexpected(message)

# === Подменю ===
def show_faq(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Как сменить данные?", "Как отправить заявку?", "Назад")
    bot.send_message(chat_id, "📚 Часто задаваемые вопросы:", reply_markup=kb)

def start_help_request(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Назад")
    bot.send_message(chat_id, "📝 Опишите вашу проблему. Оператор свяжется с вами.", reply_markup=kb)

def request_feedback(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Назад")
    bot.send_message(chat_id, "✏ Напишите отзыв. Мы обязательно его учтём!", reply_markup=kb)

def show_other_options(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📌 Подать жалобу", "📎 Другое", "Назад")
    bot.send_message(chat_id, "📁 Дополнительные действия:", reply_markup=kb)

def request_consultation(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Назад")
    bot.send_message(chat_id, "💬 Консультация будет предоставлена в ближайшее время.", reply_markup=kb)

def show_employment(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📄 Посмотреть вакансии", "📨 Отправить резюме", "Назад")
    bot.send_message(chat_id, "📌 Раздел трудоустройства:", reply_markup=kb)

# === Обработка жалоб ===
@bot.message_handler(func=lambda m: m.text and m.text.lower() == "📌 подать жалобу")
def handle_complaint(message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("На чат-бот", "На сотрудника", "Самостоятельно ввести", "Назад")
    bot.send_message(message.chat.id, "🗂 Выберите тип жалобы:", reply_markup=kb)

# === Обработка непредсказуемого ввода ===
def handle_unexpected(message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Назад", "Подключиться к оператору", "Запросить помощь")
    bot.send_message(
        message.chat.id,
        "⚠️ Мы не распознали ваш запрос. Вы можете вернуться назад или запросить помощь:",
        reply_markup=kb
    )

print("✅ Бот клиента запущен")
# bot.infinity_polling()
