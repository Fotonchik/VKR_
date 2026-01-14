# db_tickets.py — работа с заявками, клиентами и комментариями

import sqlite3
import config

DB_PATH = config.FILE_DB


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                status TEXT,
                operator_id INTEGER,
                client_id INTEGER,
                reason TEXT
            )
        """)
        # можно добавить clients, comments и т.д. тоже здесь
        conn.commit()



def init_ticket_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Таблица клиентов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                info TEXT
            )
        ''')

        # Таблица заявок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT CHECK(status IN ('open', 'active', 'closed', 'to_manager')) NOT NULL DEFAULT 'open',
                operator_id INTEGER,
                client_id INTEGER NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients(id)
            )
        ''')
        
        # Добавляем поля created_at и updated_at, если их нет
        try:
            cursor.execute("ALTER TABLE tickets ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE tickets ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE tickets ADD COLUMN description TEXT")
        except:
            pass

        # Таблица комментариев к заявкам
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ticket_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                author_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_id) REFERENCES tickets(id)
            )
        ''')

        conn.commit()

# === Операции ===

def get_tickets_by_status(operator_id, status):
    """Получает заявки по статусу. Если operator_id=None, возвращает все заявки с этим статусом"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if operator_id is None:
            cursor.execute("""
                SELECT * FROM tickets
                WHERE status = ?
            """, (status,))
        else:
            cursor.execute("""
                SELECT * FROM tickets
                WHERE status = ? AND operator_id = ?
            """, (status, operator_id))
        return cursor.fetchall()

def get_ticket_by_id(ticket_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
        return cursor.fetchone()

def get_users_by_role(role):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, name FROM users WHERE role = ?", (role,))
        return cursor.fetchall()

def update_client_name(client_id, new_name):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE clients SET name = ? WHERE id = ?", (new_name, client_id))
        conn.commit()

def get_tickets_by_date_range(start_date, end_date):
    """Получает заявки по диапазону дат (заглушка, так как в таблице нет поля даты)"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets")
        return cursor.fetchall()

def update_user_name(user_id, new_name):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET name = ? WHERE user_id = ?", (new_name, user_id))
        conn.commit()

def has_user_role(user_id, role):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE user_id = ? AND role = ?", (user_id, role))
        return cursor.fetchone() is not None

def get_client_by_id(client_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
        return cursor.fetchone()

def update_client_info(client_id, new_info):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE clients SET info = ? WHERE id = ?", (new_info, client_id))
        conn.commit()

def add_ticket_comment(ticket_id, author_id, text):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ticket_comments (ticket_id, author_id, text)
            VALUES (?, ?, ?)
        """, (ticket_id, author_id, text))
        conn.commit()

def get_ticket_comments(ticket_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ticket_comments WHERE ticket_id = ? ORDER BY created_at ASC", (ticket_id,))
        return cursor.fetchall()

def transfer_ticket_to_manager(ticket_id, reason):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tickets SET status = 'to_manager', reason = ?
            WHERE id = ?
        """, (reason, ticket_id))
        conn.commit()

def close_ticket(ticket_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE tickets SET status = 'closed' WHERE id = ?", (ticket_id,))
        conn.commit()

def update_ticket_status(ticket_id, new_status):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE tickets SET status = ? WHERE id = ?", (new_status, ticket_id))
        conn.commit()

# Новый функционал: изменение комментариев (если потребуется)
def update_ticket_comment(comment_id, new_text):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE ticket_comments SET text = ? WHERE id = ?
        """, (new_text, comment_id))
        conn.commit()

# === Функции создания заявок ===

def create_or_get_client(client_id, client_name):
    """Создает клиента или возвращает существующего"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Проверяем, существует ли клиент
        cursor.execute("SELECT id FROM clients WHERE id = ?", (client_id,))
        if cursor.fetchone():
            # Обновляем имя, если изменилось
            cursor.execute("UPDATE clients SET name = ? WHERE id = ?", (client_name, client_id))
        else:
            # Создаем нового клиента
            cursor.execute("INSERT INTO clients (id, name) VALUES (?, ?)", (client_id, client_name))
        conn.commit()
    return client_id

def create_ticket_from_client(client_id, client_name, message_text):
    """Создает заявку от клиента"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Создаем или получаем клиента
        create_or_get_client(client_id, client_name)
        
        # Создаем заявку
        title = message_text[:100] if len(message_text) > 100 else message_text
        description = message_text
        
        cursor.execute("""
            INSERT INTO tickets (title, description, status, client_id, created_at, updated_at)
            VALUES (?, ?, 'open', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (title, description, client_id))
        ticket_id = cursor.lastrowid
        conn.commit()
    return ticket_id

def get_open_tickets():
    """Получает все открытые заявки (без оператора)"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM tickets 
            WHERE status = 'open' AND operator_id IS NULL
            ORDER BY created_at DESC
        """)
        return cursor.fetchall()

def assign_ticket_to_operator(ticket_id, operator_id):
    """Назначает заявку оператору и меняет статус на active"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tickets 
            SET operator_id = ?, status = 'active', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (operator_id, ticket_id))
        conn.commit()

def get_all_open_tickets():
    """Получает все открытые заявки (включая назначенные операторам)"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM tickets 
            WHERE status = 'open'
            ORDER BY created_at DESC
        """)
        return cursor.fetchall()
