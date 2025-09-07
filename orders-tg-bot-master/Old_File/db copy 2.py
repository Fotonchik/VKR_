# admin_bot.py — телеграм-бот с функциональностью только для администраторов

import config
import db
import sqlite3
from sqlite3 import OperationalError, DatabaseError
import config

import datetime
import telebot
from telebot import types

import config
import db

import datetime
# Инициализация бота
bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode='HTML')

# Список ID с доступом
admin_ids = config.ADMIN_CHAT_ID[:]
DB_NAME = config.FILE_DB
# admin_bot.py — телеграм-бот с функциональностью для администратора, менеджера и оператора
DB_PATH = DB_NAME

# Инициализация бота
bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode='HTML')

# Список ID с доступом
admin_ids = config.ADMIN_CHAT_ID[:]

def connect_db():
    return sqlite3.connect(DB_NAME)

def ensure_and_get_users():
    try:
        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'manager', 'tp'))
            )
        ''')
        conn.commit()

        cursor.execute("SELECT user_id, name, role FROM users")
        users = cursor.fetchall()

        return users
    except Exception as e:
        print(f"❌ Ошибка базы данных: {e}")
        return []

# def add_user(user_id, name, role,  key=None):
#     try:
#         if not name or not isinstance(user_id, int) or role not in ['admin', 'manager', 'tp']:
#             raise ValueError("Некорректные данные для добавления пользователя")

#         conn = connect_db()
#         cursor = conn.cursor()

#         cursor.execute("INSERT OR REPLACE INTO users (id, name, role, key) VALUES (?, ?, ?,?)", (user_id, name, role, key))
#         conn.commit()
#         conn.close()
#     except Exception as e:
        print(f"❌ Ошибка при добавлении пользователя: {e}")
def add_user(user_id, name, role, key=None):
    try:
        if not name or not isinstance(user_id, int) or role not in ['admin', 'manager', 'tp']:
            raise ValueError("Некорректные данные для добавления пользователя")
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (user_id, name, role, key)
                VALUES (?, ?, ?, ?)
            ''', (user_id, name, role, key))
            conn.commit()
    except Exception as e:
        print(f"❌ Ошибка при добавлении пользователя: {e}")

def delete_user(user_id):
    try:
        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка при удалении пользователя: {e}")

