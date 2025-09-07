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
    # elif message.chat.id == TP:
    #     # Приветствие TP
    #     bot.send_message(message.chat.id, 
    #                     format2.get_hello_tp_text(), 
    #                     reply_markup=format2.get_hello_TP_keyboard())
    # elif message.chat.id == manager:
    #     # Приветствие менеджера
    #     bot.send_message(message.chat.id, 
    #                     format2.get_hello_manager_text(), 
    #                     reply_markup=format2.get_hello_manager_keyboard())
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
            # Приветствие пользователя
            case _: 
                bot.send_message(message.chat.id, 
                    format2.get_hello_client_text(), 
                    reply_markup=format2.get_hello_client_keyboard())
    if message.chat.id == admin:
        if not check_access_message(message):  return
        # Обрабтка сообщений главного меню администратора
        match message.text:
           
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
            # case format2.button_managers:
            #     bot.send_message(message.chat.id, 
            #                      format2.get_admin_list_text(),
            #                      reply_markup=format2.get_admin_list_edit_keyboard())
            # # Редактирование списка TP
            # case format2.button_TPs:
            #     bot.send_message(message.chat.id, 
            #                      format2.get_admin_list_text(),
            #                      reply_markup=format2.get_admin_list_edit_keyboard())
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

    # elif message.chat.id == manager:
    #     # Обрабтка сообщений главного меню manager
    #     match message.text:
    #         # Редактирование списка manager
    #         case format2.button_managers:
    #             bot.send_message(message.chat.id, 
    #                              format2.get_admin_list_text(),
    #                              reply_markup=format2.get_admin_list_edit_keyboard())
    #         # Редактирование списка TP
    #         case format2.button_TPs:
    #             bot.send_message(message.chat.id, 
    #                              format2.get_admin_list_text(),
    #                              reply_markup=format2.get_admin_list_edit_keyboard())
    #         case _:
    #         # Приветствие manager
    #             bot.send_message(message.chat.id, 
    #                             format2.get_hello_manager_text(), 
    #                             reply_markup=format2.get_hello_manager_keyboard())
                

    # elif message.chat.id == TP:
    #     # Обрабтка сообщений главного меню TP
    #     match message.text:
    #         case _:
    #         # Приветствие TP
    #             bot.send_message(message.chat.id, 
    #                             format2.get_hello_TP_text(), 
    #                             reply_markup=format2.get_hello_TP_keyboard())

# Обрабтка сообщений главного меню администратора
@bot.callback_query_handler(func=lambda call: True)
def get_callback(callback: types.CallbackQuery):
    # if not check_access_callback(callback):  return
    match callback.data:
        # Добавление нового блюда
        case 'sticker_delete':
            delete_sticker(callback)
            return
    call = callback.data.split('_')
    match call[0]:
        # Редактирование корзины
    
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

# def set_hello_messageTP(message):
#     '''
#     Установка нового приветствия для TP
#     '''
#     if not message.content_type == 'text':
#         bot.send_message(message.chat.id, 
#                          format2.text_error_only_text, 
#                          reply_markup=format2.get_hello_TP_keyboard())
#         bot.register_next_step_handler(message, set_hello_message)
#         return
#     if message.text == format2.button_ok:
#         get_all_mesasge(message)
#         return
    
#     db.set_message_hello_text(message.text)

#     bot.send_message(message.chat.id, 
#                      format2.text_new_hello_text)
#     msg = bot.send_message(message.chat.id, 
#                                  format2.get_message_hello_edit(),
#                                  reply_markup=format2.get_ok_keyboard())
#     bot.register_next_step_handler(msg, set_hello_message)
    
# # Функция задания нового приветствия для клиента

# def set_hello_messageManager(message):
#     '''
#     Установка нового приветствия для Manager
#     '''
#     if not message.content_type == 'text':
#         bot.send_message(message.chat.id, 
#                          format2.text_error_only_text, 
#                          reply_markup=format2.get_hello_manager_keyboard())
#         bot.register_next_step_handler(message, set_hello_message)
#         return
#     if message.text == format2.button_ok:
#         get_all_mesasge(message)
#         return
    
