# admin_bot.py — функции административной панели

import uuid
from telebot import types
import config
import db

# Временное хранилище этапов добавления/редактирования/удаления
admin_workflow = {}

# Получение списка сотрудников с ролями
def get_role_dict():
    """Возвращает словарь ролей с ID пользователей"""
    users_from_db = db.ensure_and_get_users()
    role_dict = {"admin": [], "manager": [], "tp": []}
    admin_ids = config.ADMIN_CHAT_ID[:]
    manager_ids = config.MANAGER_CHAT_ID[:]
    tp_ids = config.TP_CHAT_ID[:]
    
    for uid, name, role in users_from_db:
        if role in role_dict:
            role_dict[role].append(uid)
            if role == "admin" and uid not in admin_ids:
                admin_ids.append(uid)
            if role == "manager" and uid not in manager_ids:
                manager_ids.append(uid)
            if role == "tp" and uid not in tp_ids:
                tp_ids.append(uid)
    
    return role_dict, admin_ids, manager_ids, tp_ids

# Проверка роли
def has_role(user_id, roles, role_dict):
    return any(user_id in role_dict.get(r, []) for r in roles)

# Проверка доступа: либо роль, либо ID в конфиге
def has_access(user_id, roles, role_dict):
    if "admin" in roles and user_id in config.ADMIN_CHAT_ID:
        return True
    if "manager" in roles and user_id in config.MANAGER_CHAT_ID:
        return True
    if "tp" in roles and user_id in config.TP_CHAT_ID:
        return True
    return has_role(user_id, roles, role_dict)

# Панель администратора
def admin_panel(bot, message):
    """Отображает панель администратора"""
    role_dict, _, _, _ = get_role_dict()
    
    if not has_access(message.from_user.id, ["admin"], role_dict):
        return bot.send_message(message.chat.id, "❌ У вас нет доступа к административной панели.")

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🔧 Меню редактирования информации для клиента", callback_data="edit_client_info"))
    keyboard.add(types.InlineKeyboardButton("👤 Редактирование учетных записей", callback_data="edit_accounts"))
    keyboard.add(types.InlineKeyboardButton("👀 Просмотр учетных записей", callback_data="list_staff_menu"))
    keyboard.add(types.InlineKeyboardButton("📁 Редактирование данных по клиенту", callback_data="edit_client_data"))
    keyboard.add(types.InlineKeyboardButton("🔄 Запросы от менеджмента", callback_data="manager_requests"))
    keyboard.add(types.InlineKeyboardButton("📌 Просмотр заявок", callback_data="view_requests"))
    bot.send_message(message.chat.id, "⚖ Административная панель:", reply_markup=keyboard)

