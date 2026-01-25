# modules/tickets.py

from telebot import types
import db.db_tickets as tickets_db
import db.employees as employees_db
from core.permissions import is_staff
from core.state import StateManager

state = StateManager()


# =========================================================
# CLIENT: CREATE TICKET
# =========================================================

def new_ticket_start(bot, message):
    state.set(message.from_user.id, "ticket_subject", {})
    bot.send_message(message.chat.id, "Введите тему заявки:")


def ticket_subject(bot, message):
    data = {"subject": message.text}
    state.set(message.from_user.id, "ticket_description", data)
    bot.send_message(message.chat.id, "Опишите проблему подробно:")


def ticket_description(bot, message):
    data = state.get(message.from_user.id)
    data["description"] = message.text

    ticket_id, ticket_number = tickets_db.create_ticket(
        user_id=message.from_user.id,
        subject=data["subject"],
        description=data["description"]
    )

    # первое сообщение заявки
    tickets_db.add_ticket_message(
        ticket_id=ticket_id,
        user_id=message.from_user.id,
        content=data["description"]
    )

    state.clear(message.from_user.id)

    bot.send_message(
        message.chat.id,
        f"✅ Заявка <b>{ticket_number}</b> создана.\n"
        f"Мы скоро с вами свяжемся."
    )


# =========================================================
# CLIENT: MY TICKETS
# =========================================================

def my_tickets(bot, message):
    items = tickets_db.get_tickets_for_user(message.from_user.id)

    if not items:
        bot.send_message(message.chat.id, "У вас пока нет заявок.")
        return

    markup = types.InlineKeyboardMarkup()
    for t in items:
        markup.add(
            types.InlineKeyboardButton(
                f"{t['ticket_number']} [{t['status']}]",
                callback_data=f"ticket:view:{t['id']}"
            )
        )

    bot.send_message(
        message.chat.id,
        "📂 <b>Мои заявки</b>",
        reply_markup=markup
    )


# =========================================================
# STAFF: LIST
# =========================================================

def tickets_menu(bot, message, current_user):
    if not is_staff(current_user["role"]):
        bot.send_message(message.chat.id, "⛔ Доступ запрещён")
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("📥 Новые", callback_data="ticket:list:new"),
        types.InlineKeyboardButton("🔄 В работе", callback_data="ticket:list:in_progress")
    )
    markup.add(
        types.InlineKeyboardButton("✅ Завершённые", callback_data="ticket:list:resolved"),
        types.InlineKeyboardButton("📁 Закрытые", callback_data="ticket:list:closed")
    )

    bot.send_message(
        message.chat.id,
        "🎫 <b>Заявки</b>",
        reply_markup=markup
    )


def tickets_list(bot, call, status):
    items = tickets_db.get_tickets_by_status(status)

    markup = types.InlineKeyboardMarkup()
    for t in items:
        markup.add(
            types.InlineKeyboardButton(
                f"{t['ticket_number']} ({t['priority']})",
                callback_data=f"ticket:view:{t['id']}"
            )
        )

    markup.add(types.InlineKeyboardButton("⬅ Назад", callback_data="tickets:menu"))

    bot.edit_message_text(
        f"📋 Заявки [{status}]",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


# =========================================================
# VIEW + DIALOG
# =========================================================

def ticket_view(bot, call, ticket_id, current_user):
    ticket = tickets_db.get_ticket_by_id(ticket_id)
    messages = tickets_db.get_ticket_messages(ticket_id)

    text = (
        f"<b>{ticket['ticket_number']}</b>\n"
        f"Статус: {ticket['status']}\n"
        f"Приоритет: {ticket['priority']}\n\n"
        f"<b>Сообщения:</b>\n"
    )

    for m in messages:
        sender = "👤 Клиент" if m["user_id"] == ticket["user_id"] else "🧑‍💼 Сотрудник"
        text += f"\n<b>{sender}:</b> {m['content']}"

    markup = types.InlineKeyboardMarkup()

    if is_staff(current_user["role"]):
        markup.add(
            types.InlineKeyboardButton("✉ Ответить", callback_data=f"ticket:reply:{ticket_id}"),
            types.InlineKeyboardButton("🔄 В работу", callback_data=f"ticket:status:{ticket_id}:in_progress")
        )

    markup.add(types.InlineKeyboardButton("⬅ Назад", callback_data="tickets:menu"))

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


# =========================================================
# REPLY
# =========================================================

def ticket_reply_start(bot, call, ticket_id):
    state.set(call.from_user.id, "ticket_reply", {"ticket_id": ticket_id})
    bot.send_message(call.message.chat.id, "Введите ответ по заявке:")


def ticket_reply_send(bot, message):
    data = state.get(message.from_user.id)

    tickets_db.add_ticket_message(
        ticket_id=data["ticket_id"],
        user_id=message.from_user.id,
        content=message.text
    )

    state.clear(message.from_user.id)
    bot.send_message(message.chat.id, "✅ Ответ отправлен")
