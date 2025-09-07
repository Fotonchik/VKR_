# operator_manager_bot.py — панели менеджера и оператора с чатом

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

# Массив чатов: user_id -> (target_id, ticket_id)
chat_sessions = {}

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

    if data in ["open", "closed", "active", "to_manager"]:
        role_check = is_operator(uid) if data != "to_manager" else is_manager(uid)
        tickets = db.get_tickets_by_status(uid if data != "to_manager" else None, data)
        if not role_check or not tickets:
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
        kb.add(types.InlineKeyboardButton("💬 Комментарии", callback_data=f"comments_{tid}"))
        kb.add(types.InlineKeyboardButton("👤 Данные клиента", callback_data=f"client_{ticket['client_id']}"))
        if ticket['status'] == 'to_manager' and is_manager(uid):
            kb.add(types.InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{tid}"))
            kb.add(types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{tid}"))
        else:
            kb.add(types.InlineKeyboardButton("🔁 Передать менеджеру", callback_data=f"forward_{tid}"))
            kb.add(types.InlineKeyboardButton("✅ Закрыть заявку", callback_data=f"close_{tid}"))
            kb.add(types.InlineKeyboardButton("📬 Связь с менеджером", callback_data=f"chat_manager_{uid}"))

        bot.send_message(call.message.chat.id,
                         f"📌 Заявка #{ticket['id']}: <b>{ticket['title']}</b>",
                         reply_markup=kb)

    elif data.startswith("comment_"):
        tid = int(data.split("_")[1])
        bot.send_message(call.message.chat.id, "📝 Введите комментарий:")
        bot.register_next_step_handler(call.message, lambda m: process_comment(m, tid))

    elif data.startswith("comments_"):
        tid = int(data.split("_")[1])
        comments = db.get_ticket_comments(tid)
        if not comments:
            return bot.send_message(call.message.chat.id, "📝 Комментариев нет.")
        text = "💬 Комментарии по заявке:\n\n"
        for c in comments:
            text += f"— <b>{c['author_id']}</b>: {c['text']}\n"
        bot.send_message(call.message.chat.id, text)

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

    elif data.startswith("approve_"):
        tid = int(data.split("_")[1])
        db.update_ticket_status(tid, "active")
        bot.send_message(call.message.chat.id, f"✅ Заявка #{tid} одобрена.")

    elif data.startswith("reject_"):
        tid = int(data.split("_")[1])
        db.update_ticket_status(tid, "open")
        bot.send_message(call.message.chat.id, f"❌ Заявка #{tid} отклонена и возвращена оператору.")

    elif data.startswith("chat_manager_"):
        operator_id = int(data.split("_")[2])
        managers = db.get_users_by_role("manager")
        kb = types.InlineKeyboardMarkup()
        for uid, name in managers:
            kb.add(types.InlineKeyboardButton(name, callback_data=f"chat_with_{uid}_{operator_id}"))
        bot.send_message(call.message.chat.id, "👔 Выберите менеджера для связи:", reply_markup=kb)

    elif data.startswith("chat_with_"):
        parts = data.split("_")
        mid = int(parts[2])
        opid = int(parts[3])
        chat_sessions[opid] = mid
        chat_sessions[mid] = opid
        bot.send_message(mid, f"📞 Связь с оператором <code>{opid}</code> открыта. Напишите сообщение:")
        bot.send_message(opid, f"📞 Связь с менеджером <code>{mid}</code> открыта. Напишите сообщение:")

    elif data == "account":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("✏ Изменить имя", callback_data="rename"))
        bot.send_message(call.message.chat.id, "👤 Учётная запись:", reply_markup=kb)

    elif data == "rename":
        bot.send_message(call.message.chat.id, "✏ Введите новое имя:")
        bot.register_next_step_handler(call.message, lambda m: rename_user(m))

# === Текстовые сообщения для чата ===
@bot.message_handler(content_types=['text', 'photo', 'document'])
def relay_chat(message):
    if message.from_user.id not in chat_sessions:
        return

    target_id, ticket_id = chat_sessions.get(message.from_user.id, (None, 0))
    if not target_id:
        return

    # Текст
    if message.text:
        bot.send_message(target_id, f"✉️ <b>{message.from_user.id}</b>: {message.text}")
        db.add_ticket_comment(ticket_id, message.from_user.id, f"[CHAT TEXT] {message.text}")

    # Документ
    elif message.document:
        bot.send_document(target_id, message.document.file_id, caption=f"📎 Документ от {message.from_user.id}")
        db.add_ticket_comment(ticket_id, message.from_user.id, f"[DOC] {message.document.file_name}")

    # Фото
    elif message.photo:
        largest_photo = message.photo[-1]
        bot.send_photo(target_id, largest_photo.file_id, caption=f"🖼 Фото от {message.from_user.id}")
        db.add_ticket_comment(ticket_id, message.from_user.id, "[PHOTO]")

    if message.from_user.id not in chat_sessions:
        return

    target_id = chat_sessions.get(message.from_user.id)
    if not target_id:
        return

    # Текст
    if message.text:
        bot.send_message(target_id, f"✉️ <b>{message.from_user.id}</b>: {message.text}")
        db.add_ticket_comment(0, message.from_user.id, f"[CHAT TEXT] {message.text}")

    # Документ
    elif message.document:
        bot.send_document(target_id, message.document.file_id, caption=f"📎 Документ от {message.from_user.id}")
        db.add_ticket_comment(0, message.from_user.id, f"[DOC] {message.document.file_name}")

    # Фото
    elif message.photo:
        largest_photo = message.photo[-1]
        bot.send_photo(target_id, largest_photo.file_id, caption=f"🖼 Фото от {message.from_user.id}")
        db.add_ticket_comment(0, message.from_user.id, "[PHOTO]")

# === Обработка текстов ===
def process_comment(message, tid):
    text = message.text.strip()
    db.add_ticket_comment(tid, message.from_user.id, text)
    bot.send_message(message.chat.id, "✅ Комментарий добавлен.")

def process_forward(message, tid):
    reason = message.text.strip()
    db.transfer_ticket_to_manager(tid, reason)
    bot.send_message(message.chat.id, f"🔁 Заявка #{tid} передана менеджеру.")

def rename_user(message):
    db.update_user_name(message.from_user.id, message.text.strip())
    bot.send_message(message.chat.id, "✅ Имя обновлено.")

# === Установка активной заявки для чата ===
@bot.callback_query_handler(func=lambda call: call.data.startswith("chat_ticket_"))
def set_chat_ticket(call):
    try:
        ticket_id = int(call.data.split("_")[2])
        uid = call.from_user.id
        if uid in chat_sessions:
            target_id, _ = chat_sessions[uid]
            chat_sessions[uid] = (target_id, ticket_id)
            chat_sessions[target_id] = (uid, ticket_id)
            bot.send_message(uid, f"🔗 Чат теперь привязан к заявке #{ticket_id}.")
            bot.send_message(target_id, f"🔗 Чат теперь привязан к заявке #{ticket_id}.")
    except:
        bot.send_message(call.message.chat.id, "⚠ Ошибка при установке заявки для чата.")

print("✅ Бот операторов и менеджеров запущен")
bot.infinity_polling()
