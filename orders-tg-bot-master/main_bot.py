# main_bot.py — стартовый бот, переключающий панели по ролям

import telebot
import config
import db
import db_tickets
import operator_manager_bot
# import client_bot

from admin_bot import admin_panel
from operator_manager_bot import manager_panel, operator_panel


bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode="HTML")

db.ensure_and_get_users()
db_tickets.init_ticket_db()

# === Команда /start — проверка роли ===
@bot.message_handler(commands=['start'])
def handle_start(message):
    uid = message.from_user.id
    if db.has_access(uid, ['admin']):
        return admin_panel(message)
    elif operator_manager_bot.is_operator(uid):
        return operator_panel(message)
    elif operator_manager_bot.is_manager(uid):
        return manager_panel(message)
    else:
        return 
    # client_bot.send_main_menu(message)
    
print("🚀 Запущен универсальный бот")
bot.infinity_polling()