#     db.set_message_hello_text(message.text)

#     bot.send_message(message.chat.id, 
#                      format2.text_new_hello_text)
#     msg = bot.send_message(message.chat.id, 
#                                  format2.get_message_hello_edit(),
#                                  reply_markup=format2.get_ok_keyboard())
#     bot.register_next_step_handler(msg, set_hello_message)
    
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

# def add_TP_step1(message: types.Message) -> None:
#     '''
#     Устанавливает новое имя и запрашивает id TP
#     '''
#     if not message.content_type == 'text':
#         bot.send_message(message.chat.id, format2.text_error_only_text)
#         bot.register_next_step_handler(message, add_TP_step1)
#         return
    
#     if message.text == format2.button_back:
#         bot.send_message(message.chat.id, 
#                      format2.get_hello_TP_text(),
#                      reply_markup=format2.get_hello_TP_keyboard())
#         return
    
#     msg = bot.send_message(message.chat.id, 
#                            format2.get_TP_id(), 
#                            reply_markup=format2.get_back_keyboard())
#     bot.register_next_step_handler(msg, add_TP_step2, message.text)

# def add_TP_step2(message: types.Message, name: str) -> None:
#     '''
#     Устанавливает id нового TP
#     '''
#     if not message.content_type == 'text':
#         bot.send_message(message.chat.id, format2.text_error_only_text)
#         bot.register_next_step_handler(message, add_TP_step2)
#         return

#     if message.text == format2.button_back:
#         bot.send_message(message.chat.id, 
#                      format2.get_hello_TP_text(),
#                      reply_markup=format2.get_hello_TP_keyboard())
#         return
    
#     if not message.text.isdigit():
#         bot.send_message(message.chat.id, 
#                          format2.text_error_id)
#         bot.register_next_step_handler(message, add_TP_step2)
#         return
    
#     db.add_TP(int(message.text), name)
#     bot.send_message(message.chat.id, format2.text_done)

#     bot.send_message(message.chat.id, 
#                      format2.get_hello_TP_text(),
#                      reply_markup=format2.get_hello_TP_keyboard())
#     load_TPs()


# Секция добавления manager 

# def add_manager_step1(message: types.Message) -> None:
#     '''
#     Устанавливает новое имя и запрашивает id manager
#     '''
#     if not message.content_type == 'text':
#         bot.send_message(message.chat.id, format2.text_error_only_text)
#         bot.register_next_step_handler(message, add_manager_step1)
#         return
    
#     if message.text == format2.button_back:
#         bot.send_message(message.chat.id, 
#                      format2.get_hello_manager_text(),
#                      reply_markup=format2.get_hello_manager_keyboard())
#         return
    
#     msg = bot.send_message(message.chat.id, 
#                            format2.get_manager_id(), 
#                            reply_markup=format2.get_back_keyboard())
#     bot.register_next_step_handler(msg, add_manager_step2, message.text)

# def add_manager_step2(message: types.Message, name: str) -> None:
#     '''
#     Устанавливает id нового manager
#     '''
#     if not message.content_type == 'text':
#         bot.send_message(message.chat.id, format2.text_error_only_text)
#         bot.register_next_step_handler(message, add_manager_step2)
#         return

#     if message.text == format2.button_back:
#         bot.send_message(message.chat.id, 
#                      format2.get_hello_manager_text(),
#                      reply_markup=format2.get_hello_manager_keyboard())
#         return
    
#     if not message.text.isdigit():
#         bot.send_message(message.chat.id, 
#                          format2.text_error_id)
#         bot.register_next_step_handler(message, add_manager_step2)
#         return
    
#     db.add_manager(int(message.text), name)
#     bot.send_message(message.chat.id, format2.text_done)

#     bot.send_message(message.chat.id, 
#                      format2.get_hello_manager_text(),
#                      reply_markup=format2.get_hello_manager_keyboard())
#     load_managers()

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

bot.infinity_polling()

