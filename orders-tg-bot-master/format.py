from telebot import types

# Кнопки меню администратора
button_hello_text = "Приветствие"
button_menu_nice = "Меню (Краткое)"
button_menu_full = "Меню (Полное)"
button_admins = "Администраторы"
button_add_admin = "Добавить администратора"
button_remove_admin = "Удалить администратора"
button_stickers = "Стикеры"
button_menu_hidden = "Скрыть меню"
button_menu_visible = "Показать меню"

def get_admin_menu_keyboard() -> types.ReplyKeyboardMarkup:
    """
    Возвращает клавиатуру с кнопками меню администратора
    """
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(button_hello_text, button_menu_nice)
    keyboard.add(button_menu_full, button_admins)
    keyboard.add(button_add_admin, button_remove_admin)
    keyboard.add(button_stickers, button_menu_hidden, button_menu_visible)
    return keyboard

def get_admin_menu_text() -> str:
    """
    Возвращает текст для меню администратора
    """
    return "Выберите действие:"

def get_admin_list_text() -> str:
    """
    Возвращает текст для отображения списка администраторов
    """
    return "Список администраторов:"

def get_admin_list_edit_keyboard() -> types.InlineKeyboardMarkup:
    """
    Возвращает клавиатуру для редактирования списка администраторов
    """
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Добавить администратора", callback_data="add_admin"))
    return keyboard

def get_admin_list_remove_keyboard(admin_list: list) -> types.InlineKeyboardMarkup:
    """
    Возвращает клавиатуру для удаления администраторов из списка
    """
    keyboard = types.InlineKeyboardMarkup()
    for admin_id, admin_name in admin_list:
        keyboard.add(types.InlineKeyboardButton(f"Удалить администратора {admin_name}", callback_data=f"remove_admin_{admin_id}"))
    return keyboard

def get_hello_text() -> str:
    """
    Возвращает текст приветствия для администратора
    """
    return "Привет, администратор!"

def get_menu_nice_text() -> str:
    """
    Возвращает текст для краткого меню
    """
    return "Краткое меню"

def get_menu_full_text() -> str:
    """
    Возвращает текст для полного меню
    """
    return "Полное меню"

def get_stickers_list_text() -> str:
    """
    Возвращает текст для списка стикеров
    """
    return "Список стикеров"

def get_menu_hidden_text() -> str:
    """
    Возвращает текст для скрытого меню
    """
    return "Меню скрыто"

def get_menu_visible_text() -> str:
    """
    Возвращает текст для отображаемого меню
    """
    return "Меню отображается"
