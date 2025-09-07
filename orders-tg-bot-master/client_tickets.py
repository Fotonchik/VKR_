# client_tickets.py — работа пользователя с заявками 

import sqlite3
from datetime import datetime
import logging

DB_PATH = 'orders.db'

# === Логирование ошибок ===
logging.basicConfig(level=logging.INFO, filename="py_log.log",filemode="w",
                    format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# === Инициализация таблицы заявок от клиентов ===
def init_client_ticket_db():
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS client_tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT CHECK(status IN ('open', 'active', 'closed')) DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    operator_id INTEGER DEFAULT NULL,
                    resolution TEXT DEFAULT NULL
                )
            ''')
            conn.commit()
    except Exception as e:
        logger.error(f"Ошибка инициализации таблицы client_tickets: {e}")

# === Проверка: не является ли пользователь сотрудником ===
def is_restricted_user(user_id):
    import config
    import db
    if user_id in config.ADMIN_CHAT_ID or db.has_access(user_id, ['admin']):
        return True
    if user_id in config.MANAGER_CHAT_ID or db.has_access(user_id, ['manager']):
        return True
    if user_id in config.TP_CHAT_ID or db.has_access(user_id, ['tp']):
        return True
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row and row[0] in ("admin", "manager", "tp"):
                return True
    except Exception as e:
        logger.error(f"Ошибка при проверке роли пользователя: {e}")
    return False


# === Добавление новой заявки ===
def add_ticket(user_id, title, description):
    from telebot import TeleBot
    from config import BOT_TOKEN
    bot = TeleBot(BOT_TOKEN, parse_mode="HTML")

    if is_restricted_user(user_id):
        bot.send_message(user_id, "🚫 Вы не можете создавать заявки, так как вы зарегистрированы как сотрудник.")
        logger.warning(f"Пользователь {user_id} с ролью сотрудника не может создавать клиентские заявки")
        return
    try:
        if not title:
            raise ValueError("Заголовок заявки не может быть пустым")
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO client_tickets (user_id, title, description)
                VALUES (?, ?, ?)
            ''', (user_id, title, description))
            conn.commit()
    except Exception as e:
        logger.error(f"Ошибка при добавлении заявки: {e}")

# === Получение всех заявок клиента ===
def get_user_tickets(user_id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM client_tickets
                WHERE user_id = ?
                ORDER BY created_at DESC
            ''', (user_id,))
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Ошибка при получении заявок пользователя: {e}")
        return []

# === Получение заявки по ID ===
def get_ticket_by_id(ticket_id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM client_tickets WHERE id = ?
            ''', (ticket_id,))
            return cursor.fetchone()
    except Exception as e:
        logger.error(f"Ошибка при получении заявки по ID: {e}")
        return None

# === Обновление статуса заявки ===
def update_ticket_status(ticket_id, new_status):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE client_tickets
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_status, ticket_id))
            conn.commit()
    except Exception as e:
        logger.error(f"Ошибка при обновлении статуса заявки: {e}")

# === Закрытие заявки с комментарием ===
def close_ticket(ticket_id, resolution_text):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE client_tickets
                SET status = 'closed', resolution = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (resolution_text, ticket_id))
            conn.commit()
    except Exception as e:
        logger.error(f"Ошибка при закрытии заявки: {e}")

# === Получение всех заявок клиента по статусу ===
def get_user_tickets_by_status(user_id, status):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM client_tickets
                WHERE user_id = ? AND status = ?
                ORDER BY created_at DESC
            ''', (user_id, status))
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Ошибка при получении заявок по статусу: {e}")
        return []

print("📂 Модуль client_tickets готов к работе")
