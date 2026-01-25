# core/audit.py

import sqlite3
import json
import config
from datetime import datetime

DB = config.DB_PATH


# =========================================================
# INIT
# =========================================================

def init_audit_table():
    with sqlite3.connect(DB) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            entity TEXT NOT NULL,
            entity_id TEXT,
            old_value TEXT,
            new_value TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()


# =========================================================
# LOGGING
# =========================================================

def log_action(
    user_id: int,
    action: str,
    entity: str,
    entity_id: str | int | None = None,
    old_value: dict | None = None,
    new_value: dict | None = None
):
    """
    Записывает действие в audit_log
    """
    with sqlite3.connect(DB) as conn:
        conn.execute("""
        INSERT INTO audit_log (
            user_id, action, entity, entity_id,
            old_value, new_value, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            action,
            entity,
            str(entity_id) if entity_id is not None else None,
            json.dumps(old_value, ensure_ascii=False) if old_value else None,
            json.dumps(new_value, ensure_ascii=False) if new_value else None,
            datetime.utcnow().isoformat()
        ))
        conn.commit()


# =========================================================
# HELPERS
# =========================================================

def log_create(user_id, entity, entity_id, new_value=None):
    log_action(
        user_id=user_id,
        action="create",
        entity=entity,
        entity_id=entity_id,
        new_value=new_value
    )


def log_update(user_id, entity, entity_id, old_value, new_value):
    log_action(
        user_id=user_id,
        action="update",
        entity=entity,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value
    )


def log_delete(user_id, entity, entity_id, old_value=None):
    log_action(
        user_id=user_id,
        action="delete",
        entity=entity,
        entity_id=entity_id,
        old_value=old_value
    )


# =========================================================
# QUERY (для админа)
# =========================================================

def get_audit_logs(limit=100):
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("""
        SELECT * FROM audit_log
        ORDER BY created_at DESC
        LIMIT ?
        """, (limit,)).fetchall()
# core/audit.py

import sqlite3
import json
import config
from datetime import datetime

DB = config.DB_PATH


# =========================================================
# INIT
# =========================================================

def init_audit_table():
    with sqlite3.connect(DB) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            entity TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()


# =========================================================
# HELPERS
# =========================================================

def _json(data):
    if data is None:
        return None
    return json.dumps(data, ensure_ascii=False)


# =========================================================
# LOGGING
# =========================================================

def log_create(*, user_id, entity, entity_id, new_value):
    _insert(
        user_id=user_id,
        entity=entity,
        entity_id=entity_id,
        action="create",
        old_value=None,
        new_value=new_value
    )


def log_update(*, user_id, entity, entity_id, old_value, new_value):
    _insert(
        user_id=user_id,
        entity=entity,
        entity_id=entity_id,
        action="update",
        old_value=old_value,
        new_value=new_value
    )


def log_delete(*, user_id, entity, entity_id, old_value):
    _insert(
        user_id=user_id,
        entity=entity,
        entity_id=entity_id,
        action="delete",
        old_value=old_value,
        new_value=None
    )


def _insert(*, user_id, entity, entity_id, action, old_value, new_value):
    with sqlite3.connect(DB) as conn:
        conn.execute("""
        INSERT INTO audit_log (
            user_id, entity, entity_id,
            action, old_value, new_value
        ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            entity,
            entity_id,
            action,
            _json(old_value),
            _json(new_value)
        ))
        conn.commit()
