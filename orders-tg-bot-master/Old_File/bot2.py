import datetime
import telebot
import re
from telebot import types

import config
import db
import format2

bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode='HTML')

# Определение глобальных переменных
orders_chat = config.ORDERS_CHAT_ID
admin = config.ADMIN_CHAT_ID
TP = config.TP_CHAT_ID
manager = config.MANAGER_CHAT_ID

# Корзины пользователей
carts = {}
# Сообщения с корзиной пользователя
cart_message_id = {}
# Проверка базы данных
db.check_database()

def load_admins():
    '''
    Обновляет список администраторов бота
    '''
    global admin
    admin = config.ADMIN_CHAT_ID
    admins = db.get_admins()
    for item in admins:
        admin.append(item[0])

load_admins()

def load_TPs():
    '''
    Обновляет список TP бота
    '''
    global TP
    TP = config.TP_CHAT_ID
    TPs = db.get_TPs()
    for item in TPs:
        TP.append(item[0])

load_TPs()

def load_managers():
    '''
    Обновляет список managers бота
    '''
    global manager
    manager = config.MANAGER_CHAT_ID
    managers = db.get_managers()
    for item in managers:
        manager.append(item[0])

load_managers()


def check_access_time() -> bool:
    '''
    Доступ разрешен в период: с 9:00 до 23:00
    '''
    return True
    now = datetime.datetime.now()
    current_hour = now.hour
    current_minute = now.minute

    if 9 <= current_hour <= 23 and current_minute < 60: return True
    else: return False

def check_access_message(message: types.Message) -> bool:
    '''
    Функция проверки досутпа к сообщениям бота
    Необходима для блокировки бота в нерабочее время
    '''
    access = check_access_time()
    if access: return access
    bot.send_message(message.chat.id, 
                     format2.get_access_restricted_text(),
                     reply_markup=format2.get_ok_keyboard())
    return access

def check_access_callback(callback: types.CallbackQuery) -> bool:
    '''
    Функция проверки досутпа к callback кнопкам бота
    Необходима для блокировки бота в нерабочее время
    '''
    access = check_access_time()
    if access: return
    bot.delete_message(callback.message.chat.id, callback.message.id)
    bot.send_message(callback.message.chat.id, 
                     format2.get_access_restricted_text(),
                     reply_markup=format2.get_ok_keyboard())
    return access

@bot.message_handler(commands=['start', 'старт', 'начало'])
def hello_message_command(message):
    '''
    Сообщение приветствия
    '''
    if message.chat.id < 0:  return
    
    # Проверка роли пользователя
    if message.chat.id in admin:
        # Приветствие администратора
        bot.send_message(message.chat.id, 
                        format2.get_hello_admin_text(), 
                        reply_markup=format2.get_hello_admin_keyboard())
    elif message.chat.id == TP:
        # Приветствие TP
        bot.send_message(message.chat.id, 
                        format2.get_hello_tp_text(), 
                        reply_markup=format2.get_hello_TP_keyboard())
    elif message.chat.id == manager:
        # Приветствие менеджера
        bot.send_message(message.chat.id, 
                        format2.get_hello_manager_text(), 
                        reply_markup=format2.get_hello_manager_keyboard())
    else:
        # Приветствие клиента
        if not check_access_message(message):
            return
        bot.send_message(message.chat.id, 
                        format2.get_hello_client_text(), 
                        reply_markup=format2.get_hello_client_keyboard())

