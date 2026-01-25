import telebot
from telebot import types
import config
import db
import db_tickets

BOT_TOKEN = config.BOT_TOKEN
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")


# =========================================================
# КЛАВИАТУРЫ
# =========================================================

def operator_main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📂 Очередь заявок")
    kb.add("📄 Мои заявки")
    return kb


def ticket_dialog_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("❌ Закрыть заявку")
    kb.add("⬅️ Выйти из диалога")
    return kb


# =========================================================
# СТАРТ
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):
    db.register_user(message.from_user)

    if not db.has_role(message.from_user.id, ["operator", "manager", "admin"]):
        bot.send_message(message.chat.id, "⛔ У вас нет доступа.")
        return

    bot.send_message(
        message.chat.id,
        "👨‍💻 Панель оператора",
        reply_markup=operator_main_kb()
    )

    active = db.get_active_ticket(message.from_user.id)
    if active:
        show_ticket_dialog(message.chat.id, active)


# =========================================================
# ОЧЕРЕДЬ ЗАЯВОК
# =========================================================

@bot.message_handler(func=lambda m: m.text == "📂 Очередь заявок")
def queue(message):
    tickets = db_tickets.get_open_tickets()

    if not tickets:
        bot.send_message(message.chat.id, "Очередь пуста.")
        return

    kb = types.InlineKeyboardMarkup()
    for t in tickets:
        kb.add(
            types.InlineKeyboardButton(
                text=f"Заявка #{t['id']}",
                callback_data=f"take:{t['id']}"
            )
        )

    bot.send_message(
        message.chat.id,
        "📂 Открытые заявки:",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("take:"))
def take_ticket(call):
    ticket_id = int(call.data.split(":")[1])

    try:
        db_tickets.assign_operator(ticket_id, call.from_user.id)
    except Exception as e:
        bot.answer_callback_query(call.id, str(e))
        return

    db.set_active_ticket(call.from_user.id, ticket_id)

    bot.answer_callback_query(call.id, "Заявка взята в работу")
    show_ticket_dialog(call.message.chat.id, ticket_id)


# =========================================================
# МОИ ЗАЯВКИ
# =========================================================

@bot.message_handler(func=lambda m: m.text == "📄 Мои заявки")
def my_tickets(message):
    tickets = db_tickets.get_tickets_by_operator(message.from_user.id)

    if not tickets:
        bot.send_message(message.chat.id, "У вас нет заявок.")
        return

    kb = types.InlineKeyboardMarkup()
    for t in tickets:
        kb.add(
            types.InlineKeyboardButton(
                text=f"#{t['id']} — {t['status']}",
                callback_data=f"open:{t['id']}"
            )
        )

    bot.send_message(
        message.chat.id,
        "📄 Ваши заявки:",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("open:"))
def open_ticket(call):
    ticket_id = int(call.data.split(":")[1])
    db.set_active_ticket(call.from_user.id, ticket_id)
    show_ticket_dialog(call.message.chat.id, ticket_id)
    bot.answer_callback_query(call.id)


# =========================================================
# ДИАЛОГ ПО ЗАЯВКЕ
# =========================================================

def show_ticket_dialog(chat_id, ticket_id):
    ticket = db_tickets.get_ticket(ticket_id)
    client = db.get_user(ticket["client_id"])
    messages = db_tickets.get_ticket_messages(ticket_id)

    header = (
        f"<b>💬 Заявка #{ticket_id}</b>\n"
        f"Клиент: {client['full_name'] or client['tg_username'] or client['user_id']}\n\n"
    )

    text = header
    for m in messages:
        author = "Клиент" if m["author_role"] == "client" else "Вы"
        text += f"<b>{author}:</b> {m['content']}\n"

    bot.send_message(chat_id, text, reply_markup=ticket_dialog_kb())


@bot.message_handler(func=lambda m: True)
def dialog_handler(message):
    if not db.has_role(message.from_user.id, ["operator", "manager", "admin"]):
        return

    ticket_id = db.get_active_ticket(message.from_user.id)
    if not ticket_id:
        return

    if message.text == "⬅️ Выйти из диалога":
        db.clear_active_ticket(message.from_user.id)
        bot.send_message(
            message.chat.id,
            "Вы вышли из диалога.",
            reply_markup=operator_main_kb()
        )
        return

    if message.text == "❌ Закрыть заявку":
        db_tickets.close_ticket(ticket_id)
        db.clear_active_ticket(message.from_user.id)

        ticket = db_tickets.get_ticket(ticket_id)
        bot.send_message(ticket["client_id"], "✅ Ваша заявка закрыта оператором.")

        bot.send_message(
            message.chat.id,
            "Заявка закрыта.",
            reply_markup=operator_main_kb()
        )
        return

    # сообщение оператор → клиент
    db_tickets.add_message(
        ticket_id=ticket_id,
        author_id=message.from_user.id,
        author_role="operator",
        content=message.text
    )

    ticket = db_tickets.get_ticket(ticket_id)
    bot.send_message(
        ticket["client_id"],
        f"💬 Ответ оператора:\n\n{message.text}"
    )

    bot.send_message(message.chat.id, "📨 Сообщение отправлено клиенту.")


# =========================================================
# ЗАПУСК
# =========================================================

def run():
    bot.infinity_polling()
