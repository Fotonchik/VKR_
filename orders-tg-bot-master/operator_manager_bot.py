# operator_manager_bot.py — панели менеджера и оператора с чатом, заявками и отчётами

import telebot
from telebot import types
import db_tickets as db_tickets
import config
import io
from fpdf import FPDF

db_tickets.init_db() 

bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode='HTML')

# === Проверка ролей ===
def is_operator(user_id):
    return user_id in config.TP_CHAT_ID or db_tickets.has_user_role(user_id, 'tp')

def is_manager(user_id):
    return user_id in config.MANAGER_CHAT_ID or db_tickets.has_user_role(user_id, 'manager')

# === Активные чаты: user_id -> (target_id, ticket_id) ===
chat_sessions = {}

# === Старт ===

@bot.message_handler(commands=['start'])
def start_handler(message):
    uid = message.from_user.id
    if is_manager(uid):
        return manager_panel(message)
    if is_operator(uid):
        return operator_panel(message)
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
        tickets = db_tickets.get_tickets_by_status(uid if data != "to_manager" else None, data)
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
        ticket = db_tickets.get_ticket_by_id(tid)
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
        comments = db_tickets.get_ticket_comments(tid)
        if not comments:
            return bot.send_message(call.message.chat.id, "📝 Комментариев нет.")
        text = "💬 Комментарии по заявке:\n\n"
        for c in comments:
            text += f"— <b>{c['author_id']}</b>: {c['text']}\n"
        bot.send_message(call.message.chat.id, text)

    elif data.startswith("client_"):
        cid = int(data.split("_")[1])
        client = db_tickets.get_client_by_id(cid)
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
        db_tickets.close_ticket(tid)
        bot.send_message(call.message.chat.id, f"✅ Заявка #{tid} закрыта.")

    elif data.startswith("approve_"):
        tid = int(data.split("_")[1])
        db_tickets.update_ticket_status(tid, "active")
        bot.send_message(call.message.chat.id, f"✅ Заявка #{tid} одобрена.")

    elif data.startswith("reject_"):
        tid = int(data.split("_")[1])
        db_tickets.update_ticket_status(tid, "open")
        bot.send_message(call.message.chat.id, f"❌ Заявка #{tid} отклонена и возвращена оператору.")

    elif data.startswith("chat_manager_"):
        operator_id = int(data.split("_")[2])
        managers = db_tickets.get_users_by_role("manager")
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

# === Обработка редактирования клиента ===
def process_edit_client_request(message):
    try:
        cid = int(message.text.strip())
        client = db_tickets.get_client_by_id(cid)
        if not client:
            return bot.send_message(message.chat.id, "❌ Клиент не найден.")
        bot.send_message(message.chat.id, f"Клиент найден: {client['name']}\nТекущий комментарий: {client['info']}")
        bot.send_message(message.chat.id, "✏ Введите новое имя клиента:")
        bot.register_next_step_handler(message, lambda m: process_client_name_update(m, cid))
    except:
        bot.send_message(message.chat.id, "⚠ Ошибка: введите корректный ID клиента")

def process_client_name_update(message, cid):
    new_name = message.text.strip()
    db_tickets.update_client_name(cid, new_name)
    bot.send_message(message.chat.id, "✅ Имя клиента обновлено. Введите новый комментарий:")
    bot.register_next_step_handler(message, lambda m: process_client_info_update(m, cid))

def process_client_info_update(message, cid):
    new_info = message.text.strip()
    db_tickets.update_client_info(cid, new_info)
    bot.send_message(message.chat.id, "✅ Комментарий обновлён.")

# === Отчёт в PDF ===
def process_report_range(message):
    bot.send_message(message.chat.id, "📂 Укажите статус заявок для отчёта (например: open, active, closed или all):")
    bot.register_next_step_handler(message, lambda m: process_report_status(message, m.text.strip().lower()))

def process_report_status(message, status):
    if status not in ["open", "active", "closed", "all"]:
        return bot.send_message(message.chat.id, "⚠ Неверный статус. Введите: open, active, closed или all")
    bot.send_message(message.chat.id, "📊 Введите диапазон дат для отчёта (пример: 2025-01-01:2025-12-31):")
    bot.register_next_step_handler(message, lambda m: generate_filtered_report(m, status))

def generate_filtered_report(message, status):
    try:
        dates = message.text.strip().split(":")
        start, end = dates[0], dates[1]
        rows = db_tickets.get_tickets_by_date_range(start, end)
        if status != "all":
            rows = [r for r in rows if r['status'] == status]
        if not rows:
            return bot.send_message(message.chat.id, "📭 Заявки не найдены в указанном диапазоне.")

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Отчёт по заявкам ({start} — {end})", ln=True, align="C")

        for row in rows:
            pdf.cell(200, 10, txt=f"#{row['id']}: {row['title']} / Статус: {row['status']}", ln=True)

        buffer = io.BytesIO()
        pdf.output(buffer)
        buffer.seek(0)
        bot.send_document(message.chat.id, buffer, visible_file_name="report.pdf")
    except:
        bot.send_message(message.chat.id, "❌ Ошибка генерации отчёта. Проверьте формат дат (YYYY-MM-DD:YYYY-MM-DD)")