@bot.message_handler(content_types=['text'])
def get_all_mesasge(message):
    '''
    Текстовые сообщения
    '''
    if message.chat.id < 0:  return
    if message.chat.id not in admin and message.chat.id != TP and message.chat.id != manager:
        if not check_access_message(message):  return
        match message.text:
            # TODO: 
            case format2.button_init_order:
                start_order(message)
            # Приветствие пользователя
            case _: 
                bot.send_message(message.chat.id, 
                    format2.get_hello_client_text(), 
                    reply_markup=format2.get_hello_client_keyboard())
    if message.chat.id == admin:
        if not check_access_message(message):  return
        # Обрабтка сообщений главного меню администратора
        match message.text:
            # Вывод меню (полностью)
            case format2.button_menu_full:
                menu = db.menu_get_list()
                if len(menu) == 0:
                    bot.send_message(message.chat.id, 
                                     format2.text_empty_menu, 
                                     reply_markup=format2.get_menu_add_keyboard())
                else:
                    bot.send_message(message.chat.id, 
                                     format2.format_menu_list_full(menu), 
                                     reply_markup=format2.get_menu_edit_keyboard())
            # Вывод меню (как для клиента)
            case format2.button_menu_nice:
                menu = db.menu_get_list_nice()
                if len(menu) == 0:
                    bot.send_message(message.chat.id, 
                                     format2.text_empty_menu_admin, 
                                     reply_markup=format2.get_menu_add_keyboard())
                else:
                    bot.send_message(message.chat.id, 
                                     format2.format_menu_list_nice(menu), 
                                     reply_markup=format2.get_menu_edit_keyboard())
            # Редактирование текста приветствия клиента
            case format2.button_hello_text:
                msg = bot.send_message(message.chat.id, 
                                 format2.get_message_hello_edit(),
                                 reply_markup=format2.get_ok_keyboard())
                bot.register_next_step_handler(msg, set_hello_message)
            # Редактирование списка администраторов
            case format2.button_admins:
                bot.send_message(message.chat.id, 
                                 format2.get_admin_list_text(),
                                 reply_markup=format2.get_admin_list_edit_keyboard())
            case format2.button_stickers:
                stickers = db.get_sticker_list()
                for sticker in stickers:
                    bot.send_sticker(message.chat.id,
                                     sticker=sticker,
                                     reply_markup=format2.get_sticker_delete_keyboard(sticker))
                bot.send_message(message.chat.id, 
                                 format2.get_sticker_help(),
                                 reply_markup=format2.get_ok_keyboard())
                bot.register_next_step_handler(message, add_sticker)
            # Редактирование списка manager
            case format2.button_managers:
                bot.send_message(message.chat.id, 
                                 format2.get_admin_list_text(),
                                 reply_markup=format2.get_admin_list_edit_keyboard())
            # Редактирование списка TP
            case format2.button_TPs:
                bot.send_message(message.chat.id, 
                                 format2.get_admin_list_text(),
                                 reply_markup=format2.get_admin_list_edit_keyboard())
            # Редактирование списка client
            # TODO: для них свой котел в аду
            # case format.button_clients:
            #     bot.send_message(message.chat.id, 
            #                      format.get_client_list_text(),
            #                      reply_markup=format.get_client_list_edit_keyboard())
            case _:
            # Приветствие администратора
                bot.send_message(message.chat.id, 
                                format2.get_hello_admin_text(), 
                                reply_markup=format2.get_hello_admin_keyboard())

    elif message.chat.id == manager:
        # Обрабтка сообщений главного меню manager
        match message.text:
            # Редактирование списка manager
            case format2.button_managers:
                bot.send_message(message.chat.id, 
                                 format2.get_admin_list_text(),
                                 reply_markup=format2.get_admin_list_edit_keyboard())
            # Редактирование списка TP
            case format2.button_TPs:
                bot.send_message(message.chat.id, 
                                 format2.get_admin_list_text(),
                                 reply_markup=format2.get_admin_list_edit_keyboard())
            case _:
            # Приветствие manager
                bot.send_message(message.chat.id, 
                                format2.get_hello_manager_text(), 
                                reply_markup=format2.get_hello_manager_keyboard())
                

    elif message.chat.id == TP:
        # Обрабтка сообщений главного меню TP
        match message.text:
            case _:
            # Приветствие TP
                bot.send_message(message.chat.id, 
                                format2.get_hello_TP_text(), 
                                reply_markup=format2.get_hello_TP_keyboard())

