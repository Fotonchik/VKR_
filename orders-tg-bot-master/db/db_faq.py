# db/db_faq.py

import sqlite3
import config
from core.audit import log_create, log_update, log_delete

DB = config.DB_PATH


# =========================================================
# INIT
# =========================================================

def init_faq_table():
    with sqlite3.connect(DB) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS faq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            display_order INTEGER DEFAULT 0,
            created_by INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
        """)
        conn.commit()


# =========================================================
# CRUD
# =========================================================

def add_faq(
    *,
    user_id: int,
    title: str,
    content: str,
    category: str = "general",
    display_order: int = 0
):
    with sqlite3.connect(DB) as conn:
        cur = conn.execute("""
        INSERT INTO faq (
            title, content, category,
            display_order, created_by
        ) VALUES (?, ?, ?, ?, ?)
        """, (
            title,
            content,
            category,
            display_order,
            user_id
        ))
        faq_id = cur.lastrowid
        conn.commit()

    log_create(
        user_id=user_id,
        entity="faq",
        entity_id=faq_id,
        new_value={
            "title": title,
            "category": category,
            "display_order": display_order
        }
    )

    return faq_id


def update_faq(
    *,
    user_id: int,
    faq_id: int,
    title: str | None = None,
    content: str | None = None,
    category: str | None = None,
    display_order: int | None = None
):
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        faq = conn.execute(
            "SELECT * FROM faq WHERE id=?",
            (faq_id,)
        ).fetchone()

        if not faq:
            raise ValueError("FAQ не найден")

        old_data = dict(faq)

        fields = []
        values = []

        if title is not None:
            fields.append("title=?")
            values.append(title)

        if content is not None:
            fields.append("content=?")
            values.append(content)

        if category is not None:
            fields.append("category=?")
            values.append(category)

        if display_order is not None:
            fields.append("display_order=?")
            values.append(display_order)

        if not fields:
            return

        values.append(faq_id)

        conn.execute(
            f"UPDATE faq SET {', '.join(fields)} WHERE id=?",
            values
        )
        conn.commit()

    log_update(
        user_id=user_id,
        entity="faq",
        entity_id=faq_id,
        old_value=old_data,
        new_value={
            "title": title,
            "content": content,
            "category": category,
            "display_order": display_order
        }
    )


def set_faq_active(
    *,
    user_id: int,
    faq_id: int,
    is_active: bool
):
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        faq = conn.execute(
            "SELECT * FROM faq WHERE id=?",
            (faq_id,)
        ).fetchone()

        if not faq:
            raise ValueError("FAQ не найден")

        old_data = dict(faq)

        conn.execute(
            "UPDATE faq SET is_active=? WHERE id=?",
            (1 if is_active else 0, faq_id)
        )
        conn.commit()

    log_update(
        user_id=user_id,
        entity="faq",
        entity_id=faq_id,
        old_value=old_data,
        new_value={"is_active": is_active}
    )


def delete_faq(user_id: int, faq_id: int):
    """
    Полное удаление (использовать редко, в основном soft delete)
    """
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        faq = conn.execute(
            "SELECT * FROM faq WHERE id=?",
            (faq_id,)
        ).fetchone()

        if not faq:
            raise ValueError("FAQ не найден")

        conn.execute(
            "DELETE FROM faq WHERE id=?",
            (faq_id,)
        )
        conn.commit()

    log_delete(
        user_id=user_id,
        entity="faq",
        entity_id=faq_id,
        old_value=dict(faq)
    )


# =========================================================
# QUERIES
# =========================================================

def get_all_faq(include_inactive=False):
    query = "SELECT * FROM faq"
    if not include_inactive:
        query += " WHERE is_active=1"

    query += " ORDER BY display_order, created_at"

    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(query).fetchall()


def get_faq_by_id(faq_id: int):
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            "SELECT * FROM faq WHERE id=?",
            (faq_id,)
        ).fetchone()


def get_faq_for_clients():
    """
    Только активные FAQ, отсортированные
    """
    return get_all_faq(include_inactive=False)