def update_user_name(user_id, new_name):
    try:
        if not new_name:
            raise ValueError("Имя не может быть пустым")

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("UPDATE users SET name = ? WHERE user_id = ?", (new_name, user_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка при обновлении имени: {e}")
        
# Получение списка пользователей с ролями
users_from_db = db.ensure_and_get_users()
role_dict = {"admin": [], "manager": [], "tp": []}
for uid, name, role in users_from_db:
    role_dict[role].append(uid)
    if role == "admin" and uid not in admin_ids:
        admin_ids.append(uid)

# Временное хранилище этапов добавления/редактирования/удаления
admin_workflow = {}

# Проверка роли
def has_role(user_id, roles):
    return any(user_id in role_dict.get(r, []) for r in roles)

# Проверка доступа: либо роль, либо ID в конфиге
def has_access(user_id, roles):
    return user_id in config.ADMIN_CHAT_ID or has_role(user_id, roles)

# Команда: /admin — панель администратора
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not has_access(message.from_user.id, ["admin"]):
        return bot.send_message(message.chat.id, "❌ У вас нет доступа к административной панели.")

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🔧 Меню редактирования информации для клиента", callback_data="edit_client_info"))
    keyboard.add(
        types.InlineKeyboardButton("👤 Редактирование учетных записей", callback_data="edit_accounts"),
        types.InlineKeyboardButton("👀 Просмотр учетных записей", callback_data="list_staff_menu")
    )
    keyboard.add(types.InlineKeyboardButton("📁 Редактирование данных по клиенту", callback_data="edit_client_data"))
    keyboard.add(types.InlineKeyboardButton("🔄 Запросы от менеджмента", callback_data="manager_requests"))
    keyboard.add(types.InlineKeyboardButton("📌 Просмотр заявок", callback_data="view_requests"))
    bot.send_message(message.chat.id, "⚖ Административная панель:", reply_markup=keyboard)

# Добавление сотрудника — шаг 1 (имя)
def process_new_user_name(message):
    if message.text.lower() == "назад":
        return admin_panel(message)

    name = message.text.strip()
    if not name:
        return bot.send_message(message.chat.id, "⚠ Имя не может быть пустым.")

    admin_workflow[message.from_user.id] = {"name": name}
    bot.send_message(message.chat.id, "🔢 Теперь введите ID нового сотрудника или 'назад'")
    bot.register_next_step_handler(message, process_new_user_id)

# Добавление сотрудника — шаг 2 (ID)
def process_new_user_id(message):
    if message.text.lower() == "назад":
        return admin_panel(message)

    try:
        user_id = int(message.text.strip())
        if user_id <= 0:
            raise ValueError
        admin_workflow[message.from_user.id]["id"] = user_id
        bot.send_message(message.chat.id, "📌 Введите роль сотрудника: admin, manager или tp")
        bot.register_next_step_handler(message, process_new_user_role_with_key_check)
    except ValueError:
        bot.send_message(message.chat.id, "⚠ Неверный формат ID. Введите положительное число.")

# Добавление сотрудника — шаг 3 (роль)
def process_new_user_role(message):
    if message.text.lower() == "назад":
        return admin_panel(message)

    role = message.text.strip().lower()
    if role not in ["admin", "manager", "tp"]:
        return bot.send_message(message.chat.id, "⚠ Неверная роль. Введите: admin, manager или tp")

    info = admin_workflow.get(message.from_user.id, {})
    user_id = info.get("user_id")
    name = info.get("name")
    key = info.get("key") if role != "admin" else None

    db.add_user(user_id, name, role, key)
    bot.send_message(message.chat.id, f"✅ Сотрудник <b>{name}</b> с ролью <b>{role}</b> добавлен.")
    admin_panel(message)

# Удаление администратора
def process_delete_admin(message):
    if message.text.lower() == "назад":
        return admin_panel(message)

    try:
        admin_id = int(message.text.strip())
        db.delete_user(admin_id)
        bot.send_message(message.chat.id, f"❌ Администратор с ID <code>{admin_id}</code> удалён.")
    except ValueError:
        bot.send_message(message.chat.id, "⚠ Неверный формат ID. Введите число.")

# Редактирование имени администратора — шаг 1
def process_edit_admin_id(message):
    if message.text.lower() == "назад":
        return admin_panel(message)

    try:
        admin_id = int(message.text.strip())
        admin_workflow[message.from_user.id] = {"edit_id": admin_id}
        bot.send_message(message.chat.id, "📝 Введите новое имя администратора или 'назад'")
        bot.register_next_step_handler(message, process_edit_admin_name)
    except ValueError:
        bot.send_message(message.chat.id, "⚠ Неверный формат ID. Введите число.")

# Редактирование имени администратора — шаг 2
def process_edit_admin_name(message):
    if message.text.lower() == "назад":
        return admin_panel(message)

    new_name = message.text.strip()
    if not new_name:
        return bot.send_message(message.chat.id, "⚠ Имя не может быть пустым.")

    admin_id = admin_workflow.get(message.from_user.id, {}).get("edit_id")
    if admin_id:
        db.update_user_name(admin_id, new_name)
        bot.send_message(message.chat.id, f"✅ Имя администратора обновлено на <b>{new_name}</b>.")
    else:
        bot.send_message(message.chat.id, "⚠ Произошла ошибка. Попробуйте снова.")

# Запуск бота
print("✅ Админ-бот запущен")
bot.infinity_polling()



# TODO cgbcjr cjnhelybrjd b rkbtynjd yt njr flvbyjd  e dct[ htlfrn b elfktybt ]
# Z ljk;yf ,snm d cgbcrt flvbyjd

# def init_db():
#     with sqlite3.connect(DB_PATH) as conn:
#         cursor = conn.cursor()

#         # Пересоздаём таблицу users
#         cursor.execute("DROP TABLE IF EXISTS users")
#         cursor.execute('''
#             CREATE TABLE users (
#                 user_id INTEGER PRIMARY KEY,
#                 name TEXT NOT NULL,
#                 role TEXT CHECK(role IN ('admin', 'manager', 'tp')) NOT NULL,
#                 key TEXT
#             )
#         ''')

#         # Таблица для запросов от менеджеров
#         cursor.execute('''
#             CREATE TABLE IF NOT EXISTS manager_requests (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 manager_id INTEGER NOT NULL,
#                 content TEXT NOT NULL,
#                 status TEXT CHECK(status IN ('pending', 'approved', 'rejected')) DEFAULT 'pending',
#                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#             )
#         ''')
#         conn.commit()

# Получить всех сотрудников

# Получение уникального ключа сотрудника (если нужен)
def get_user_key(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT key FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        return row[0] if row else None

# Добавление запроса от менеджера
def add_manager_request(manager_id, content):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO manager_requests (manager_id, content)
            VALUES (?, ?)
        ''', (manager_id, content))
        conn.commit()

# Получение всех запросов от менеджеров
def get_all_manager_requests():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, manager_id, content, status, created_at FROM manager_requests')
        return cursor.fetchall()


def process_new_user_role_with_key_check(message):
    if message.text.lower() == "назад":
        return admin_panel(message)

    role = message.text.strip().lower()
    if role not in ["admin", "manager", "tp"]:
        return bot.send_message(message.chat.id, "⚠ Неверная роль. Введите: admin, manager или tp")

    admin_workflow[message.from_user.id]["role"] = role

    if role == "admin":
        return process_new_user_role(message)  # перейти сразу к добавлению

    # Для manager или tp — запрос ключа
    bot.send_message(
        message.chat.id,
        "🔐 Введите уникальный ключ или отправьте 'сгенерировать', чтобы использовать сгенерированный:"
    )
    bot.register_next_step_handler(message, process_user_key_input)

def process_user_key_input(message):
    if message.text.lower() == "назад":
        return admin_panel(message)

    key = admin_workflow[message.from_user.id].get("key")  # сгенерированный
    if message.text.lower() != "сгенерировать":
        key = message.text.strip()

    admin_workflow[message.from_user.id]["key"] = key

    # Проксируем к финальному шагу
    proxy_msg = message
    proxy_msg.text = admin_workflow[message.from_user.id]["role"]
    process_new_user_role(proxy_msg)



# Обновление статуса запроса от менеджера

def update_request_status(request_id, new_status):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE manager_requests
            SET status = ?
            WHERE id = ?
        ''', (new_status, request_id))
        conn.commit()
# db.py — логика работы с базой данных


# Инициализация базы данных (пересоздание users с правильными полями)
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Пересоздаём таблицу users
        cursor.execute("DROP TABLE IF EXISTS users")
        cursor.execute('''
            CREATE TABLE users (
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT CHECK(role IN ('admin', 'manager', 'tp')) NOT NULL,
                key TEXT
            )
        ''')

        # Таблица для запросов от менеджеров
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS manager_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manager_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                status TEXT CHECK(status IN ('pending', 'approved', 'rejected')) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

# Получить всех сотрудников

def ensure_and_get_users():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, name, role FROM users")
        return cursor.fetchall()

# Добавление сотрудника

def add_user(user_id, name, role, key=None):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, name, role, key)
            VALUES (?, ?, ?, ?)
        ''', (user_id, name, role, key))
        conn.commit()

# Удаление сотрудника

def delete_user(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()

# Обновление имени сотрудника

def update_user_name(user_id, new_name):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET name = ? WHERE user_id = ?", (new_name, user_id))
        conn.commit()

# Обновление ключа сотрудника (для manager/tp)

def update_user_key(user_id, new_key):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET key = ? WHERE user_id = ?", (new_key, user_id))
        conn.commit()

# Обновление ID сотрудника (изменение user_id)

def update_user_id(old_id, new_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET user_id = ? WHERE user_id = ?", (new_id, old_id))
        conn.commit()

# Обновление статуса запроса от менеджера

def update_request_status(request_id, new_status):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE manager_requests
            SET status = ?
            WHERE id = ?
        ''', (new_status, request_id))
        conn.commit()