# Обрабтка сообщений главного меню администратора
@bot.callback_query_handler(func=lambda call: True)
def get_callback(callback: types.CallbackQuery):
    # if not check_access_callback(callback):  return
    match callback.data:
        # Добавление нового блюда
        case 'menu_add':
            menu_add_item_step1(callback)
            return
        case 'sticker_delete':
            delete_sticker(callback)
            return
    call = callback.data.split('_')
    match call[0]:
        # Редактирование корзины
        case 'cart':
            match call[1]:
                # При удалении
                case 'delete':
                    if '+' in call[2]:
                        carts[callback.message.chat.id].pop(call[2])
                    else: 
                        carts[callback.message.chat.id].pop(int(call[2]))
                    bot.delete_message(callback.message.chat.id, callback.message.id)
                    msg = bot.send_message(callback.message.chat.id,
                        format2.format_cart_list(carts[callback.message.chat.id]),
                        reply_markup=format2.get_cart_edit_keyboard(carts[callback.message.chat.id])
                        )
                    cart_message_id[callback.message.chat.id] = msg.id
                # При добавлении
                case 'plus':
                    if '+' in call[2]:
                        count = carts[callback.message.chat.id][call[2]]
                        carts[callback.message.chat.id][call[2]] = count + 1
                    else: 
                        count = carts[callback.message.chat.id][int(call[2])]
                        carts[callback.message.chat.id][int(call[2])] = count + 1
                    bot.delete_message(callback.message.chat.id, callback.message.id)
                    msg = bot.send_message(callback.message.chat.id,
                        format2.format_cart_list(carts[callback.message.chat.id]),
                        reply_markup=format2.get_cart_edit_keyboard(carts[callback.message.chat.id])
                        )
                    cart_message_id[callback.message.chat.id] = msg.id

                # При уменьшении
                case 'minus':
                    if '+' in call[2]:
                        count = carts[callback.message.chat.id][call[2]]
                        if count <= 1:
                            carts[callback.message.chat.id].pop(call[2])
                        else: 
                            carts[callback.message.chat.id][call[2]] = count - 1
                    else: 
                        count = carts[callback.message.chat.id][int(call[2])]
                        if count <= 1:
                            carts[callback.message.chat.id].pop(int(call[2]))
                        else: 
                            carts[callback.message.chat.id][int(call[2])] = count - 1
                    bot.delete_message(callback.message.chat.id, callback.message.id)
                    msg = bot.send_message(callback.message.chat.id,
                        format2.format_cart_list(carts[callback.message.chat.id]),
                        reply_markup=format2.get_cart_edit_keyboard(carts[callback.message.chat.id])
                        )
                    cart_message_id[callback.message.chat.id] = msg.id
        case 'order':
            # Принятие заказа оператором
            match call[1]:
                case 'accept':
                    client = db.order_accept(int(call[2]))
                    bot.send_message(orders_chat, 
                                     format2.get_order_accepted_chat_text(call[2]))
                    bot.edit_message_reply_markup(callback.message.chat.id, 
                                                  callback.message.id, 
                                                  reply_markup=None)
                    bot.edit_message_text(callback.message.text.replace('🟡', '🟢'), 
                                          callback.message.chat.id, 
                                          callback.message.id)
                    
                    bot.send_message(client,
                                     format2.get_order_accpeted_client_text(call[2]),
                                     reply_markup=format2.get_hello_client_keyboard())
                    bot.send_sticker(client, db.get_sticker_random())
                case 'cancel':
                    client = db.order_cancel(int(call[2]))
                    bot.send_message(orders_chat, 
                                     format2.get_order_canceled_chat_text(call[2]))
                    bot.edit_message_reply_markup(callback.message.chat.id, 
                                                  callback.message.id, 
                                                  reply_markup=None)
                    bot.edit_message_text(callback.message.text.replace('🟡', '🔴'), 
                                          callback.message.chat.id, 
                                          callback.message.id)
                    
                    bot.send_message(client, 
                                     format2.get_order_canceled_client_text(call[2]),
                                     reply_markup=format2.get_hello_client_keyboard())
        case 'admin':
            bot.delete_message(callback.message.chat.id, 
                               callback.message.id)
            # Редактирование списка администраторов
            match call[1]:
                case 'add':
                    msg = bot.send_message(callback.message.chat.id,
                                           format2.get_admin_name(), 
                                           reply_markup=format2.get_back_keyboard())
                    bot.register_next_step_handler(callback.message,
                                                   add_admin_step1)
                case 'delete':
                    db.delete_admin(call[2])
                    bot.send_message(callback.message.chat.id, format2.text_admin_deleted)
                    bot.send_message(callback.message.chat.id, 
                                 format2.get_admin_list_text(),
                                 reply_markup=format2.get_admin_list_edit_keyboard())
                    load_admins()


