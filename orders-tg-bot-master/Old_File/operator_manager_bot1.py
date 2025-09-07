# operator_manager_bot.py — панели менеджера и оператора

import telebot
from telebot import types
import db_tickets as db
import config

bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode='HTML')

# === Проверка роли ===
def is_operator(user_id):
    return user_id in config.TP_CHAT_ID or db.has_user_role(user_id, 'tp')

def is_manager(user_id):
    return user_id in config.MANAGER_CHAT_ID or db.has_user_role(user_id, 'manager')

# === Старт ===
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if is_operator(uid):
        return operator_panel(message)
    if is_manager(uid):
        return manager_panel(message)
    bot.send_message(message.chat.id, "❌ У вас нет доступа.")

# === Панель оператора ===
def operator_panel(message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🟢 Активные", callback_data="active"))
    kb.add(types.InlineKeyboardButton("🟡 Открытые", callback_data="open"))
    kb.add(types.InlineKeyboardButton("🔴 Закрытые", callback_data="closed"))
    kb.add(types.InlineKeyboardButton("👤 Учётная запись", callback_data="account"))
    bot.send_message(message.chat.id, "🧑‍💻 Панель оператора:", reply_markup=kb)

# === Панель менеджера ===
def manager_panel(message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📨 Запросы от операторов", callback_data="to_manager"))
    bot.send_message(message.chat.id, "👔 Панель менеджера:", reply_markup=kb)

# === Обработка callback ===
@bot.callback_query_handler(func=lambda c: True)
def handle_callbacks(call):
    uid = call.from_user.id
    data = call.data

    if data in ["open", "closed", "active", "to_manager"] and is_operator(uid):
        tickets = db.get_tickets_by_status(uid, data)
        if not tickets:
            return bot.send_message(call.message.chat.id, "📭 Нет заявок.")
        for t in tickets:
            tid = t['id']
            title = t['title']
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("🔍 Открыть", callback_data=f"view_{tid}"))
            bot.send_message(call.message.chat.id, f"📌 #{tid}: <b>{title}</b>", reply_markup=kb)

    elif data.startswith("view_"):
        tid = int(data.split("_")[1])
        ticket = db.get_ticket_by_id(tid)
        if not ticket:
            return bot.send_message(call.message.chat.id, "❌ Заявка не найдена")

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📄 Добавить информацию", callback_data=f"comment_{tid}"))
        kb.add(types.InlineKeyboardButton("👤 Данные клиента", callback_data=f"client_{ticket['client_id']}"))
        kb.add(types.InlineKeyboardButton("🔁 Передать менеджеру", callback_data=f"forward_{tid}"))
        kb.add(types.InlineKeyboardButton("✅ Закрыть заявку", callback_data=f"close_{tid}"))

        bot.send_message(call.message.chat.id,
                         f"📌 Заявка #{ticket['id']}: <b>{ticket['title']}</b>",
                         reply_markup=kb)

    elif data.startswith("comment_"):
        tid = int(data.split("_")[1])
        bot.send_message(call.message.chat.id, "📝 Введите комментарий:")
        bot.register_next_step_handler(call.message, lambda m: process_comment(m, tid))

    elif data.startswith("client_"):
        cid = int(data.split("_")[1])
        client = db.get_client_by_id(cid)
        if client:
            bot.send_message(call.message.chat.id, f"👤 Клиент #{cid}\nИмя: <b>{client['name']}</b>\nКомментарий: {client['info'] or '—'}")
        else:
            bot.send_message(call.message.chat.id, "❌ Клиент не найден.")

    elif data.startswith("forward_"):
        tid = int(data.split("_")[1])
        bot.send_message(call.message.chat.id, "📝 Введите причину передачи заявки менеджеру:")
        bot.register_next_step_handler(call.message, lambda m: process_forward(m, tid))

    elif data.startswith("close_"):
        tid = int(data.split("_")[1])
        db.close_ticket(tid)
        bot.send_message(call.message.chat.id, f"✅ Заявка #{tid} закрыта.")

    elif data == "account":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("✏ Изменить имя", callback_data="rename"))
        bot.send_message(call.message.chat.id, "👤 Учётная запись:", reply_markup=kb)

    elif data == "rename":
        bot.send_message(call.message.chat.id, "✏ Введите новое имя:")
        bot.register_next_step_handler(call.message, lambda m: db.update_user_name(m.from_user.id, m.text.strip()))
        bot.send_message(call.message.chat.id, "✅ Имя обновлено.")

# === Обработка комментария ===
def process_comment(message, tid):
    text = message.text.strip()
    db.add_ticket_comment(tid, message.from_user.id, text)
    bot.send_message(message.chat.id, "✅ Комментарий добавлен.")

# === Обработка причины передачи ===
def process_forward(message, tid):
    reason = message.text.strip()
    db.transfer_ticket_to_manager(tid, reason)
    bot.send_message(message.chat.id, f"🔁 Заявка #{tid} передана менеджеру.")

print("✅ Бот операторов и менеджеров запущен")
bot.infinity_polling()