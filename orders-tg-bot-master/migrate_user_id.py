import sqlite3
import sys
import config

DB_PATH = config.DB_PATH


def migrate_user_id(old_id: int, new_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        # Проверка существования старого пользователя
        cur.execute("SELECT * FROM users WHERE user_id=?", (old_id,))
        old_user = cur.fetchone()
        if not old_user:
            raise ValueError("Старый user_id не найден")

        # Проверка, что новый user_id не занят
        cur.execute("SELECT * FROM users WHERE user_id=?", (new_id,))
        if cur.fetchone():
            raise ValueError("Новый user_id уже существует")

        print("→ Перенос users...")
        cur.execute("""
            UPDATE users
            SET user_id=?
            WHERE user_id=?
        """, (new_id, old_id))

        print("→ Перенос tickets.client_id...")
        cur.execute("""
            UPDATE tickets
            SET client_id=?
            WHERE client_id=?
        """, (new_id, old_id))

        print("→ Перенос tickets.operator_id...")
        cur.execute("""
            UPDATE tickets
            SET operator_id=?
            WHERE operator_id=?
        """, (new_id, old_id))

        print("→ Перенос ticket_messages.author_id...")
        cur.execute("""
            UPDATE ticket_messages
            SET author_id=?
            WHERE author_id=?
        """, (new_id, old_id))

        conn.commit()
        print("✅ Миграция завершена успешно")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Использование:")
        print("  python migrate_user_id.py OLD_ID NEW_ID")
        sys.exit(1)

    old_user_id = int(sys.argv[1])
    new_user_id = int(sys.argv[2])

    migrate_user_id(old_user_id, new_user_id)
