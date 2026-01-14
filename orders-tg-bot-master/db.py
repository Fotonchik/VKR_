# db.py — работа с базой данных пользователей и заказов

import sqlite3
import config
import os

DB_NAME = config.FILE_DB

def connect_db():
    """Создает подключение к базе данных"""
    return sqlite3.connect(DB_NAME)

def check_database():
    """Проверяет и создает необходимые таблицы"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        # Таблица пользователей (для клиентов и сотрудников)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT CHECK(role IN ('admin', 'manager', 'tp', 'client', NULL))
            )
        ''')
        
        # Таблица товаров
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                price REAL,
                description TEXT
            )
        ''')
        
        # Таблица заказов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total REAL,
                status INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # Таблица элементов заказа
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                quantity INTEGER DEFAULT 1,
                price REAL,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка при проверке базы данных: {e}")

def ensure_and_get_users():
    """Создает таблицу пользователей если нужно и возвращает всех пользователей"""
    try:
        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT CHECK(role IN ('admin', 'manager', 'tp', 'client', NULL))
            )
        ''')
        conn.commit()

        cursor.execute("SELECT user_id, name, role FROM users WHERE role IN ('admin', 'manager', 'tp')")
        users = cursor.fetchall()

        conn.close()
        return users
    except Exception as e:
        print(f"❌ Ошибка базы данных: {e}")
        return []

def has_access(user_id, roles):
    """Проверяет доступ пользователя по роли"""
    if user_id in config.ADMIN_CHAT_ID and 'admin' in roles:
        return True
    
    try:
        conn = connect_db()
        cursor = conn.cursor()
        placeholders = ','.join(['?'] * len(roles))
        cursor.execute(f"SELECT 1 FROM users WHERE user_id = ? AND role IN ({placeholders})", 
                      [user_id] + list(roles))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except Exception as e:
        print(f"❌ Ошибка при проверке доступа: {e}")
        return False

def user_exists(user_id):
    """Проверяет существование пользователя"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except Exception as e:
        print(f"❌ Ошибка при проверке пользователя: {e}")
        return False

def add_user(user_id, name, role=None, key=None):
    """Добавляет пользователя (клиента или сотрудника)"""
    try:
        if not name or not isinstance(user_id, int):
            raise ValueError("Некорректные данные для добавления пользователя")

        conn = connect_db()
        cursor = conn.cursor()
        
        # Если роль не указана, это клиент
        if role is None:
            role = 'client'
        elif role not in ['admin', 'manager', 'tp', 'client']:
            role = 'client'
        
        cursor.execute("INSERT OR REPLACE INTO users (user_id, name, role) VALUES (?, ?, ?)", 
                      (user_id, name, role))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка при добавлении пользователя: {e}")

def delete_user(user_id):
    """Удаляет пользователя"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка при удалении пользователя: {e}")

def update_user_name(user_id, new_name):
    """Обновляет имя пользователя"""
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

def get_admins():
    """Возвращает список администраторов"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, name FROM users WHERE role = 'admin'")
        admins = cursor.fetchall()
        conn.close()
        return admins
    except Exception as e:
        print(f"❌ Ошибка при получении администраторов: {e}")
        return []

def get_products():
    """Возвращает список всех товаров"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, price, description FROM products")
        products = cursor.fetchall()
        conn.close()
        return products
    except Exception as e:
        print(f"❌ Ошибка при получении товаров: {e}")
        return []

def get_product_by_name(name):
    """Возвращает товар по имени"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, price, description FROM products WHERE name = ?", (name,))
        product = cursor.fetchone()
        conn.close()
        return product
    except Exception as e:
        print(f"❌ Ошибка при получении товара: {e}")
        return None

def add_order(user_id, cart):
    """Добавляет заказ и возвращает его ID"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        # Подсчет общей суммы
        total = sum(item[2] if len(item) > 2 else 0 for item in cart if item)
        
        # Добавление заказа
        cursor.execute("INSERT INTO orders (user_id, total) VALUES (?, ?)", (user_id, total))
        order_id = cursor.lastrowid
        
        # Добавление элементов заказа
        for item in cart:
            if item and len(item) >= 2:
                product_name = item[1] if isinstance(item, (list, tuple)) else str(item)
                price = item[2] if len(item) > 2 else 0
                quantity = 1
                cursor.execute("INSERT INTO order_items (order_id, product_name, quantity, price) VALUES (?, ?, ?, ?)",
                             (order_id, product_name, quantity, price))
        
        conn.commit()
        conn.close()
        return order_id
    except Exception as e:
        print(f"❌ Ошибка при добавлении заказа: {e}")
        return None

def get_user_orders(user_id):
    """Возвращает список заказов пользователя"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, created_at, total FROM orders WHERE user_id = ? ORDER BY created_at DESC", 
                      (user_id,))
        orders = cursor.fetchall()
        conn.close()
        return orders
    except Exception as e:
        print(f"❌ Ошибка при получении заказов: {e}")
        return []
