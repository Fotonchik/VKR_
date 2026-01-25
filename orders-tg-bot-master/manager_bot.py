import telebot
from telebot import types
import config
import db
import db_tickets

BOT_TOKEN = config.BOT_TOKEN
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")


# =========================================================
# ВРЕМЕННОЕ СОСТОЯНИЕ (РЕДАКТИРОВАНИЕ КЛИЕНТА)
# =========================================================

editing_client = {}


# =========================================================
# КЛАВИАТУРЫ
# =========================================================

def manager_main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📋 Все заявки")
    kb.add("👤 Клиенты")
    return kb


def ticket_view_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("❌ Закрыть заявку")
    kb.add("⬅️ Назад")
    return kb


def client_edit_kb(client_id):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            text="✏️ Изменить ФИО",
            callback_data=f"edit_name:{client_id}"
        ),
        types.InlineKeyboardButton(
            text="✏️ Изменить телефон",
            callback_data=f"edit_phone:{client_id}"
        )
    )
    return kb


# =========================================================
# СТАРТ
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):
    db.register_user(message.from_user)

    if not db.has_role(message.from_user.id, ["manager", "admin"]):
        bot.send_message(message.chat.id, "⛔ Доступ запрещён.")
        return

    bot.send_message(
        message.chat.id,
        "📊 Панель менеджера",
        reply_markup=manager_main_kb()
    )


# =========================================================
# ВСЕ ЗАЯВКИ
# =========================================================

@bot.message_handler(func=lambda m: m.text == "📋 Все заявки")
def all_tickets(message):
    tickets = db_tickets.get_all_tickets()

    if not tickets:
        bot.send_message(message.chat.id, "Заявок нет.")
        return

    kb = types.InlineKeyboardMarkup()
    for t in tickets:
        kb.add(
            types.InlineKeyboardButton(
                text=f"#{t['id']} — {t['status']}",
                callback_data=f"view_ticket:{t['id']}"
            )
        )

    bot.send_message(
        message.chat.id,
        "📋 Все заявки:",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("view_ticket:"))
def view_ticket(call):
    ticket_id = int(call.data.split(":")[1])
    db.set_active_ticket(call.from_user.id, ticket_id)
    show_ticket(call.message.chat.id, ticket_id)
    bot.answer_callback_query(call.id)


# =========================================================
# ПРОСМОТР ЗАЯВКИ
# =========================================================

def show_ticket(chat_id, ticket_id):
    ticket = db_tickets.get_ticket(ticket_id)
    client = db.get_user(ticket["client_id"])
    operator = db.get_user(ticket["operator_id"]) if ticket["operator_id"] else None
    messages = db_tickets.get_ticket_messages(ticket_id)

    header = (
        f"<b>💼 Заявка #{ticket_id}</b>\n"
        f"Статус: {ticket['status']}\n"
        f"Клиент: {client['full_name'] or client['tg_username'] or client['user_id']}\n"
        f"Оператор: {operator['tg_username'] if operator else '—'}\n\n"
    )

    text = header
    for m in messages:
        role = "Клиент" if m["author_role"] == "client" else "Оператор"
        text += f"<b>{role}:</b> {m['content']}\n"

    bot.send_message(chat_id, text, reply_markup=ticket_view_kb())


# =========================================================
# КЛИЕНТЫ
# =========================================================

@bot.message_handler(func=lambda m: m.text == "👤 Клиенты")
def clients(message):
    users = db.get_all_clients()

    if not users:
        bot.send_message(message.chat.id, "Клиентов нет.")
        return

    kb = types.InlineKeyboardMarkup()
    for u in users:
        kb.add(
            types.InlineKeyboardButton(
                text=u["full_name"] or u["tg_username"] or str(u["user_id"]),
                callback_data=f"view_client:{u['user_id']}"
            )
        )

    bot.send_message(
        message.chat.id,
        "👤 Клиенты:",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("view_client:"))
def view_client(call):
    client_id = int(call.data.split(":")[1])
    user = db.get_user(client_id)

    text = (
        f"<b>👤 Клиент</b>\n\n"
        f"ID: {user['user_id']}\n"
        f"ФИО: {user['full_name'] or '—'}\n"
        f"Телефон: {user['phone'] or '—'}\n"
        f"Email: {user['email'] or '—'}"
    )

    bot.send_message(
        call.message.chat.id,
        text,
        reply_markup=client_edit_kb(client_id)
    )
    bot.answer_callback_query(call.id)


# =========================================================
# РЕДАКТИРОВАНИЕ КЛИЕНТА
# =========================================================

@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_"))
def edit_client(call):
    action, client_id = call.data.split(":")
    client_id = int(client_id)

    field = "full_name" if "name" in action else "phone"
    editing_client[call.from_user.id] = (client_id, field)

    bot.send_message(
        call.message.chat.id,
        f"Введите новое значение для поля <b>{field}</b>:"
    )
    bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda m: m.from_user.id in editing_client)
def save_client_edit(message):
    client_id, field = editing_client.pop(message.from_user.id)

    kwargs = {field: message.text}
    db.update_client_profile(client_id, **kwargs)

    bot.send_message(
        message.chat.id,
        "✅ Данные клиента обновлены.",
        reply_markup=manager_main_kb()
    )


# =========================================================
# ДЕЙСТВИЯ С ЗАЯВКОЙ
# =========================================================

@bot.message_handler(func=lambda m: m.text == "❌ Закрыть заявку")
def close_ticket(message):
    ticket_id = db.get_active_ticket(message.from_user.id)
    if not ticket_id:
        return

    db_tickets.close_ticket(ticket_id)
    db.clear_active_ticket(message.from_user.id)

    ticket = db_tickets.get_ticket(ticket_id)
    bot.send_message(ticket["client_id"], "✅ Ваша заявка закрыта менеджером.")

    bot.send_message(
        message.chat.id,
        "Заявка закрыта.",
        reply_markup=manager_main_kb()
    )


@bot.message_handler(func=lambda m: m.text == "⬅️ Назад")
def back(message):
    db.clear_active_ticket(message.from_user.id)
    bot.send_message(
        message.chat.id,
        "Возврат в меню.",
        reply_markup=manager_main_kb()
    )


# =========================================================
# ЗАПУСК
# =========================================================

def run():
    bot.infinity_polling()