# Обработчик кнопок панели
@bot.callback_query_handler(func=lambda call: True)
def admin_callbacks(call):
    if not has_access(call.from_user.id, ["admin"]):
        return bot.answer_callback_query(call.id, "❌ Нет доступа")

    if call.data == "view_orders":
        bot.send_message(call.message.chat.id, "✍ Здесь будут отображены заказы (заглушка)")

    elif call.data == "add_user":
        bot.send_message(call.message.chat.id, "📝 Введите имя нового сотрудника или 'назад'")
        bot.register_next_step_handler(call.message, process_new_user_name)

    elif call.data == "list_admins":
        users = db.ensure_and_get_users()
        admins = [u for u in users if u[2] == "admin"]
        if not admins:
            bot.send_message(call.message.chat.id, "⚠ Администраторы не найдены.")
        else:
            text = "👥 <b>Список администраторов:</b>\n\n"
            for uid, name, role in admins:
                text += f"• <b>{name}</b> — <code>{uid}</code>\n"
            bot.send_message(call.message.chat.id, text)

    elif call.data == "delete_admin":
        bot.send_message(call.message.chat.id, "❌ Введите ID администратора для удаления или 'назад'")
        bot.register_next_step_handler(call.message, process_delete_admin)

    elif call.data == "edit_admin":
        bot.send_message(call.message.chat.id, "✏ Введите ID администратора, чьё имя хотите изменить, или 'назад'")
        bot.register_next_step_handler(call.message, process_edit_admin_id)
