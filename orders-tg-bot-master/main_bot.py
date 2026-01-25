# main_bot.py

import telebot
from telebot import types

import config

# DB init
from db.employees import init_employees_table
from db.db_faq import init_faq_table
from db.db_tickets import init_tickets_tables
from core.audit import init_audit_table

# modules
import modules.staff as staff
import modules.faq as faq
import modules.tickets as tickets

# state
from core.state import StateManager

bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode="HTML")
state = StateManager()


# =========================================================
# INIT DB
# =========================================================

init_employees_table()
init_faq_table()
init_tickets_tables()
init_audit_table()


# =========================================================
# MOCK CURRENT USER (пример)
# =========================================================

def get_current_user(message):
    """
    В реальном проекте:
    - проверка в employees
    - если нет → client
    """
    return {
        "user_id": message.from_user.id,
        "role": "admin"  # для тестов, потом заменить на реальную проверку
    }


# =========================================================
# COMMANDS
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "Добро пожаловать!\n"
        "/faq — помощь\n"
        "/new_ticket — создать заявку\n"
        "/my_tickets — мои заявки\n"
        "/staff — сотрудники (если есть доступ)\n"
        "/tickets — заявки (для персонала)"
    )


@bot.message_handler(commands=["faq"])
def faq_cmd(message):
    faq.show_faq(bot, message)


@bot.message_handler(commands=["manage_faq"])
def manage_faq_cmd(message):
    user = get_current_user(message)
    faq.manage_faq(bot, message, user)


@bot.message_handler(commands=["staff"])
def staff_cmd(message):
    user = get_current_user(message)
    staff.staff_menu(bot, message, user)


@bot.message_handler(commands=["new_ticket"])
def new_ticket_cmd(message):
    tickets.new_ticket_start(bot, message)


@bot.message_handler(commands=["my_tickets"])
def my_tickets_cmd(message):
    tickets.my_tickets(bot, message)


@bot.message_handler(commands=["tickets"])
def tickets_cmd(message):
    user = get_current_user(message)
    tickets.tickets_menu(bot, message, user)


# =========================================================
# FSM HANDLER
# =========================================================

@bot.message_handler(func=lambda m: state.has_state(m.from_user.id))
def fsm_handler(message):
    current = state.get_state(message.from_user.id)
    user = get_current_user(message)

    if current == "ticket_subject":
        tickets.ticket_subject(bot, message)
    elif current == "ticket_description":
        tickets.ticket_description(bot, message)
    elif current == "ticket_reply":
        tickets.ticket_reply_send(bot, message)
    elif current == "staff_add_name":
        staff.staff_add_name(bot, message)
    elif current == "staff_add_code":
        staff.staff_add_code(bot, message, user)
    elif current == "faq_add_content":
        faq.admin_faq_add_content(bot, message, user)


# =========================================================
# CALLBACK HANDLER (упрощённый, расширяемый)
# =========================================================

@bot.callback_query_handler(func=lambda c: True)
def callback_handler(call):
    data = call.data
    user = get_current_user(call.message)

    if data == "staff:list":
        staff.staff_list(bot, call, user)
    elif data.startswith("staff:add"):
        staff.staff_add_start(bot, call, user)
    elif data.startswith("ticket:view"):
        ticket_id = int(data.split(":")[2])
        tickets.ticket_view(bot, call, ticket_id, user)
    elif data.startswith("ticket:reply"):
        ticket_id = int(data.split(":")[2])
        tickets.ticket_reply_start(bot, call, ticket_id)


# =========================================================
# START
# =========================================================

bot.infinity_polling()
