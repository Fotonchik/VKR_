# admin_bot.py

import telebot
from telebot import types
from core.decorators import require_role
from core.permissions import is_admin, is_staff

from core.state import StateManager
from core.permissions import (
    is_admin,
    is_manager,
    is_staff,
    can_manage_staff
)

import db.employees as employees_db
import db.db_tickets as tickets_db
import db.db_faq as faq_db

state = StateManager()


def register_handlers(bot):

    @bot.message_handler(commands=["admin"])
    @require_role("admin")
   
    def admin_panel(message):
        bot.send_message(
            message.chat.id,
            "👑 Админ-панель\n\n"
            "/staff — сотрудники\n"
            "/tickets — заявки\n"
            "/manage_faq — FAQ"
        )

    @bot.message_handler(func=lambda m: m.text == "❓ Управление FAQ")
    def manage_faq(message):
        user = get_current_user(message)
        if not is_admin(user["role"]):
            bot.send_message(message.chat.id, "⛔ Только администратор")
            return

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("📋 Список FAQ", callback_data="faq:list"),
            types.InlineKeyboardButton("➕ Добавить FAQ", callback_data="faq:add")
        )

        bot.send_message(
            message.chat.id,
            "<b>Управление FAQ</b>",
            reply_markup=markup
            )
    # =========================================================
    # HELPERS
    # =========================================================

    def get_current_user(message):
        """
        Определяем пользователя по таблице employees.
        Если нет — считаем client.
        """
        emp = employees_db.get_employee_by_id_by_user_id(message.from_user.id) \
            if hasattr(employees_db, "get_employee_by_id_by_user_id") else None

        if emp:
            return {
                "user_id": emp["user_id"],
                "role": emp["role"]
            }

        return {
            "user_id": message.from_user.id,
            "role": "client"
        }


    # =========================================================
    # START / MENU
    # =========================================================

    @bot.message_handler(commands=["start"])
    def start(message):
        user = get_current_user(message)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

        if is_staff(user["role"]):
            markup.add("🎫 Заявки")

        if can_manage_staff(user["role"]):
            markup.add("👥 Сотрудники")

        if is_admin(user["role"]):
            markup.add("❓ Управление FAQ")

        bot.send_message(
            message.chat.id,
            "Административная панель:",
            reply_markup=markup
        )


    # =========================================================
    # STAFF
    # =========================================================

    @bot.message_handler(func=lambda m: m.text == "👥 Сотрудники")
    def staff_menu(message):
        user = get_current_user(message)

        if not can_manage_staff(user["role"]):
            bot.send_message(message.chat.id, "⛔ Недостаточно прав")
            return

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("📋 Список", callback_data="staff:list"),
            types.InlineKeyboardButton("➕ Добавить", callback_data="staff:add")
        )

        bot.send_message(
            message.chat.id,
            "<b>Управление сотрудниками</b>",
            reply_markup=markup
        )


    @bot.callback_query_handler(func=lambda c: c.data == "staff:list")
    def staff_list(call):
        items = employees_db.get_employees(include_inactive=True)

        markup = types.InlineKeyboardMarkup()
        for e in items:
            status = "🟢" if e["is_active"] else "🔴"
            markup.add(
                types.InlineKeyboardButton(
                    f"{status} {e['full_name']} ({e['role']})",
                    callback_data=f"staff:view:{e['id']}"
                )
            )

        bot.edit_message_text(
            "📋 <b>Сотрудники</b>",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )


    @bot.callback_query_handler(func=lambda c: c.data.startswith("staff:view"))
    def staff_view(call):
        emp_id = int(call.data.split(":")[2])
        emp = employees_db.get_employee_by_id(emp_id)

        text = (
            f"<b>{emp['full_name']}</b>\n"
            f"Роль: {emp['role']}\n"
            f"Код: {emp['employee_code']}\n"
            f"ID: {emp['user_id']}\n"
            f"Статус: {'Активен' if emp['is_active'] else 'Неактивен'}"
        )

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "🔁 Вкл/Выкл",
                callback_data=f"staff:toggle:{emp_id}"
            )
        )
        markup.add(types.InlineKeyboardButton("⬅ Назад", callback_data="staff:list"))

        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )


    @bot.callback_query_handler(func=lambda c: c.data.startswith("staff:toggle"))
    def staff_toggle(call):
        emp_id = int(call.data.split(":")[2])
        emp = employees_db.get_employee_by_id(emp_id)

        employees_db.set_employee_active(
            current_user_id=call.from_user.id,
            employee_id=emp_id,
            is_active=not emp["is_active"]
        )

        bot.answer_callback_query(call.id, "Статус обновлён")
        staff_list(call)


    # =========================================================
    # TICKETS (STAFF)
    # =========================================================

    @bot.message_handler(func=lambda m: m.text == "🎫 Заявки")
    def tickets_menu(message):
        user = get_current_user(message)

        if not is_staff(user["role"]):
            bot.send_message(message.chat.id, "⛔ Недостаточно прав")
            return

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("📥 Новые", callback_data="tickets:new"),
            types.InlineKeyboardButton("🔄 В работе", callback_data="tickets:in_progress")
        )
        markup.add(
            types.InlineKeyboardButton("✅ Решённые", callback_data="tickets:resolved"),
            types.InlineKeyboardButton("📁 Закрытые", callback_data="tickets:closed")
        )

        bot.send_message(
            message.chat.id,
            "<b>Заявки</b>",
            reply_markup=markup
        )


    @bot.callback_query_handler(func=lambda c: c.data.startswith("tickets:"))
    def tickets_list(call):
        status = call.data.split(":")[1]
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


    @bot.callback_query_handler(func=lambda c: c.data.startswith("ticket:view"))
    def ticket_view(call):
        ticket_id = int(call.data.split(":")[2])
        ticket = tickets_db.get_ticket_by_id(ticket_id)
        messages = tickets_db.get_ticket_messages(ticket_id)

        text = (
            f"<b>{ticket['ticket_number']}</b>\n"
            f"Статус: {ticket['status']}\n"
            f"Приоритет: {ticket['priority']}\n\n"
            f"<b>Диалог:</b>\n"
        )

        for m in messages:
            who = "Клиент" if m["user_id"] == ticket["user_id"] else "Сотрудник"
            text += f"\n<b>{who}:</b> {m['content']}"

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "✉ Ответить",
                callback_data=f"ticket:reply:{ticket_id}"
            ),
            types.InlineKeyboardButton(
                "🔄 В работу",
                callback_data=f"ticket:status:{ticket_id}:in_progress"
            ),
            types.InlineKeyboardButton(
                "✅ Закрыть",
                callback_data=f"ticket:status:{ticket_id}:closed"
            )
        )
        markup.add(types.InlineKeyboardButton("⬅ Назад", callback_data="tickets:menu"))

        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )


    @bot.callback_query_handler(func=lambda c: c.data.startswith("ticket:reply"))
    def ticket_reply_start(call):
        ticket_id = int(call.data.split(":")[2])
        state.set(call.from_user.id, "ticket_reply", {"ticket_id": ticket_id})
        bot.send_message(call.message.chat.id, "Введите ответ клиенту:")


    @bot.message_handler(func=lambda m: state.get_state(m.from_user.id) == "ticket_reply")
    def ticket_reply_send(message):
        data = state.get(message.from_user.id)

        tickets_db.add_ticket_message(
            ticket_id=data["ticket_id"],
            user_id=message.from_user.id,
            content=message.text
        )

        state.clear(message.from_user.id)
        bot.send_message(message.chat.id, "✅ Ответ отправлен")


    # =========================================================
    # FAQ MANAGEMENT (ADMIN)
    # =========================================================
