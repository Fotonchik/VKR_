import sqlite3
import config

DB = config.DB_PATH


# =========================================================
# CONNECT
# =========================================================

def connect():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


# =========================================================
# INIT
# =========================================================

def init_db():
    with connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            role TEXT DEFAULT 'client',
            tg_username TEXT,
            tg_first_name TEXT,
            tg_last_name TEXT,
            full_name TEXT,
            phone TEXT,
            email TEXT,
            active_ticket_id INTEGER
        )
        """)
        conn.commit()


# =========================================================
# REGISTRATION
# =========================================================

def register_user(tg_user):
    with connect() as conn:
        exists = conn.execute(
            "SELECT 1 FROM users WHERE user_id=?",
            (tg_user.id,)
        ).fetchone()

        if exists:
            return

        conn.execute("""
        INSERT INTO users (
            user_id, role, tg_username,
            tg_first_name, tg_last_name
        ) VALUES (?, 'client', ?, ?, ?)
        """, (
            tg_user.id,
            tg_user.username,
            tg_user.first_name,
            tg_user.last_name
        ))
        conn.commit()


# =========================================================
# GETTERS
# =========================================================

def get_user(user_id):
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE user_id=?",
            (user_id,)
        ).fetchone()


def get_role(user_id):
    user = get_user(user_id)
    return user["role"] if user else None


def has_role(user_id, roles):
    return get_role(user_id) in roles


def get_all_clients():
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM users"
        ).fetchall()


# =========================================================
# ROLES
# =========================================================

def set_role(user_id, role):
    with connect() as conn:
        conn.execute(
            "UPDATE users SET role=? WHERE user_id=?",
            (role, user_id)
        )
        conn.commit()


# =========================================================
# ACTIVE TICKET
# =========================================================

def set_active_ticket(user_id, ticket_id):
    with connect() as conn:
        conn.execute(
            "UPDATE users SET active_ticket_id=? WHERE user_id=?",
            (ticket_id, user_id)
        )
        conn.commit()


def get_active_ticket(user_id):
    with connect() as conn:
        row = conn.execute(
            "SELECT active_ticket_id FROM users WHERE user_id=?",
            (user_id,)
        ).fetchone()
        return row["active_ticket_id"] if row else None


def clear_active_ticket(user_id):
    set_active_ticket(user_id, None)


# =========================================================
# CLIENT PROFILE
# =========================================================

def update_client_profile(user_id, **fields):
    if not fields:
        return

    keys = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [user_id]

    with connect() as conn:
        conn.execute(
            f"UPDATE users SET {keys} WHERE user_id=?",
            values
        )
        conn.commit()
