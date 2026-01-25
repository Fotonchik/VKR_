# db/employees.py

import sqlite3
import config
from typing import Optional


# =========================
# CONNECTION
# =========================

def get_connection():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# TABLE INIT
# =========================

def init_table():
    """
    Создание таблицы сотрудников
    """
    with get_connection() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            full_name TEXT,
            employee_code TEXT UNIQUE,
            role TEXT NOT NULL CHECK(role IN ('admin','manager','operator')),
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()


# =========================
# BOOTSTRAP ADMIN
# =========================

def create_admin_if_not_exists(user_id: int):
    """
    Создаёт администратора, если его нет
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM employees WHERE user_id = ?",
            (user_id,)
        ).fetchone()

        if row:
            return

        conn.execute("""
            INSERT INTO employees (user_id, full_name, role, is_active)
            VALUES (?, ?, 'admin', 1)
        """, (user_id, "System Admin"))
        conn.commit()

        print(f"[BOOTSTRAP] Admin created: {user_id}")


# =========================
# ROLE LOGIC (КЛЮЧЕВОЕ)
# =========================

def get_user_role(user_id: int) -> str:
    """
    Единственный источник правды о роли пользователя.
    Если нет записи — это client.
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT role FROM employees WHERE user_id = ? AND is_active = 1",
            (user_id,)
        ).fetchone()

    if row:
        return row["role"]

    return "client"


def is_staff(user_id: int) -> bool:
    return get_user_role(user_id) in ("admin", "manager", "operator")


def is_admin(user_id: int) -> bool:
    return get_user_role(user_id) == "admin"
