import sqlite3

# Укажите путь к новому файлу базы данных
db_path = 'C:\\Users\\Фотончик\\OneDrive\\Desktop\\домашка\\BKR\\08code\\orders-tg-bot-master\\orders.db'

# Подключение к базе данных (если файл не существует, он будет создан)
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Создание таблицы, если она не существует
cur.execute('''
CREATE TABLE IF NOT EXISTS `order` (
    `id` INTEGER PRIMARY KEY AUTOINCREMENT,
    `user_id` TEXT,
    `date` DATE,
    `telephone` TEXT,
    `address` TEXT,
    `order_list` TEXT,
    status INTEGER DEFAULT 0
)
''')

# Сохранение изменений и закрытие соединения
conn.commit()
conn.close()

print("Новый файл базы данных создан и таблица `order` добавлена.")
