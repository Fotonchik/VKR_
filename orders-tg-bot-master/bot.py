import datetime
import telebot
from telebot import types

import config
import db
import format

bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode='HTML')

# Определение глобальных переменных
orders_chat = config.ORDERS_CHAT_ID
admin = [config.ADMIN_CHAT_ID]
TP = config.TP_CHAT_ID
manager = config.MANAGER_CHAT_ID

# Корзины пользователей
carts = {}
# Сообщения с корзиной пользователя
cart_message_id = {}
# Проверка базы данных
db.check_database()

def load_admins():
    """
    Обновляет список администраторов бота
    """
    global admin
    admin = [config.ADMIN_CHAT_ID]
    admins = db.get_admins()
    for chat_id, name in admins:
        admin.append(chat_id)

load_admins()
@bot.message_handler(commands=['start'])
def handle_start(message):
    """
    Обрабатывает команду /start
    """
    user_id = message.chat.id
    user_name = message.chat.first_name
    
    if not db.user_exists(user_id):
        register_user(message, user_id, user_name)
    else:
        show_main_menu(message)

def register_user(message, user_id, user_name):
    """
    Регистрирует нового пользователя
    """
    db.add_user(user_id, user_name)
    bot.send_message(user_id, f"Вы успешно зарегистрированы как {user_name}.")
    show_main_menu(message)

def show_main_menu(message):
    """
    Отображает главное меню
    """
    user_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Сделать заказ")
    btn2 = types.KeyboardButton("Мои заказы")
    btn3 = types.KeyboardButton("Информация")
    markup.add(btn1, btn2, btn3)
    bot.send_message(user_id, "Выберите действие:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_main_menu)
def handle_main_menu(message):
    """
    Обрабатывает выбор в главном меню
    """
    user_id = message.chat.id
    choice = message.text
    if choice == "Сделать заказ":
        start_order(message)
    elif choice == "Мои заказы":
        show_user_orders(message)
    elif choice == "Информация":
        show_info(message)
    else:
        bot.send_message(user_id, "Неверный выбор. Попробуйте еще раз.")
        show_main_menu(message)

def start_order(message):
    """
    Начинает процесс оформления заказа
    """
    user_id = message.chat.id
    carts[user_id] = []
    cart_message_id[user_id] = None
    bot.send_message(user_id, "Начинаем оформление заказа. Выберите товар:")
    show_product_menu(message)

def show_product_menu(message):
    """
    Отображает меню товаров
    """
    user_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    products = db.get_products()
    for product in products:
        btn = types.KeyboardButton(product[1])
        markup.add(btn)
    btn = types.KeyboardButton("Завершить заказ")
    markup.add(btn)
    bot.send_message(user_id, "Выберите товар или завершите заказ:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_product_selection)

def handle_product_selection(message):
    """
    Обрабатывает выбор товара
    """
    user_id = message.chat.id
    choice = message.text
    if choice == "Завершить заказ":
        finalize_order(message)
    else:
        product = db.get_product_by_name(choice)
        if product:
            carts[user_id].append(product)
            update_cart_message(message)
            show_product_menu(message)
        else:
            bot.send_message(user_id, "Неверный выбор. Попробуйте еще раз.")
            show_product_menu(message)

def update_cart_message(message):
    """
    Обновляет сообщение с корзиной
    """
    user_id = message.chat.id
    cart = carts[user_id]
    if cart_message_id[user_id]:
        bot.edit_message_text(chat_id=user_id, message_id=cart_message_id[user_id], text=format.format_cart(cart))
    else:
        msg = bot.send_message(user_id, format.format_cart(cart))
        cart_message_id[user_id] = msg.message_id

def finalize_order(message):
    """
    Завершает оформление заказа
    """
    user_id = message.chat.id
    cart = carts[user_id]
    if cart:
        order_id = db.add_order(user_id, cart)
        bot.send_message(user_id, f"Ваш заказ #{order_id} успешно оформлен.")
        notify_admins(order_id, cart)
        carts[user_id] = []
        cart_message_id[user_id] = None
        show_main_menu(message)
    else:
        bot.send_message(user_id, "Ваша корзина пуста. Добавьте товары, чтобы оформить заказ.")
        show_product_menu(message)

def notify_admins(order_id, cart):
    """
    Уведомляет администраторов о новом заказе
    """
    for chat_id in admin:
        bot.send_message(chat_id, format.format_order(order_id, cart))

def show_user_orders(message):
    """
    Отображает список заказов пользователя
    """
    user_id = message.chat.id
    orders = db.get_user_orders(user_id)
    if orders:
        for order_id, created_at, total in orders:
            bot.send_message(user_id, format.format_order_summary(order_id, created_at, total))
    else:
        bot.send_message(user_id, "У вас пока нет заказов.")
    show_main_menu(message)

def show_info(message):
    """
    Отображает информацию о боте
    """
    user_id = message.chat.id
    bot.send_message(user_id, "Это бот для оформления заказов.")
    show_main_menu(message)

def check_access_time() -> bool:
    """
    Проверяет, находится ли текущее время в разрешенном диапазоне (с 9:00 до 23:00)
    """
    now = datetime.datetime.now()
    return 9 <= now.hour < 23

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    """
    Обрабатывает callback-запросы
    """
    pass

bot.polling()
