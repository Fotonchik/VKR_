import sqlite3
import json, random
from datetime import date, datetime
from config import FILE_DB

DB = FILE_DB

'''
Статусы заказов:
0 - Только что создан
1 - Принят
2 - Отменён
'''

class Food:
    '''
    Категории:
    1 - Первое блюдо
    2 - Гарнир
    3 - Мясное
    4 - Салат
    5 - Напиток
    '''
    id = -1
    category = 0
    name = ''
    price = 0
    visibility = 0

def check_database() -> None:
    '''
    Проверяет на наличие базу данных. В случае отсутствия создает новую пустую
    '''
    
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS `order` 
                (`id` INTEGER PRIMARY KEY AUTOINCREMENT, `user_id` TEXT, `date` date, `telephone` TEXT, `address` TEXT, `order_list` TEXT, status INTEGER DEFAULT 0)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS `menu` 
                (`id` INTEGER PRIMARY KEY AUTOINCREMENT, `category` INTEGER, `name` TEXT UNIQUE, `price` INTEGER, `visibility` INTEGER DEFAULT 1)''')
    cur.execute('''CREATE TABLE  IF NOT EXISTS `message` 
                (`name` TEXT PRIMARY KEY, `text` TEXT NOT NULL)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS`admin`
                (`id` INTEGER PRIMARY KEY, `name` TEXT NOT NULL)''')
    
    # Задание начальных текстов для сообщений
    cur.execute('''INSERT OR IGNORE INTO `message` (name, text) 
                   VALUES ('HELLO_TEXT', "👋 Здравствуйте, вас приветсвтует Пищепром!
📝 Прием заказов на обед до 11; доставка обедов с 13 до 14 🕐")''')
    cur.execute('''INSERT OR IGNORE INTO message (name, text)
                   VALUES ("FINISH_STICKERS", '["CAACAgIAAxkBAAIqrGdQpFi7bZlc3GbdjBBzCTZ3msPJAAKhRgACylVhSB8JxUjYQkfyNgQ"]')''', (''))
    
    con.commit()

def add_admin(id: int, name: str) -> None:
    '''
    Устанавливает нового администратора
    '''
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(f'''INSERT INTO `admin` (id, name) 
                VALUES ({id}, "{name}")''')
    con.commit()

def delete_admin(id: int) -> None:
    '''
    Удаляет администратора
    '''
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(f'''DELETE FROM `admin`
                    WHERE id = {id}''')
    con.commit()

def get_admins() -> list:
    '''
    Выгружает список администраторов из базы данных
    '''
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(f'''SELECT id, name FROM `admin`''')
    return cur.fetchall()


def menu_get_list_nice() -> list:
    '''
    Выгружает из базы данных список всех блюд, без скрытых
    '''
    result = []
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute('''SELECT id, category, name, price
                FROM menu 
                WHERE menu.visibility = 1
                ORDER BY category, id ASC;''')
    rows = cur.fetchall()
    for row in rows:
        f = Food()
        f.id = row[0]
        f.category = row[1]
        f.name = row[2]
        f.price = row[3]
        result.append(f)
    return result

def menu_get_list() -> list:
    '''
    Выгружает из базы данных список всех блюд
    '''
    result = []
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute('''SELECT id, category, name, price, visibility
                FROM menu 
                ORDER BY menu.category, menu.id ASC;''')
    rows = cur.fetchall()
    for row in rows:
        f = Food()
        f.id = row[0]
        f.category = row[1]
        f.name = row[2]
        f.price = row[3]
        f.visibility = row[4]
        result.append(f)
    return result

def menu_get_list_category(category: int) -> list:
    '''
    Получает список блюд из меню по одной категории
    '''
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(f'''SELECT * FROM menu 
                    WHERE category = {category} 
                    ORDER BY `id` ASC;''')
    rows = cur.fetchall()
    result = []
    for row in rows:
        f = Food()
        f.id = row[0]
        f.category = row[1]
        f.name = row[2]
        f.price = row[3]
        f.visibility = row[4]
        result.append(f)
    return result

def menu_get_list_category_nice(category: int) -> list:
    '''
    Получает список блюд из меню по одной категории, без скрытых
    '''
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(f'''SELECT * FROM menu 
                    WHERE category = {category} AND visibility = 1
                    ORDER BY `id` ASC;''')
    rows = cur.fetchall()
    result = []
    for row in rows:
        f = Food()
        f.id = row[0]
        f.category = row[1]
        f.name = row[2]
        f.price = row[3]
        f.visibility = row[4]
        result.append(f)
    return result


def menu_add_item(i: Food) -> bool:
    '''
    Добавляет запись с новым блюдом
    В случае успеха возвращает True
    При ошибке добавления (совпадение по имени), возвращает False
    '''
    con = sqlite3.connect(DB)
    cur = con.cursor()
    try:
        cur.execute(f'''INSERT INTO menu (category, name, price) 
                    VALUES ({i.category}, "{i.name}", {i.price})''')
    except:
        return False
    else:
        con.commit()
        return True
    finally:
        con.close()

def menu_edit_item(id: int, new: Food) -> bool:
    '''
    Установка новых значений для поля
    В случае успеха возвращает True
    При ошибке изменения, возвращает False
    '''
    con = sqlite3.connect(DB)
    cur = con.cursor()
    try:
        cur.execute(f'''UPDATE menu
                    SET name = '{new.name}', price = {new.price}, visibility = {new.visibility}
                    WHERE id = {id};''')
    except:
        return False
    else:
        con.commit()
        return True
    finally:
        con.close()

def menu_delete_item(id: int) -> None:
    '''
    Удаление элемента по id
    '''
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(f'''DELETE FROM menu WHERE id = {id};''')
    con.commit()

def get_item(id) -> Food:
    '''
    Получение одного элемента из БД
    В случае отсутствия возвращает пустой элемент
    '''
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(f'''SELECT * FROM menu 
                    WHERE id = {id};''')
    value = cur.fetchone()

    if value is None:
        return Food()
    
    result = Food()
    result.id = value[0]
    result.category = value[1]
    result.name = value[2]
    result.price = value[3]
    result.visibility = value[4]

    return result

def get_telephone_from_last_order(user_id: int) -> str:
    '''
    Возвращает последний использованный номер телефона
    '''
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(f'''SELECT id, telephone FROM `order` 
                    WHERE user_id = {user_id} 
                    ORDER BY id DESC;''')
    value = cur.fetchone()

    if value is None: return ''
    else: return value[1]

def get_address_from_last_order(user_id: int) -> str:
    '''
    Возвращает последний использованный адрес
    '''
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(f'''SELECT id, address FROM `order` 
                    WHERE user_id = {user_id} 
                    ORDER BY id DESC;''')
    value = cur.fetchone()

    if value is None: return ''
    else: return value[1]

def order_add(user_id: int, telephone: str, address: str, order_list: str, date: datetime = datetime.now()) -> int:
    '''
    Добавляет запись с заказом в базу данных
    При ошибке возвращает -1
    Возвращает номер созданного заказа
    '''
    con = sqlite3.connect(DB)
    cur = con.cursor()

    try:
        cur.execute(f'''INSERT INTO `order` (user_id, date, telephone, address, order_list) 
                    VALUES ("{user_id}", "{date.strftime("%d.%m.%Y %H:%M:%S")}", "{telephone}", "{address}", "{order_list}")''')
    except:
        con.close()
        return -1
                    
    con.commit()
    cur.execute(f'''SELECT id 
                    FROM`order` 
                    WHERE user_id = {user_id} 
                    ORDER BY id DESC;''')
    return int(cur.fetchone()[0])

def order_get_user_id(id: int) -> int:
    '''
    По номеру заказа возвращает id клиента
    '''
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(f'''SELECT user_id FROM `order` 
                    WHERE id = {id};''')
    value = cur.fetchone()

    if value is None: return 0
    else: return value[0]

def order_change_status(id: int, status: int) -> None:
    '''
    Меняет статус заказа
    '''
    con = sqlite3.connect(DB)
    cur = con.cursor()    
    cur.execute(f'''UPDATE `order`
                SET status = {status}
                WHERE id = {id};''')
    con.commit()

def order_accept(id: int) -> int:
    '''
    Делает отметку в БД, что заказ принят
    Возвращает id клиента
    '''
    order_change_status(id, 1)
    return order_get_user_id(id)
    
def order_cancel(id: int) -> int:
    '''
    Делает отметку в БД, что заказ отменен
    Возвращает id клиента
    '''
    order_change_status(id, 2)
    return order_get_user_id(id)
    
def message_get(name: str) -> str:
    '''
    Выгружает из БД текст сообщения
    '''
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(f'''SELECT text
                    FROM `message` 
                    WHERE name = "{name}";''')
    value = cur.fetchone()

    if value is None: return ''
    else: return value[0]

def message_set(name: str, value: str):
    '''
    Задает новое значение для сообщения
    '''
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute('''UPDATE `message`
                    SET text = ?
                    WHERE name = ?;''', (value, name))
    con.commit()

def get_message_hello_text() -> str:
    '''
    Получение сообщения приветствия пользователя
    '''
    return message_get('HELLO_TEXT')

def set_message_hello_text(value: str):
    '''
    Установка сообщения приветствия пользователя
    '''
    message_set('HELLO_TEXT', value)

def get_sticker_random() -> str:
    '''
    Получение случайного id стикера из БД
    '''
    stickers = json.loads(message_get('FINISH_STICKERS'))
    rand = random.Random(datetime.timestamp(datetime.now()))
    sticker_id = rand.randint(0, len(stickers) - 1)
    return stickers[sticker_id]

def get_sticker_list() -> list:
    '''
    Получение списка стикеров
    '''
    stickers = json.loads(message_get('FINISH_STICKERS'))
    return stickers

def add_sticker(sticker_id: str) -> None:
    '''
    Добавление id стикера
    '''
    stickers = json.loads(message_get('FINISH_STICKERS'))
    stickers.append(sticker_id)
    message_set('FINISH_STICKERS', json.dumps(stickers))

def delete_sticker(sticker_id: str) -> None:
    '''
    Удаление id стикера
    '''
    stickers = json.loads(message_get('FINISH_STICKERS'))
    stickers.remove(sticker_id)
    message_set('FINISH_STICKERS', json.dumps(stickers))
    
def item_toggle_visibility(id: int):
    '''
    Изменения отображения блюда
    '''
    item = get_item(id)
    new_visibility = 0 if item.visibility else 1
    
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute('''UPDATE `menu`
                    SET visibility = ?
                    WHERE id = ?;''', (new_visibility, id))
    con.commit()
