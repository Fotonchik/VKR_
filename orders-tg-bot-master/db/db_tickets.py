# db/db_tickets.py

import sqlite3
import config
from datetime import datetime
from core.audit import log_create, log_update

DB = config.DB_PATH


# =========================================================
# INIT
# =========================================================

def init_tickets_tables():
    with sqlite3.connect(DB) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_number TEXT UNIQUE,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT CHECK(status IN (
                'new','in_progress','resolved','closed'
            )) DEFAULT 'new',
            priority TEXT CHECK(priority IN (
                'low','medium','high','urgent'
            )) DEFAULT 'medium',
            assigned_to INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            closed_at DATETIME
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS ticket_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            message_type TEXT CHECK(
                message_type IN ('text','photo','document')
            ) DEFAULT 'text',
            content TEXT,
            file_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()


# =========================================================
# HELPERS
# =========================================================

def _generate_ticket_number(conn):
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"TICKET-{today}"

    row = conn.execute("""
        SELECT COUNT(*) FROM tickets
        WHERE ticket_number LIKE ?
    """, (f"{prefix}%",)).fetchone()

    seq = row[0] + 1
    return f"{prefix}-{seq:03d}"


def _validate_status_transition(old, new):
    transitions = {
        "new": ["in_progress"],
        "in_progress": ["resolved", "closed"],
        "resolved": ["closed"],
        "closed": []
    }
    return new in transitions.get(old, [])


# =========================================================
# CREATE
# =========================================================

def create_ticket(
    *,
    user_id: int,
    subject: str,
    description: str,
    priority: str = "medium"
):
    with sqlite3.connect(DB) as conn:
        ticket_number = _generate_ticket_number(conn)

        cur = conn.execute("""
        INSERT INTO tickets (
            ticket_number, user_id,
            subject, description, priority
        ) VALUES (?, ?, ?, ?, ?)
        """, (
            ticket_number,
            user_id,
            subject,
            description,
            priority
        ))

        ticket_id = cur.lastrowid
        conn.commit()

    log_create(
        user_id=user_id,
        entity="ticket",
        entity_id=ticket_id,
        new_value={
            "ticket_number": ticket_number,
            "subject": subject,
            "priority": priority
        }
    )

    return ticket_id, ticket_number


# =========================================================
# STATUS / ASSIGNMENT
# =========================================================

def update_ticket_status(
    *,
    current_user_id: int,
    ticket_id: int,
    new_status: str
):
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        ticket = conn.execute(
            "SELECT * FROM tickets WHERE id=?",
            (ticket_id,)
        ).fetchone()

        if not ticket:
            raise ValueError("Заявка не найдена")

        if not _validate_status_transition(ticket["status"], new_status):
            raise ValueError(
                f"Недопустимый переход статуса: "
                f"{ticket['status']} → {new_status}"
            )

        old_status = ticket["status"]

        fields = ["status=?", "updated_at=?"]
        values = [new_status, datetime.utcnow().isoformat()]

        if new_status == "closed":
            fields.append("closed_at=?")
            values.append(datetime.utcnow().isoformat())

        values.append(ticket_id)

        conn.execute(
            f"UPDATE tickets SET {', '.join(fields)} WHERE id=?",
            values
        )
        conn.commit()

    log_update(
        user_id=current_user_id,
        entity="ticket",
        entity_id=ticket_id,
        old_value={"status": old_status},
        new_value={"status": new_status}
    )


def assign_ticket(
    *,
    current_user_id: int,
    ticket_id: int,
    assigned_to: int
):
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        ticket = conn.execute(
            "SELECT * FROM tickets WHERE id=?",
            (ticket_id,)
        ).fetchone()

        if not ticket:
            raise ValueError("Заявка не найдена")

        old_value = dict(ticket)

        conn.execute("""
        UPDATE tickets
        SET assigned_to=?, updated_at=?
        WHERE id=?
        """, (
            assigned_to,
            datetime.utcnow().isoformat(),
            ticket_id
        ))
        conn.commit()

    log_update(
        user_id=current_user_id,
        entity="ticket",
        entity_id=ticket_id,
        old_value={"assigned_to": old_value["assigned_to"]},
        new_value={"assigned_to": assigned_to}
    )


# =========================================================
# MESSAGES
# =========================================================

def add_ticket_message(
    *,
    ticket_id: int,
    user_id: int,
    message_type: str = "text",
    content: str | None = None,
    file_id: str | None = None
):
    with sqlite3.connect(DB) as conn:
        conn.execute("""
        INSERT INTO ticket_messages (
            ticket_id, user_id,
            message_type, content, file_id
        ) VALUES (?, ?, ?, ?, ?)
        """, (
            ticket_id,
            user_id,
            message_type,
            content,
            file_id
        ))
        conn.commit()


def get_ticket_messages(ticket_id: int):
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("""
        SELECT * FROM ticket_messages
        WHERE ticket_id=?
        ORDER BY created_at
        """, (ticket_id,)).fetchall()


# =========================================================
# QUERIES
# =========================================================

def get_ticket_by_id(ticket_id: int):
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            "SELECT * FROM tickets WHERE id=?",
            (ticket_id,)
        ).fetchone()


def get_tickets_by_status(status: str):
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            "SELECT * FROM tickets WHERE status=? ORDER BY created_at DESC",
            (status,)
        ).fetchall()


def get_tickets_for_user(user_id: int):
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            "SELECT * FROM tickets WHERE user_id=? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
