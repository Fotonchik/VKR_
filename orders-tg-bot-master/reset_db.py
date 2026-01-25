"""
reset_db.py — безопасный сброс локальной SQLite базы (orders.db).

Что делает:
- создает бэкап текущей БД рядом с файлом
- удаляет основной файл БД
- пересоздает таблицы (users/orders/products + tickets/clients/comments)

Использование (PowerShell):
  python reset_db.py --yes
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from datetime import datetime

import config
import db
import db_tickets

# На Windows консоль часто CP1251/CP866 и может падать на emoji.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def reset_database(db_path: str) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    if os.path.exists(db_path):
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = f"{db_path}.bak.{ts}"
        shutil.copy2(db_path, backup_path)
        print(f"✅ Бэкап создан: {backup_path}")

        os.remove(db_path)
        print(f"🗑 Удалён файл БД: {db_path}")
    else:
        print(f"ℹ Файл БД не найден, будет создан заново: {db_path}")

    # Пересоздаем таблицы
    db.check_database()
    db.ensure_and_get_users()
    db_tickets.init_ticket_db()
    print("✅ Таблицы пересозданы. База пустая.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Подтверждение удаления/пересоздания базы данных",
    )
    args = parser.parse_args()

    db_path = config.DB_PATH
    print(f"База данных: {db_path}")
    if not args.yes:
        print("⚠ Это удалит текущую базу данных (с бэкапом).")
        print("Запустите так: python reset_db.py --yes")
        return 2

    reset_database(db_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

