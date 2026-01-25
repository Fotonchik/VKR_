# client_bot.py

import telebot
from telebot import types

from core.decorators import require_role
from core.permissions import is_admin, is_staff

from core.state import StateManager
from core.permissions import is_staff

import db.db_faq as faq_db
import db.db_tickets as tickets_db

state = StateManager()


def register_handlers(bot):

    @bot.message_handler(commands=["start"])
    # =========================================================
    # START
    # =========================================================

    @bot.message_handler(commands=["start"])
    def start(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("❓ FAQ", "📝 Оставить заявку")
        markup.add("📂 Мои заявки")

        bot.send_message(
            message.chat.id,
            "Добро пожаловать!\n"
            "Выберите действие:",
            reply_markup=markup
        )


    # =========================================================
    # FAQ
    # =========================================================

    @bot.message_handler(func=lambda m: m.text == "❓ FAQ")
    def faq_menu(message):
        items = faq_db.get_faq_for_clients()

        if not items:
            bot.send_message(message.chat.id, "FAQ пока пуст.")
            return

        markup = types.InlineKeyboardMarkup()
        for f in items:
            markup.add(
                types.InlineKeyboardButton(
                    f["title"],
                    callback_data=f"faq:view:{f['id']}"
                )
            )

        bot.send_message(
            message.chat.id,
            "❓ <b>Часто задаваемые вопросы</b>",
            reply_markup=markup
        )


    @bot.callback_query_handler(func=lambda c: c.data.startswith("faq:view"))
    def faq_view(call):
        faq_id = int(call.data.split(":")[2])
        f = faq_db.get_faq_by_id(faq_id)

        if not f or not f["is_active"]:
            bot.answer_callback_query(call.id, "FAQ недоступен")
            return

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅ Назад", callback_data="faq:back"))

        bot.edit_message_text(
            f"<b>{f['title']}</b>\n\n{f['content']}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )


    @bot.callback_query_handler(func=lambda c: c.data == "faq:back")
    def faq_back(call):
        faq_menu(call.message)


    # =========================================================
    # NEW TICKET (FSM)
    # =========================================================

    @bot.message_handler(func=lambda m: m.text == "📝 Оставить заявку")
    def new_ticket_start(message):
        state.set(message.from_user.id, "ticket_subject", {})
        bot.send_message(message.chat.id, "Введите тему заявки:")


    @bot.message_handler(func=lambda m: state.get_state(m.from_user.id) == "ticket_subject")
    def ticket_subject(message):
        state.set(
            message.from_user.id,
            "ticket_description",
            {"subject": message.text}
        )
        bot.send_message(message.chat.id, "Опишите проблему подробно:")


    @bot.message_handler(func=lambda m: state.get_state(m.from_user.id) == "ticket_description")
    def ticket_description(message):
        data = state.get(message.from_user.id)

        ticket_id, ticket_number = tickets_db.create_ticket(
            user_id=message.from_user.id,
            subject=data["subject"],
            description=message.text
        )

        tickets_db.add_ticket_message(
            ticket_id=ticket_id,
            user_id=message.from_user.id,
            content=message.text
        )

        state.clear(message.from_user.id)

        bot.send_message(
            message.chat.id,
            f"✅ Заявка <b>{ticket_number}</b> успешно создана.\n"
            f"Мы скоро ответим."
        )


    # =========================================================
    # MY TICKETS
    # =========================================================

    @bot.message_handler(func=lambda m: m.text == "📂 Мои заявки")
    def my_tickets(message):
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
            "📂 <b>Ваши заявки</b>",
            reply_markup=markup
        )


    @bot.callback_query_handler(func=lambda c: c.data.startswith("ticket:view"))
    def ticket_view(call):
        ticket_id = int(call.data.split(":")[2])
        ticket = tickets_db.get_ticket_by_id(ticket_id)
        messages = tickets_db.get_ticket_messages(ticket_id)

        text = (
            f"<b>{ticket['ticket_number']}</b>\n"
            f"Статус: {ticket['status']}\n\n"
            f"<b>Диалог:</b>\n"
        )

        for m in messages:
            who = "Вы" if m["user_id"] == call.from_user.id else "Сотрудник"
            text += f"\n<b>{who}:</b> {m['content']}"

        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id
        )