# Секция добавления элемента в меню

def menu_add_item_step1(callback):
    '''
    Определение категории для добавления
    '''
    msg = bot.send_message(callback.message.chat.id, 
                           format2.text_item_category, 
                           reply_markup=format2.get_menu_category_keyboard())
    bot.register_next_step_handler(msg, menu_add_item_step2)

def menu_add_item_step2(message):
    '''
    Выбор названия
    '''

    if not message.content_type == 'text':
        bot.send_message(message.chat.id, format2.text_error_text_or_button)
        bot.register_next_step_handler(message, menu_add_item_step2)
        return

    add_item = db.Food()
    match message.text:
        case format2.category_1: add_item.category = 1
        case format2.category_2: add_item.category = 2
        case format2.category_3: add_item.category = 3
        case format2.category_4: add_item.category = 4
        case format2.category_6: add_item.category = 6
        case format2.button_back: 
            bot.send_message(message.chat.id, 
                     format2.get_hello_admin_text(), 
                     reply_markup=format2.get_hello_admin_keyboard())
            return
        case _: 
            bot.send_message(message.chat.id, 
                             format2.text_error_unknown_category, 
                             reply_markup=format2.get_hello_admin_keyboard())
            return

    msg = bot.send_message(message.chat.id, 
                           format2.text_item_name, 
                           reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, menu_add_item_step3, add_item)

def menu_add_item_step3(message, add_item):
    '''
    Выбор цены
    '''

    if not message.content_type == 'text':
        bot.send_message(message.chat.id, format2.text_error_only_text)
        bot.register_next_step_handler(message, menu_add_item_step3, add_item)
        return
    
    add_item.name = message.text
    msg = bot.send_message(message.chat.id, 
                           format2.text_item_price, 
                           reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, menu_add_item_step4, add_item)

def menu_add_item_step4(message, add_item):
    '''
    Добавление в меню
    '''

    if not message.content_type == 'text':
        bot.send_message(message.chat.id, format2.text_error_only_numbers)
        bot.register_next_step_handler(message, menu_add_item_step4, add_item)
        return
    if not message.text.isdigit():
        bot.send_message(message.chat.id, format2.text_error_only_numbers)
        bot.register_next_step_handler(message, menu_add_item_step4, add_item)
        return
    
    add_item.price = message.text
    if db.menu_add_item(add_item):
        bot.send_message(message.chat.id, 
                         format2.text_done, 
                         reply_markup=format2.get_hello_admin_keyboard())
    else:
        bot.send_message(message.chat.id, 
                         format2.text_error_adding_item, 
                         reply_markup=format2.get_hello_admin_keyboard())

# Функция задания нового приветствия для клиента

def set_hello_message(message):
    '''
    Установка нового приветствия для пользователя
    '''
    if not message.content_type == 'text':
        bot.send_message(message.chat.id, 
                         format2.text_error_only_text, 
                         reply_markup=format2.get_hello_admin_keyboard())
        bot.register_next_step_handler(message, set_hello_message)
        return
    if message.text == format2.button_ok:
        get_all_mesasge(message)
        return
    
    db.set_message_hello_text(message.text)

    bot.send_message(message.chat.id, 
                     format2.text_new_hello_text)
    msg = bot.send_message(message.chat.id, 
                                 format2.get_message_hello_edit(),
                                 reply_markup=format2.get_ok_keyboard())
    bot.register_next_step_handler(msg, set_hello_message)

# Функция задания нового приветствия для TP

def set_hello_messageTP(message):
    '''
    Установка нового приветствия для TP
    '''
    if not message.content_type == 'text':
        bot.send_message(message.chat.id, 
                         format2.text_error_only_text, 
                         reply_markup=format2.get_hello_TP_keyboard())
        bot.register_next_step_handler(message, set_hello_message)
        return
    if message.text == format2.button_ok:
        get_all_mesasge(message)
        return
    
    db.set_message_hello_text(message.text)

    bot.send_message(message.chat.id, 
                     format2.text_new_hello_text)
    msg = bot.send_message(message.chat.id, 
                                 format2.get_message_hello_edit(),
                                 reply_markup=format2.get_ok_keyboard())
    bot.register_next_step_handler(msg, set_hello_message)
    
