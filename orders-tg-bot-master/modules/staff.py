# modules/staff.py

from telebot import types
import db.employees as employees
from core.permissions import get_visible_roles, can_manage_staff
from core.state import StateManager

state = StateManager()


# =========================================================
# ENTRY POINT
# =========================================================

def staff_menu(bot, message, current_user):
    if not can_manage_staff(current_user["role"]):
        bot.send_message(
            message.chat.id,
            "⛔ У вас нет доступа к управлению сотрудниками"
        )
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("📋 Список сотрудников", callback_data="staff:list"),
        types.InlineKeyboardButton("➕ Добавить сотрудника", callback_data="staff:add")
    )

    bot.send_message(
        message.chat.id,
        "👥 <b>Управление сотрудниками</b>",
        reply_markup=markup
    )


# =========================================================
# LIST
# =========================================================

def staff_list(bot, call, current_user):
    roles = get_visible_roles(current_user["role"])
    items = employees.get_employees(filter_roles=roles)

    markup = types.InlineKeyboardMarkup()

    for emp in items:
        status = "🟢" if emp["is_active"] else "🔴"
        markup.add(
            types.InlineKeyboardButton(
                f"{status} {emp['full_name']} ({emp['role']})",
                callback_data=f"staff:view:{emp['id']}"
            )
        )

    markup.add(
        types.InlineKeyboardButton("⬅ Назад", callback_data="staff:menu")
    )

    bot.edit_message_text(
        "📋 <b>Сотрудники</b>",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


# =========================================================
# ADD FLOW
# =========================================================

def staff_add_start(bot, call, current_user):
    roles = get_visible_roles(current_user["role"])
    markup = types.InlineKeyboardMarkup()

    for r in roles:
        markup.add(
            types.InlineKeyboardButton(
                f"👑 {r}",
                callback_data=f"staff:add:role:{r}"
            )
        )

    markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="staff:menu"))

    bot.edit_message_text(
        "Выберите роль нового сотрудника:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


def staff_add_role(bot, call, role):
    state.set(call.from_user.id, "staff_add_role", {"role": role})
    bot.send_message(call.message.chat.id, "Введите Telegram ID сотрудника:")


def staff_add_user_id(bot, message):
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "❌ Telegram ID должен быть числом")
        return

    data = state.get(message.from_user.id)
    data["user_id"] = int(message.text)

    state.set(message.from_user.id, "staff_add_name", data)
    bot.send_message(message.chat.id, "Введите полное имя сотрудника:")


def staff_add_name(bot, message):
    data = state.get(message.from_user.id)
    data["full_name"] = message.text.strip()

    state.set(message.from_user.id, "staff_add_code", data)
    bot.send_message(message.chat.id, "Введите код сотрудника (например EMP-001):")


def staff_add_code(bot, message, current_user):
    data = state.get(message.from_user.id)
    data["employee_code"] = message.text.strip()

    try:
        employees.add_employee(
            current_user_id=current_user["user_id"],
            current_user_role=current_user["role"],
            **data
        )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")
        return

    state.clear(message.from_user.id)
    bot.send_message(message.chat.id, "✅ Сотрудник успешно добавлен")


# =========================================================
# VIEW
# =========================================================

def staff_view(bot, call, employee_id):
    emp = employees.get_employee_by_id(employee_id)

    text = (
        f"<b>{emp['full_name']}</b>\n"
        f"👑 Роль: {emp['role']}\n"
        f"🔢 Код: {emp['employee_code']}\n"
        f"🆔 ID: {emp['user_id']}\n"
        f"Статус: {'Активен' if emp['is_active'] else 'Неактивен'}"
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✏️ Редактировать", callback_data=f"staff:edit:{employee_id}"),
        types.InlineKeyboardButton("🔁 Активировать / Деактивировать", callback_data=f"staff:toggle:{employee_id}")
    )
    markup.add(types.InlineKeyboardButton("⬅ Назад", callback_data="staff:list"))

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )
