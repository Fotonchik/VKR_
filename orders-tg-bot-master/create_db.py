# create_db.py

import config

from db import employees
from db import db_faq
from db import db_tickets


# =========================================================
# MAIN INIT (используется bot.py)
# =========================================================

def init_database():
    """
    Единая точка инициализации БД.
    НЕ содержит SQL.
    """
    print("▶ Инициализация базы данных...")

    employees.init_table()
    print("✔ employees")

    # bootstrap admin
    admin_id = getattr(config, "BOOTSTRAP_ADMIN_ID", None)
    if admin_id:
        employees.create_admin_if_not_exists(admin_id)
        print("✔ bootstrap admin")

    print("✅ База данных полностью готова.")


# =========================================================
# MANUAL RUN
# =========================================================

if __name__ == "__main__":
    init_database()