# Функция задания нового приветствия для клиента

def set_hello_messageManager(message):
    '''
    Установка нового приветствия для Manager
    '''
    if not message.content_type == 'text':
        bot.send_message(message.chat.id, 
                         format2.text_error_only_text, 
                         reply_markup=format2.get_hello_manager_keyboard())
        bot.register_next_step_handler(message, set_hello_message)
        return
    if message.text == format2.button_ok:
        get_all_mesasge(message)
        return
    
    db.set_message_hello_text(message.text)

    bot.send_message(message.chat.id, 
                     format2.text_new_hello_text)
    msg = bot.send_message(message.chat.id, 
                                 format2.get_message_hello_edit(),
                                 reply_markup=format2.get_ok_keyboard())
    bot.register_next_step_handler(msg, set_hello_message)
    
# Секция добавления администратора 

def add_admin_step1(message: types.Message) -> None:
    '''
    Устанавливает новое имя и запрашивает id администратора
    '''
    if not message.content_type == 'text':
        bot.send_message(message.chat.id, format2.text_error_only_text)
        bot.register_next_step_handler(message, add_admin_step1)
        return
    
    if message.text == format2.button_back:
        bot.send_message(message.chat.id, 
                     format2.get_hello_admin_text(),
                     reply_markup=format2.get_hello_admin_keyboard())
        return
    
    msg = bot.send_message(message.chat.id, 
                           format2.get_admin_id(), 
                           reply_markup=format2.get_back_keyboard())
    bot.register_next_step_handler(msg, add_admin_step2, message.text)

def add_admin_step2(message: types.Message, name: str) -> None:
    '''
    Устанавливает id нового администратора
    '''
    if not message.content_type == 'text':
        bot.send_message(message.chat.id, format2.text_error_only_text)
        bot.register_next_step_handler(message, add_admin_step2)
        return

    if message.text == format2.button_back:
        bot.send_message(message.chat.id, 
                     format2.get_hello_admin_text(),
                     reply_markup=format2.get_hello_admin_keyboard())
        return
    
    if not message.text.isdigit():
        bot.send_message(message.chat.id, 
                         format2.text_error_id)
        bot.register_next_step_handler(message, add_admin_step2)
        return
    
    db.add_admin(int(message.text), name)
    bot.send_message(message.chat.id, format2.text_done)

    bot.send_message(message.chat.id, 
                     format2.get_hello_admin_text(),
                     reply_markup=format2.get_hello_admin_keyboard())
    load_admins()

# Секция добавления TP

def add_TP_step1(message: types.Message) -> None:
    '''
    Устанавливает новое имя и запрашивает id TP
    '''
    if not message.content_type == 'text':
        bot.send_message(message.chat.id, format2.text_error_only_text)
        bot.register_next_step_handler(message, add_TP_step1)
        return
    
    if message.text == format2.button_back:
        bot.send_message(message.chat.id, 
                     format2.get_hello_TP_text(),
                     reply_markup=format2.get_hello_TP_keyboard())
        return
    
    msg = bot.send_message(message.chat.id, 
                           format2.get_TP_id(), 
                           reply_markup=format2.get_back_keyboard())
    bot.register_next_step_handler(msg, add_TP_step2, message.text)

def add_TP_step2(message: types.Message, name: str) -> None:
    '''
    Устанавливает id нового TP
    '''
    if not message.content_type == 'text':
        bot.send_message(message.chat.id, format2.text_error_only_text)
        bot.register_next_step_handler(message, add_TP_step2)
        return

    if message.text == format2.button_back:
        bot.send_message(message.chat.id, 
                     format2.get_hello_TP_text(),
                     reply_markup=format2.get_hello_TP_keyboard())
        return
    
    if not message.text.isdigit():
        bot.send_message(message.chat.id, 
                         format2.text_error_id)
        bot.register_next_step_handler(message, add_TP_step2)
        return
    
    db.add_TP(int(message.text), name)
    bot.send_message(message.chat.id, format2.text_done)

    bot.send_message(message.chat.id, 
                     format2.get_hello_TP_text(),
                     reply_markup=format2.get_hello_TP_keyboard())
    load_TPs()