# === Привязка чата для заявки ===
@bot.callback_query_handler(func=lambda call: call.data.startswith("chat_op_"))
def manager_chat_with_operator(call):
    try:
        tid = int(call.data.split("_")[2])
        ticket = db_tickets.get_ticket_by_id(tid)
        operator_id = ticket['operator_id']
        manager_id = call.from_user.id
        chat_sessions[operator_id] = (manager_id, tid)
        chat_sessions[manager_id] = (operator_id, tid)
        bot.send_message(manager_id, f"📞 Связь с оператором {operator_id} открыта по заявке #{tid}.")
        bot.send_message(operator_id, f"📞 Менеджер {manager_id} подключился к чату по заявке #{tid}.")
    except:
        bot.send_message(call.message.chat.id, "⚠ Не удалось подключить чат.")



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
        db_tickets.add_ticket_comment(ticket_id, message.from_user.id, f"[CHAT TEXT] {message.text}")

    # Документ
    elif message.document:
        bot.send_document(target_id, message.document.file_id, caption=f"📎 Документ от {message.from_user.id}")
        db_tickets.add_ticket_comment(ticket_id, message.from_user.id, f"[DOC] {message.document.file_name}")

    # Фото
    elif message.photo:
        largest_photo = message.photo[-1]
        bot.send_photo(target_id, largest_photo.file_id, caption=f"🖼 Фото от {message.from_user.id}")
        db_tickets.add_ticket_comment(ticket_id, message.from_user.id, "[PHOTO]")

    if message.from_user.id not in chat_sessions:
        return

    target_id = chat_sessions.get(message.from_user.id)
    if not target_id:
        return

    # Текст
    if message.text:
        bot.send_message(target_id, f"✉️ <b>{message.from_user.id}</b>: {message.text}")
        db_tickets.add_ticket_comment(0, message.from_user.id, f"[CHAT TEXT] {message.text}")

    # Документ
    elif message.document:
        bot.send_document(target_id, message.document.file_id, caption=f"📎 Документ от {message.from_user.id}")
        db_tickets.add_ticket_comment(0, message.from_user.id, f"[DOC] {message.document.file_name}")

    # Фото
    elif message.photo:
        largest_photo = message.photo[-1]
        bot.send_photo(target_id, largest_photo.file_id, caption=f"🖼 Фото от {message.from_user.id}")
        db_tickets.add_ticket_comment(0, message.from_user.id, "[PHOTO]")

# === Обработка текстов ===
def process_comment(message, tid):
    text = message.text.strip()
    db_tickets.add_ticket_comment(tid, message.from_user.id, text)
    bot.send_message(message.chat.id, "✅ Комментарий добавлен.")

def process_forward(message, tid):
    reason = message.text.strip()
    db_tickets.transfer_ticket_to_manager(tid, reason)
    bot.send_message(message.chat.id, f"🔁 Заявка #{tid} передана менеджеру.")

def rename_user(message):
    db_tickets.update_user_name(message.from_user.id, message.text.strip())
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

# === Завершение чата ===
@bot.message_handler(commands=['stopchat'])
def stop_chat(message):
    uid = message.from_user.id
    partner = chat_sessions.pop(uid, None)
    if partner:
        chat_sessions.pop(partner[0], None)
        bot.send_message(uid, "❎ Чат завершён.")
        bot.send_message(partner[0], "❎ Ваш собеседник завершил чат.")

# === Меню менеджера ===
@bot.message_handler(commands=['manager'])
def manager_panel(message):
    if not is_manager(message.from_user.id):
        return bot.send_message(message.chat.id, "⛔ Нет доступа")

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📄 Активные заявки", callback_data="manager_active"))
    kb.add(types.InlineKeyboardButton("🗂 Управление учётной записью", callback_data="manager_account"))
    kb.add(types.InlineKeyboardButton("✏ Справка по клиенту", callback_data="manager_edit_client"))
    kb.add(types.InlineKeyboardButton("📤 Запрос админу", callback_data="manager_request_admin"))
    kb.add(types.InlineKeyboardButton("📊 Составить отчёт", callback_data="manager_report"))
    bot.send_message(message.chat.id, "📋 Меню менеджера:", reply_markup=kb)


def process_admin_request(message):
    text = message.text.strip()
    db_tickets.add_ticket_comment(0, message.from_user.id, f"[ADMIN REQUEST] {text}")
    bot.send_message(message.chat.id, "📨 Запрос администратору отправлен.")

