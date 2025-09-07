# # admin_bot.py — телеграм-бот с функциональностью для администратора, менеджера и оператора

# import datetime
# import telebot
# from telebot import types

# import config
# import db

# # Инициализация бота
# bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode='HTML')

# # Список ID с доступом
# admin_ids = config.ADMIN_CHAT_ID[:]
# manager_ids = config.MANAGER_CHAT_ID[:]
# tp_ids = config.TP_CHAT_ID[:]

# # Получение списка сотрудников с ролями
# users_from_db = db.ensure_and_get_users()
# role_dict = {"admin": [], "manager": [], "tp": []}
# for uid, name, role in users_from_db:
#     role_dict[role].append(uid)
#     if role == "admin" and uid not in admin_ids:
#         admin_ids.append(uid)
#     if role == "manager" and uid not in manager_ids:
#         manager_ids.append(uid)
#     if role == "tp" and uid not in tp_ids:
#         tp_ids.append(uid)

# # Временное хранилище этапов добавления/редактирования/удаления
# admin_workflow = {}

# # Проверка роли
# def has_role(user_id, roles):
#     return any(user_id in role_dict.get(r, []) for r in roles)

# # Проверка доступа: либо роль, либо ID в конфиге
# def has_access(user_id, roles):
#     if "admin" in roles and user_id in config.ADMIN_CHAT_ID:
#         return True
#     if "manager" in roles and user_id in config.MANAGER_CHAT_ID:
#         return True
#     if "tp" in roles and user_id in config.TP_CHAT_ID:
#         return True
#     return has_role(user_id, roles)

# # Команда: /admin — панель администратора
# @bot.message_handler(commands=['admin'])
# def admin_panel(message):
#     if not has_access(message.from_user.id, ["admin"]):
#         return bot.send_message(message.chat.id, "❌ У вас нет доступа к административной панели.")

#     keyboard = types.InlineKeyboardMarkup()
#     keyboard.add(types.InlineKeyboardButton("✍ Просмотр заказов", callback_data="view_orders"))
#     keyboard.add(types.InlineKeyboardButton("➕ Добавить сотрудника", callback_data="add_user"))

#     if any(role_dict.values()):
#         keyboard.add(types.InlineKeyboardButton("👥 Список сотрудников", callback_data="list_staff"))

#     bot.send_message(message.chat.id, "⚖ Административная панель:", reply_markup=keyboard)

# # Обработчик кнопок панели
# @bot.callback_query_handler(func=lambda call: True)
# def admin_callbacks(call):
#     if not has_access(call.from_user.id, ["admin"]):
#         return bot.answer_callback_query(call.id, "❌ Нет доступа")

#     if call.data == "view_orders":
#         bot.send_message(call.message.chat.id, "✍ Здесь будут отображены заказы (заглушка)")

#     elif call.data == "add_user":
#         bot.send_message(call.message.chat.id, "📝 Введите имя нового сотрудника или 'назад'")
#         bot.register_next_step_handler(call.message, process_new_user_name)

#     elif call.data == "list_staff":
#         users = db.ensure_and_get_users()
#         if not users:
#             return bot.send_message(call.message.chat.id, "⚠ Сотрудники не найдены.")

#         grouped = {"admin": [], "manager": [], "tp": []}
#         for uid, name, role in users:
#             grouped[role].append((uid, name))

#         text = "👥 <b>Список сотрудников:</b>\n\n"
#         for role, display in {"admin": "Администраторы", "manager": "Менеджеры", "tp": "Операторы"}.items():
#             if grouped[role]:
#                 text += f"<b>{display}:</b>\n"
#                 for uid, name in grouped[role]:
#                     is_base_admin = uid in config.ADMIN_CHAT_ID if role == "admin" else False
#                     mark = " (встроенный)" if is_base_admin else ""
#                     text += f"• <b>{name}</b> — <code>{uid}</code>{mark}\n"
#                 text += "\n"

#         bot.send_message(call.message.chat.id, text)

# # Добавление сотрудника — шаг 1 (имя)
# def process_new_user_name(message):
#     if message.text.lower() == "назад":
#         return admin_panel(message)

#     name = message.text.strip()
#     if not name:
#         return bot.send_message(message.chat.id, "⚠ Имя не может быть пустым.")

#     admin_workflow[message.from_user.id] = {"name": name}
#     bot.send_message(message.chat.id, "🔢 Теперь введите ID нового сотрудника или 'назад'")
#     bot.register_next_step_handler(message, process_new_user_id)

# # Добавление сотрудника — шаг 2 (ID)
# def process_new_user_id(message):
#     if message.text.lower() == "назад":
#         return admin_panel(message)

#     try:
#         user_id = int(message.text.strip())
#         if user_id <= 0:
#             raise ValueError
#         admin_workflow[message.from_user.id]["id"] = user_id
#         bot.send_message(message.chat.id, "📌 Введите роль: admin, manager или tp")
#         bot.register_next_step_handler(message, process_new_user_role)
#     except ValueError:
#         bot.send_message(message.chat.id, "⚠ Неверный формат ID. Введите положительное число.")

# # Добавление сотрудника — шаг 3 (роль)
# def process_new_user_role(message):
#     if message.text.lower() == "назад":
#         return admin_panel(message)

#     role = message.text.strip().lower()
#     if role not in ["admin", "manager", "tp"]:
#         return bot.send_message(message.chat.id, "⚠ Неверная роль. Введите: admin, manager или tp")

#     info = admin_workflow.get(message.from_user.id, {})
#     user_id = info.get("id")
#     name = info.get("name")

#     db.add_user(user_id, name, role)
#     bot.send_message(message.chat.id, f"✅ Сотрудник <b>{name}</b> с ролью <b>{role}</b> добавлен.")
#     admin_panel(message)

# # Запуск бота
# print("✅ Админ-бот запущен")
# bot.infinity_polling()