# Секция добавления manager 

def add_manager_step1(message: types.Message) -> None:
    '''
    Устанавливает новое имя и запрашивает id manager
    '''
    if not message.content_type == 'text':
        bot.send_message(message.chat.id, format2.text_error_only_text)
        bot.register_next_step_handler(message, add_manager_step1)
        return
    
    if message.text == format2.button_back:
        bot.send_message(message.chat.id, 
                     format2.get_hello_manager_text(),
                     reply_markup=format2.get_hello_manager_keyboard())
        return
    
    msg = bot.send_message(message.chat.id, 
                           format2.get_manager_id(), 
                           reply_markup=format2.get_back_keyboard())
    bot.register_next_step_handler(msg, add_manager_step2, message.text)

def add_manager_step2(message: types.Message, name: str) -> None:
    '''
    Устанавливает id нового manager
    '''
    if not message.content_type == 'text':
        bot.send_message(message.chat.id, format2.text_error_only_text)
        bot.register_next_step_handler(message, add_manager_step2)
        return

    if message.text == format2.button_back:
        bot.send_message(message.chat.id, 
                     format2.get_hello_manager_text(),
                     reply_markup=format2.get_hello_manager_keyboard())
        return
    
    if not message.text.isdigit():
        bot.send_message(message.chat.id, 
                         format2.text_error_id)
        bot.register_next_step_handler(message, add_manager_step2)
        return
    
    db.add_manager(int(message.text), name)
    bot.send_message(message.chat.id, format2.text_done)

    bot.send_message(message.chat.id, 
                     format2.get_hello_manager_text(),
                     reply_markup=format2.get_hello_manager_keyboard())
    load_managers()

def add_sticker(message: types.Message) -> None:
    '''
    Процедура добавления нового стикера
    '''
    if message.content_type == 'text':
        if message.text == format2.button_ok:
            bot.send_message(message.chat.id,
                            format2.text_done,
                            reply_markup=types.ReplyKeyboardRemove())
            bot.send_message(message.chat.id, 
                     format2.get_hello_admin_text(),
                     reply_markup=format2.get_hello_admin_keyboard())
            return
    if message.content_type == 'sticker':
        db.add_sticker(message.sticker.file_id)
        bot.send_message(message.chat.id,
                    format2.text_sticker_added,
                    reply_markup=format2.get_ok_keyboard())
    bot.register_next_step_handler(message, add_sticker)

def delete_sticker(callback: types.CallbackQuery) -> None:
    '''
    Функция удаления стикеров. Если стикер остался один, он не даст этого сделать
    '''
    if len(db.get_sticker_list()) == 1:
        bot.send_message(callback.message.chat.id,
                         format2.text_sticker_last)
        return
    bot.delete_message(callback.message.chat.id,
                       callback.message.message_id)
    db.delete_sticker(callback.message.sticker.file_id)
    bot.send_message(callback.message.chat.id,
                     format2.text_sticker_deleted)

# Секция создания заказа

def start_order(message):
    '''
    Инициация создания заказа
    '''
    if not check_access_message(message):  return
    msg = bot.send_message(message.chat.id, 
                           format2.text_client_start, 
                           reply_markup=format2.get_order_start_keyboard())
    bot.register_next_step_handler(msg, start_order_step2)

def start_order_step2(message):
    '''
    Обработка кнопок меню пользователя
    '''
    if not check_access_message(message):  return
    if not message.content_type == 'text':
        bot.send_message(message.chat.id, format2.text_error_unknown_command)
        start_order(message)
        return

    global carts
    if message.chat.id not in carts.keys():
        carts.update({message.chat.id: {}})

    match message.text:
        case format2.button_back:
            if message.chat.id in carts.keys():
                carts.pop(message.chat.id)
            hello_message_command(message)
        case format2.button_make_order:
            make_order(message)
        case _: 
            msg = bot.send_message(message.chat.id, format2.text_error_text_or_button)
            bot.register_next_step_handler(msg, start_order_step2)

