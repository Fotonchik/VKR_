# admin_bot.py — телеграм-бот с функциональностью для администратора, менеджера и оператора

import datetime
import uuid
import telebot
from telebot import types

import config
import db

bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode='HTML')

admin_ids = config.ADMIN_CHAT_ID[:]
manager_ids = config.MANAGER_CHAT_ID[:]
tp_ids = config.TP_CHAT_ID[:]

users_from_db = db.ensure_and_get_users()
role_dict = {"admin": [], "manager": [], "tp": []}
for uid, name, role in users_from_db:
    role_dict[role].append(uid)
    if role == "admin" and uid not in admin_ids:
        admin_ids.append(uid)
    if role == "manager" and uid not in manager_ids:
        manager_ids.append(uid)
    if role == "tp" and uid not in tp_ids:
        tp_ids.append(uid)

admin_workflow = {}

def has_role(user_id, roles):
    return any(user_id in role_dict.get(r, []) for r in roles)

def has_access(user_id, roles):
    if "admin" in roles and user_id in config.ADMIN_CHAT_ID:
        return True
    if "manager" in roles and user_id in config.MANAGER_CHAT_ID:
        return True
    if "tp" in roles and user_id in config.TP_CHAT_ID:
        return True
    return has_role(user_id, roles)

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_"))
def handle_edit_callback(call):
    bot.answer_callback_query(call.id)
    if not has_access(call.from_user.id, ["admin"]):
        return bot.send_message(call.message.chat.id, "❌ Нет доступа")

    role_map = {
        "edit_tp": "tp",
        "edit_manager": "manager",
        "edit_admin": "admin"
    }
    role = role_map.get(call.data)
    if not role:
        return bot.send_message(call.message.chat.id, "⚠ Неизвестная роль")

    users = [u for u in db.ensure_and_get_users() if u[2] == role]

    if not users:
        return bot.send_message(call.message.chat.id, f"⚠ Нет сотрудников в роли {role}.")

    for uid, name, _ in users:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("✏ Изменить имя", callback_data=f"rename_{uid}"))
        if role != "admin":
            keyboard.add(types.InlineKeyboardButton("🔑 Изменить ключ", callback_data=f"rekey_{uid}"))
        keyboard.add(types.InlineKeyboardButton("🔁 Изменить ID", callback_data=f"reid_{uid}"))
        keyboard.add(types.InlineKeyboardButton("❌ Удалить", callback_data=f"del_{uid}"))
        bot.send_message(call.message.chat.id, f"👤 <b>{name}</b> — <code>{uid}</code>", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("rename_"))
def rename_user(call):
    bot.answer_callback_query(call.id)
    user_id = int(call.data.split("_")[1])
    admin_workflow[call.from_user.id] = {"edit_id": user_id, "mode": "name"}
    bot.send_message(call.message.chat.id, "✏ Введите новое имя:")
    bot.register_next_step_handler(call.message, handle_edit_input)

@bot.callback_query_handler(func=lambda call: call.data.startswith("rekey_"))
def rekey_user(call):
    bot.answer_callback_query(call.id)
    user_id = int(call.data.split("_")[1])
    admin_workflow[call.from_user.id] = {"edit_id": user_id, "mode": "key"}
    bot.send_message(call.message.chat.id, "🔑 Введите новый ключ:")
    bot.register_next_step_handler(call.message, handle_edit_input)

@bot.callback_query_handler(func=lambda call: call.data.startswith("reid_"))
def reid_user(call):
    bot.answer_callback_query(call.id)
    user_id = int(call.data.split("_")[1])
    admin_workflow[call.from_user.id] = {"edit_id": user_id, "mode": "id"}
    bot.send_message(call.message.chat.id, "🔁 Введите новый ID:")
    bot.register_next_step_handler(call.message, handle_edit_input)

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_"))
def delete_user(call):
    bot.answer_callback_query(call.id)
    user_id = int(call.data.split("_")[1])
    db.delete_user(user_id)
    bot.send_message(call.message.chat.id, f"❌ Сотрудник с ID <code>{user_id}</code> удалён.")

# Обработка ввода для редактирования

def handle_edit_input(message):
    info = admin_workflow.get(message.from_user.id)
    if not info:
        return bot.send_message(message.chat.id, "⚠ Не удалось обработать операцию.")

    user_id = info.get("edit_id")
    mode = info.get("mode")
    new_value = message.text.strip()

    if mode == "name":
        db.update_user_name(user_id, new_value)
        bot.send_message(message.chat.id, f"✅ Имя обновлено для <code>{user_id}</code>.")
    elif mode == "key":
        db.update_user_key(user_id, new_value)
        bot.send_message(message.chat.id, f"✅ Ключ обновлён для <code>{user_id}</code>.")
    elif mode == "id":
        try:
            new_id = int(new_value)
            existing_ids = [u[0] for u in db.ensure_and_get_users()]
            if new_id in existing_ids:
                return bot.send_message(message.chat.id, "⚠ Такой ID уже существует. Введите другой.")
            db.update_user_id(user_id, new_id)
            bot.send_message(message.chat.id, f"✅ ID обновлён: <code>{user_id}</code> → <code>{new_id}</code>.")
        except ValueError:
            bot.send_message(message.chat.id, "⚠ Неверный формат ID. Введите число.")

print("✅ Админ-бот запущен")

try:
    bot.infinity_polling()
except Exception as e:
    print(f"❌ Ошибка при запуске бота: {e}")