# === Обработка кнопок менеджера ===
@bot.callback_query_handler(func=lambda c: c.data.startswith("manager_"))
def manager_callbacks(call):
    uid = call.from_user.id
    if not is_manager(uid):
        return bot.answer_callback_query(call.id, "⛔ Нет доступа")

    action = call.data.split("_")[1]

    if action == "active":
        tickets = db_tickets.get_tickets_by_status(None, "active")
        if not tickets:
            return bot.send_message(call.message.chat.id, "📭 Нет активных заявок.")
        for t in tickets:
            tid = t['id']
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("👁 Просмотр", callback_data=f"view_{tid}"))
            kb.add(types.InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{tid}"))
            kb.add(types.InlineKeyboardButton("❌ Закрыть", callback_data=f"close_{tid}"))
            kb.add(types.InlineKeyboardButton("📞 Чат с оператором", callback_data=f"chat_op_{tid}"))
            bot.send_message(call.message.chat.id, f"📝 Заявка #{tid}: {t['title']}", reply_markup=kb)

    elif action == "account":
        bot.send_message(call.message.chat.id, "👤 Вы можете использовать /rename для смены имени.")

    elif action == "edit":
        bot.send_message(call.message.chat.id, "✍ Введите ID клиента для редактирования:")
        bot.register_next_step_handler(call.message, process_edit_client_request)

    elif action == "request":
        bot.send_message(call.message.chat.id, "📝 Введите текст запроса администратору:")
        bot.register_next_step_handler(call.message, process_admin_request)

    elif action == "report":
        bot.send_message(call.message.chat.id, "📊 Введите диапазон дат для отчёта (пример: 2025-01-01:2025-12-31):")
        bot.register_next_step_handler(call.message, process_report_range)

# === Завершение ===
def process_comment(message, tid):
    text = message.text.strip()
    db_tickets.add_ticket_comment(tid, message.from_user.id, text)
    bot.send_message(message.chat.id, "✅ Комментарий добавлен.")

def process_forward(message, tid):
    reason = message.text.strip()
    db_tickets.transfer_ticket_to_manager(tid, reason)
    bot.send_message(message.chat.id, f"🔁 Заявка #{tid} передана менеджеру.")

def rename_user(message):
    db_tickets.update_user_name(message.from_user.id, message.text.strip())
    bot.send_message(message.chat.id, "✅ Имя обновлено.")

def process_edit_client_request(message):
    try:
        cid = int(message.text.strip())
        client = db_tickets.get_client_by_id(cid)
        if not client:
            return bot.send_message(message.chat.id, "❌ Клиент не найден.")
        bot.send_message(message.chat.id, f"Найден клиент: {client['name']}\nКомментарий: {client['info']}")
        bot.send_message(message.chat.id, "✏ Введите новое имя:")
        bot.register_next_step_handler(message, lambda m: process_client_name_update(m, cid))
    except:
        bot.send_message(message.chat.id, "⚠ Введите корректный ID клиента")

def process_client_name_update(message, cid):
    new_name = message.text.strip()
    db_tickets.update_client_name(cid, new_name)
    bot.send_message(message.chat.id, "✅ Имя обновлено. Введите новый комментарий:")
    bot.register_next_step_handler(message, lambda m: process_client_info_update(m, cid))

def process_client_info_update(message, cid):
    new_info = message.text.strip()
    db_tickets.update_client_info(cid, new_info)
    bot.send_message(message.chat.id, "✅ Комментарий обновлён.")

# === Генерация PDF отчёта по заявкам ===
def process_report_status(message, status):
    if status not in ["open", "active", "closed", "all"]:
        return bot.send_message(message.chat.id, "⚠ Неверный статус. Введите: open, active, closed или all")
    bot.send_message(message.chat.id, "📊 Введите диапазон дат (пример: 2025-01-01:2025-12-31):")
    bot.register_next_step_handler(message, lambda m: generate_filtered_report(m, status))

def generate_filtered_report(message, status):
    try:
        dates = message.text.strip().split(":")
        start, end = dates[0], dates[1]
        rows = db_tickets.get_tickets_by_date_range(start, end)

        if status != "all":
            rows = [r for r in rows if r['status'] == status]

        if not rows:
            return bot.send_message(message.chat.id, "📭 Заявки не найдены.")

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Отчёт по заявкам ({start} — {end})", ln=True, align="C")

        for row in rows:
            pdf.cell(200, 10, txt=f"#{row['id']}: {row['title']} / Статус: {row['status']}", ln=True)

        buffer = io.BytesIO()
        pdf.output(buffer)
        buffer.seek(0)
        bot.send_document(message.chat.id, buffer, visible_file_name="report.pdf")

    except Exception as e:
        bot.send_message(message.chat.id, "❌ Ошибка генерации отчёта. Проверьте формат и данные.")

print("✅ Бот операторов и менеджеров запущен")
# bot.infinity_polling()