# Обработчик callback-запросов для администратора
def handle_admin_callback(bot, call):
    """Обрабатывает callback-запросы администратора"""
    role_dict, _, _, _ = get_role_dict()
    
    if not has_access(call.from_user.id, ["admin"], role_dict):
        return bot.answer_callback_query(call.id, "❌ Нет доступа")

    if call.data == "edit_accounts":
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("➕ Добавить сотрудника", callback_data="add_user"))
        keyboard.add(types.InlineKeyboardButton("🛠 Редактировать операторов", callback_data="edit_tp"))
        keyboard.add(types.InlineKeyboardButton("🛠 Редактировать менеджеров", callback_data="edit_manager"))
        keyboard.add(types.InlineKeyboardButton("🛠 Редактировать администраторов", callback_data="edit_admin"))
        keyboard.add(types.InlineKeyboardButton("↩ Назад", callback_data="back_to_main"))
        bot.send_message(call.message.chat.id, "👤 Редактирование учетных записей:", reply_markup=keyboard)

    elif call.data == "add_user":
        gen_key = uuid.uuid4().hex[:8]
        admin_workflow[call.from_user.id] = {"key": gen_key}
        bot.send_message(call.message.chat.id, f"🆔 Сгенерирован уникальный ключ: <code>{gen_key}</code>")
        bot.send_message(call.message.chat.id, "📝 Введите имя нового сотрудника или 'назад'")
        bot.register_next_step_handler(call.message, lambda m: process_new_user_name(bot, m))

    elif call.data == "list_staff":
        users = db.ensure_and_get_users()
        if not users:
            return bot.send_message(call.message.chat.id, "⚠ Сотрудники не найдены.")

        grouped = {"admin": [], "manager": [], "tp": []}
        for uid, name, role in users:
            if role in grouped:
                grouped[role].append((uid, name))

        text = "👥 <b>Список сотрудников:</b>\n\n"
        for role, display in {"admin": "Администраторы", "manager": "Менеджеры", "tp": "Операторы"}.items():
            if grouped[role]:
                text += f"<b>{display}:</b>\n"
                for uid, name in grouped[role]:
                    is_base_admin = uid in config.ADMIN_CHAT_ID if role == "admin" else False
                    mark = " (встроенный)" if is_base_admin else ""
                    text += f"• <b>{name}</b> — <code>{uid}</code>{mark}\n"
                text += "\n"

        bot.send_message(call.message.chat.id, text)

    elif call.data == "view_requests":
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🟡 Открытые заявки", callback_data="req_open"))
        keyboard.add(types.InlineKeyboardButton("🟢 Активные заявки", callback_data="req_active"))
        keyboard.add(types.InlineKeyboardButton("🔴 Закрытые заявки", callback_data="req_closed"))
        keyboard.add(types.InlineKeyboardButton("↩ Назад", callback_data="back_to_main"))
        bot.send_message(call.message.chat.id, "📌 Просмотр заявок:", reply_markup=keyboard)

    elif call.data == "manager_requests":
        bot.send_message(call.message.chat.id, "📨 Здесь будут отображены запросы от менеджмента (заглушка).\n✅/❌ для каждого.")

    elif call.data == "back_to_main":
        admin_panel(bot, call.message)
    elif call.data == "list_staff_menu":
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("🧑‍💻 Операторы", callback_data="list_tp"),
            types.InlineKeyboardButton("👔 Менеджеры", callback_data="list_manager"),
            types.InlineKeyboardButton("🛡 Администраторы", callback_data="list_admin")
        )
        keyboard.add(types.InlineKeyboardButton("↩ Назад", callback_data="back_to_main"))
        bot.send_message(call.message.chat.id, "👥 Выберите категорию сотрудников:", reply_markup=keyboard)

    elif call.data.startswith("list_"):
        role_map = {
            "list_tp": "tp",
            "list_manager": "manager",
            "list_admin": "admin"
        }
        role = role_map.get(call.data)
        if not role:
            return
        role_display = {"tp": "Операторы", "manager": "Менеджеры", "admin": "Администраторы"}[role]

        users = [u for u in db.ensure_and_get_users() if len(u) > 2 and u[2] == role]
        if not users:
            return bot.send_message(call.message.chat.id, f"⚠ Нет зарегистрированных {role_display.lower()}.")

        text = f"👥 <b>{role_display}:</b>\n\n"
        for uid, name, _ in users:
            is_base = (
                (role == "admin" and uid in config.ADMIN_CHAT_ID) or
                (role == "manager" and uid in config.MANAGER_CHAT_ID) or
                (role == "tp" and uid in config.TP_CHAT_ID)
            )
            mark = " (встроенный)" if is_base else ""
            text += f"• <b>{name}</b> — <code>{uid}</code>{mark}\n"

        bot.send_message(call.message.chat.id, text)

# Добавление сотрудника — шаг 1 (имя)
def process_new_user_name(bot, message):
    if message.text and message.text.lower() == "назад":
        return admin_panel(bot, message)

    name = message.text.strip() if message.text else ""
    if not name:
        return bot.send_message(message.chat.id, "⚠ Имя не может быть пустым.")

    admin_workflow[message.from_user.id] = {"name": name}
    bot.send_message(message.chat.id, f'''🔢 Напишите <b>id Telegram профиля</b> администратора
    Чтобы его узнать, <b>целевой</b> пользователь должен написать боту <b>IDBot</b> @myidbot в личные сообщения команду <code>/getid</code>''')
    bot.register_next_step_handler(message, lambda m: process_new_user_id(bot, m))

# Добавление сотрудника — шаг 2 (ID)
def process_new_user_id(bot, message):
    if message.text and message.text.lower() == "назад":
        return admin_panel(bot, message)

    try:
        user_id = int(message.text.strip())
        if user_id <= 0:
            raise ValueError
        admin_workflow[message.from_user.id]["id"] = user_id
        bot.send_message(message.chat.id, "📌 Введите роль: admin, manager или tp")
        bot.register_next_step_handler(message, lambda m: process_new_user_role(bot, m))
    except (ValueError, AttributeError):
        bot.send_message(message.chat.id, "⚠ Неверный формат ID. Введите положительное число.")

# Добавление сотрудника — шаг 3 (роль)
def process_new_user_role(bot, message):
    if message.text and message.text.lower() == "назад":
        return admin_panel(bot, message)

    role = message.text.strip().lower() if message.text else ""
    if role not in ["admin", "manager", "tp"]:
        return bot.send_message(message.chat.id, "⚠ Неверная роль. Введите: admin, manager или tp")

    info = admin_workflow.get(message.from_user.id, {})
    user_id = info.get("id")
    name = info.get("name")
    key = info.get("key") if role != "admin" else None

    db.add_user(user_id, name, role, key)
    bot.send_message(message.chat.id, f"✅ Сотрудник <b>{name}</b> с ролью <b>{role}</b> добавлен.")
    admin_panel(bot, message)