# Секция обработки заказа

def make_order(message):
    '''
    Начинает обработку заказа
    Если корзина пустая, то возвращает.
    В другом случае спрашиваем: номер телефона (если нету в базе);
    Адрес доставки (если нету в базе)
    И отправляем в чат для заказов предложение принять/отменить
    '''
    if not check_access_message(message):  return
    global carts
    if message.chat.id not in carts.keys() or carts[message.chat.id] == {}:
        msg = bot.send_message(message.chat.id, format2.get_cart_empty_text())
        start_order(msg)
        return
    
    # Удаление сообщения с корзиной перед обработкой заказа
    if message.chat.id in cart_message_id.keys():
        bot.delete_message(message.chat.id, cart_message_id.pop(message.chat.id))
        
    
    bot.send_message(message.chat.id, 
                     format2.get_order_ok_text(carts[message.chat.id]),
                     reply_markup=format2.get_order_ok_keyboard()
                     )
    bot.register_next_step_handler(message, make_order_step1)

def make_order_step1(message):
    '''
    Подтверждает выбор пользователя и предлагает номер телефона
    Также предлагает ввести старый номер телефона
    '''
    if not check_access_message(message):  return
    if not message.content_type == 'text':
        bot.send_message(message.chat.id, format2.text_error_only_text)
        start_order(message)
        return
    if message.text == format2.button_back:
        start_order(message)
        return

    match message.text:
        case format2.button_ok:
            telephone = db.get_telephone_from_last_order(message.chat.id)
            msg = bot.send_message(message.chat.id,
                             format2.get_order_telephone_text(telephone),
                             reply_markup=format2.get_order_telephone_keyboard(telephone))
            bot.register_next_step_handler(msg, make_order_step2)
        case '_':
            start_order(message)
            return
            
def make_order_step2(message):
    '''
    Получает номер телефона и предлагает ввести адрес
    Также предлагает ввести адрес из предыдущего заказа
    '''
    if not check_access_message(message):  return
    if not message.content_type == 'text':
        bot.send_message(message.chat.id, format2.text_error_telephone)
        bot.register_next_step_handler(message, make_order_step2)
        return
    if message.text == format2.button_back:
        start_order(message)
        return
    
    telepgone_regexp = r'(\s*)?(\+)?([- _():=+]?\d[- _():=+]?){10,14}(\s*)?'
    match = re.match(telepgone_regexp, message.text)

    if not match:
        bot.send_message(message.chat.id, format2.text_error_telephone)
        bot.register_next_step_handler(message, make_order_step2)
        return

    address = db.get_address_from_last_order(message.chat.id)

    msg = bot.send_message(message.chat.id,
                           format2.get_order_address_text(address),
                           reply_markup=format2.get_order_address_keyboard(address))
    bot.register_next_step_handler(msg, make_order_step3, match.string)
    
def make_order_step3(message, telephone):
    '''
    Получает адрес и отправляет сообщение в группу
    '''
    if not check_access_message(message):  return
    if not message.content_type == 'text':
        bot.send_message(message.chat.id, format2.text_error_address)
        bot.register_next_step_handler(message, make_order_step3)
        return
    if message.text == format2.button_back:
        message.text = format2.button_ok
        make_order_step1(message)
        return
    if '\"' in message.text or '\'' in message.text:
        bot.send_message(message.chat.id, format2.text_error_address)
        bot.register_next_step_handler(message, make_order_step3)
        return
    
    number = db.order_add(message.chat.id, 
                 telephone, 
                 message.text, 
                 format2.format_cart_list_check(carts[message.chat.id]))
    
    if number == -1:
        bot.send_message(message.chat.id, 
                         format2.text_error_creating)
        return

    bot.send_message(message.chat.id,
                     format2.get_ordered_user_text(number),
                     reply_markup=types.ReplyKeyboardRemove())
    bot.send_message(orders_chat,
                     format2.get_ordered_notify_text(carts.pop(message.chat.id), 
                                                    number,
                                                    message.text,
                                                    telephone),
                     reply_markup=format2.get_ordered_accept_keyboard(number))

bot.infinity_polling()

