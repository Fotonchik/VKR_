# operator_manager_bot.py — панели менеджера и оператора с чатом, заявками и отчётами

from telebot import types
import db_tickets as db_tickets
import config
import io
try:
    from fpdf import FPDF
except ImportError:
    try:
        from fpdf2 import FPDF
    except ImportError:
        FPDF = None
        print("⚠ Предупреждение: fpdf/fpdf2 не установлен. Функция генерации PDF не будет работать.")

# Инициализация БД заявок (будет вызвано при импорте)
db_tickets.init_ticket_db()

# === Проверка ролей ===
def is_operator(user_id):
    return user_id in config.TP_CHAT_ID or db_tickets.has_user_role(user_id, 'tp')

def is_manager(user_id):
    return user_id in config.MANAGER_CHAT_ID or db_tickets.has_user_role(user_id, 'manager')

# === Активные чаты: user_id -> (target_id, ticket_id) ===
chat_sessions = {}

# === Старт (удалено - теперь обрабатывается в main_bot.py) ===


# === Панель оператора ===
def operator_panel(bot, message):
    # Подсчитываем количество новых заявок
    open_tickets = db_tickets.get_open_tickets()
    active_tickets = db_tickets.get_tickets_by_status(message.from_user.id, 'active')
    closed_tickets = db_tickets.get_tickets_by_status(message.from_user.id, 'closed')
    
    open_count = len(open_tickets)
    active_count = len(active_tickets) if active_tickets else 0
    closed_count = len(closed_tickets) if closed_tickets else 0
    
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(f"🟡 Открытые ({open_count})", callback_data="open"))
    kb.add(types.InlineKeyboardButton(f"🟢 Активные ({active_count})", callback_data="active"))
    kb.add(types.InlineKeyboardButton(f"🔴 Закрытые ({closed_count})", callback_data="closed"))
    kb.add(types.InlineKeyboardButton("👤 Учётная запись", callback_data="account"))
    
    panel_text = "🧑‍💻 Панель оператора:\n\n"
    if open_count > 0:
        panel_text += f"⚠️ У вас {open_count} новых заявок, ожидающих обработки!\n\n"
    panel_text += "Выберите раздел:"
    
    bot.send_message(message.chat.id, panel_text, reply_markup=kb)

# === Панель менеджера ===
def manager_panel(bot, message):
    # Подсчитываем количество заявок
    to_manager_tickets = db_tickets.get_tickets_by_status(None, "to_manager")
    active_tickets = db_tickets.get_tickets_by_status(None, "active")
    
    to_manager_count = len(to_manager_tickets) if to_manager_tickets else 0
    active_count = len(active_tickets) if active_tickets else 0
    
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(f"📨 Запросы от операторов ({to_manager_count})", callback_data="to_manager"))
    kb.add(types.InlineKeyboardButton(f"🟢 Активные заявки ({active_count})", callback_data="manager_active"))
    
    panel_text = "👔 Панель менеджера:\n\n"
    if to_manager_count > 0:
        panel_text += f"⚠️ У вас {to_manager_count} заявок, требующих внимания!\n\n"
    panel_text += "Выберите раздел:"
    
    bot.send_message(message.chat.id, panel_text, reply_markup=kb)

# === Обработка callback ===
def handle_operator_manager_callbacks(bot, call):
    uid = call.from_user.id
    data = call.data

    if data in ["open", "closed", "active", "to_manager"]:
        role_check = is_operator(uid) if data != "to_manager" else is_manager(uid)
        # Исправляем вызов get_tickets_by_status
        if data == "to_manager":
            tickets = db_tickets.get_tickets_by_status(None, "to_manager")
        elif data == "open":
            # Для открытых заявок показываем все (включая без оператора)
            tickets = db_tickets.get_open_tickets()
        else:
            tickets = db_tickets.get_tickets_by_status(uid, data)
        
        if not role_check or not tickets:
            status_names = {
                "open": "открытых",
                "active": "активных", 
                "closed": "закрытых",
                "to_manager": "переданных менеджеру"
            }
            status_name = status_names.get(data, data)
            return bot.send_message(call.message.chat.id, f"📭 Нет {status_name} заявок.")
        
        # Формируем список заявок с информацией
        status_emoji = {"open": "🟡", "active": "🟢", "closed": "🔴", "to_manager": "📨"}
        emoji = status_emoji.get(data, "📌")
        
        for t in tickets:
            tid = t['id']
            title = t.get('title', 'Без названия')
            created_at = t.get('created_at', '')
            operator_id = t.get('operator_id')
            
            # Форматируем дату
            date_str = ""
            if created_at:
                try:
                    from datetime import datetime
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        date_str = dt.strftime("%d.%m.%Y %H:%M")
                    else:
                        date_str = str(created_at)[:16]
                except:
                    date_str = str(created_at)[:16] if created_at else ""
            
            # Формируем текст заявки
            ticket_text = f"{emoji} <b>Заявка #{tid}</b>\n"
            ticket_text += f"📝 {title[:100]}\n"
            if date_str:
                ticket_text += f"📅 {date_str}\n"
            if operator_id and data == "open":
                ticket_text += f"👤 Назначена оператору\n"
            elif not operator_id and data == "open":
                ticket_text += f"⚠️ Требует назначения\n"
            
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("🔍 Открыть", callback_data=f"view_{tid}"))
            if data == "open" and not operator_id:
                kb.add(types.InlineKeyboardButton("✅ Взять в работу", callback_data=f"take_{tid}"))
            
            bot.send_message(call.message.chat.id, ticket_text, reply_markup=kb)

    elif data.startswith("view_"):
        try:
            tid = int(data.split("_")[1])
            ticket = db_tickets.get_ticket_by_id(tid)
            if not ticket:
                return bot.send_message(call.message.chat.id, "❌ Заявка не найдена")

            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("📄 Добавить информацию", callback_data=f"comment_{tid}"))
            kb.add(types.InlineKeyboardButton("💬 Комментарии", callback_data=f"comments_{tid}"))
            client_id = ticket.get('client_id', 0)
            if client_id:
                kb.add(types.InlineKeyboardButton("👤 Данные клиента", callback_data=f"client_{client_id}"))
            ticket_status = ticket.get('status', '')
            if ticket_status == 'to_manager' and is_manager(uid):
                kb.add(types.InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{tid}"))
                kb.add(types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{tid}"))
            else:
                kb.add(types.InlineKeyboardButton("🔁 Передать менеджеру", callback_data=f"forward_{tid}"))
                kb.add(types.InlineKeyboardButton("✅ Закрыть заявку", callback_data=f"close_{tid}"))
                kb.add(types.InlineKeyboardButton("📬 Связь с менеджером", callback_data=f"chat_manager_{uid}"))

            ticket_title = ticket.get('title', 'Без названия')
            ticket_desc = ticket.get('description', ticket_title)
            ticket_id = ticket.get('id', tid)
            ticket_status = ticket.get('status', 'open')
            created_at = ticket.get('created_at', '')
            operator_id = ticket.get('operator_id')
            
            # Получаем информацию о клиенте
            client_info = ""
            client_id = ticket.get('client_id', 0)
            if client_id:
                client = db_tickets.get_client_by_id(client_id)
                if client:
                    client_info = f"👤 Клиент: <b>{client.get('name', 'Неизвестный')}</b> (ID: {client_id})\n"
            
            # Форматируем дату
            date_str = ""
            if created_at:
                try:
                    from datetime import datetime
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        date_str = dt.strftime("%d.%m.%Y %H:%M")
                    else:
                        date_str = str(created_at)[:16]
                except:
                    date_str = str(created_at)[:16] if created_at else ""
            
            # Статусы
            status_names = {
                "open": "🟡 Открыта",
                "active": "🟢 В работе",
                "closed": "🔴 Закрыта",
                "to_manager": "📨 Передана менеджеру"
            }
            status_text = status_names.get(ticket_status, ticket_status)
            
            # Формируем полное описание заявки
            ticket_info = f"📌 <b>Заявка #{ticket_id}</b>\n\n"
            ticket_info += f"{status_text}\n"
            if date_str:
                ticket_info += f"📅 Создана: {date_str}\n"
            ticket_info += f"\n{client_info}"
            ticket_info += f"\n📝 <b>Описание:</b>\n{ticket_desc[:500]}"
            if len(ticket_desc) > 500:
                ticket_info += "..."
            
            if operator_id:
                ticket_info += f"\n\n👨‍💻 Оператор: {operator_id}"
            
            bot.send_message(call.message.chat.id, ticket_info, reply_markup=kb)
        except (ValueError, IndexError, KeyError) as e:
            bot.send_message(call.message.chat.id, f"❌ Ошибка при открытии заявки: {e}")

    elif data.startswith("comment_"):
        tid = int(data.split("_")[1])
        bot.send_message(call.message.chat.id, "📝 Введите комментарий:")
        bot.register_next_step_handler(call.message, lambda m: process_comment(bot, m, tid))

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
        try:
            cid = int(data.split("_")[1])
            client = db_tickets.get_client_by_id(cid)
            if client:
                client_name = client.get('name', 'Неизвестно')
                client_info = client.get('info', '—')
                bot.send_message(call.message.chat.id, f"👤 Клиент #{cid}\nИмя: <b>{client_name}</b>\nКомментарий: {client_info}")
            else:
                bot.send_message(call.message.chat.id, "❌ Клиент не найден.")
        except (ValueError, IndexError):
            bot.send_message(call.message.chat.id, "❌ Неверный ID клиента.")

    elif data.startswith("forward_"):
        tid = int(data.split("_")[1])
        bot.send_message(call.message.chat.id, "📝 Введите причину передачи заявки менеджеру:")
        bot.register_next_step_handler(call.message, lambda m: process_forward(bot, m, tid))

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
        try:
            operator_id = int(data.split("_")[2])
            managers = db_tickets.get_users_by_role("manager")
            kb = types.InlineKeyboardMarkup()
            for uid, name in managers:
                kb.add(types.InlineKeyboardButton(name, callback_data=f"chat_with_{uid}_{operator_id}"))
            bot.send_message(call.message.chat.id, "👔 Выберите менеджера для связи:", reply_markup=kb)
        except (IndexError, ValueError):
            bot.send_message(call.message.chat.id, "⚠ Ошибка при получении списка менеджеров.")

    elif data.startswith("chat_with_"):
        parts = data.split("_")
        mid = int(parts[2])
        opid = int(parts[3])
        chat_sessions[opid] = mid
        chat_sessions[mid] = opid
        bot.send_message(mid, f"📞 Связь с оператором <code>{opid}</code> открыта. Напишите сообщение:")
        bot.send_message(opid, f"📞 Связь с менеджером <code>{mid}</code> открыта. Напишите сообщение:")
    
    elif data.startswith("chat_op_"):
        manager_chat_with_operator(bot, call)
    
    elif data.startswith("chat_ticket_"):
        set_chat_ticket(bot, call)

    elif data == "account":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("✏ Изменить имя", callback_data="rename"))
        bot.send_message(call.message.chat.id, "👤 Учётная запись:", reply_markup=kb)

    elif data == "rename":
        bot.send_message(call.message.chat.id, "✏ Введите новое имя:")
        bot.register_next_step_handler(call.message, lambda m: rename_user(bot, m))

# === Привязка чата для заявки ===
def manager_chat_with_operator(bot, call):
    """Обрабатывает подключение менеджера к чату с оператором"""
    try:
        tid = int(call.data.split("_")[2])
        ticket = db_tickets.get_ticket_by_id(tid)
        if not ticket:
            return bot.send_message(call.message.chat.id, "❌ Заявка не найдена.")
        operator_id = ticket.get('operator_id')
        manager_id = call.from_user.id
        chat_sessions[operator_id] = (manager_id, tid)
        chat_sessions[manager_id] = (operator_id, tid)
        bot.send_message(manager_id, f"📞 Связь с оператором {operator_id} открыта по заявке #{tid}.")
        bot.send_message(operator_id, f"📞 Менеджер {manager_id} подключился к чату по заявке #{tid}.")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"⚠ Не удалось подключить чат: {e}")



# === Текстовые сообщения для чата (будет обрабатываться в main_bot) ===
def relay_chat_message(bot, message):
    if message.from_user.id not in chat_sessions:
        return

    session_data = chat_sessions.get(message.from_user.id)
    if not session_data:
        return
    
    # Поддержка двух форматов: (target_id, ticket_id) или просто target_id
    if isinstance(session_data, tuple):
        target_id, ticket_id = session_data
    else:
        target_id = session_data
        ticket_id = 0

    if not target_id:
        return

    # Текст
    if message.text:
        bot.send_message(target_id, f"✉️ <b>{message.from_user.id}</b>: {message.text}")
        if ticket_id:
            db_tickets.add_ticket_comment(ticket_id, message.from_user.id, f"[CHAT TEXT] {message.text}")

    # Документ
    elif message.document:
        bot.send_document(target_id, message.document.file_id, caption=f"📎 Документ от {message.from_user.id}")
        if ticket_id:
            db_tickets.add_ticket_comment(ticket_id, message.from_user.id, f"[DOC] {message.document.file_name}")

    # Фото
    elif message.photo:
        largest_photo = message.photo[-1]
        bot.send_photo(target_id, largest_photo.file_id, caption=f"🖼 Фото от {message.from_user.id}")
        if ticket_id:
            db_tickets.add_ticket_comment(ticket_id, message.from_user.id, "[PHOTO]")

# === Обработка текстов ===
def process_comment(bot, message, tid):
    text = message.text.strip() if message.text else ""
    db_tickets.add_ticket_comment(tid, message.from_user.id, text)
    bot.send_message(message.chat.id, "✅ Комментарий добавлен.")

def process_forward(bot, message, tid):
    reason = message.text.strip() if message.text else ""
    db_tickets.transfer_ticket_to_manager(tid, reason)
    bot.send_message(message.chat.id, f"🔁 Заявка #{tid} передана менеджеру.")

def rename_user(bot, message):
    if message.text:
        db_tickets.update_user_name(message.from_user.id, message.text.strip())
        bot.send_message(message.chat.id, "✅ Имя обновлено.")

# === Установка активной заявки для чата ===
def set_chat_ticket(bot, call):
    """Привязывает чат к заявке"""
    try:
        ticket_id = int(call.data.split("_")[2])
        uid = call.from_user.id
        if uid in chat_sessions:
            session_data = chat_sessions[uid]
            if isinstance(session_data, tuple):
                target_id, _ = session_data
            else:
                target_id = session_data
            chat_sessions[uid] = (target_id, ticket_id)
            chat_sessions[target_id] = (uid, ticket_id)
            bot.send_message(uid, f"🔗 Чат теперь привязан к заявке #{ticket_id}.")
            bot.send_message(target_id, f"🔗 Чат теперь привязан к заявке #{ticket_id}.")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"⚠ Ошибка при установке заявки для чата: {e}")

# === Завершение чата ===
def stop_chat(bot, message):
    uid = message.from_user.id
    partner = chat_sessions.pop(uid, None)
    if partner:
        chat_sessions.pop(partner[0], None)
        bot.send_message(uid, "❎ Чат завершён.")
        bot.send_message(partner[0], "❎ Ваш собеседник завершил чат.")

# === Меню менеджера (обновленная версия) ===
def manager_panel_full(bot, message):
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
def handle_manager_callbacks(bot, call):
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
        bot.register_next_step_handler(call.message, lambda m: process_edit_client_request(bot, m))

    elif action == "request":
        bot.send_message(call.message.chat.id, "📝 Введите текст запроса администратору:")
        bot.register_next_step_handler(call.message, lambda m: process_admin_request(bot, m))

    elif action == "report":
        bot.send_message(call.message.chat.id, "📊 Введите диапазон дат для отчёта (пример: 2025-01-01:2025-12-31):")
        bot.register_next_step_handler(call.message, lambda m: process_report_range(bot, m))

# === Вспомогательные функции ===
def process_edit_client_request(bot, message):
    try:
        cid = int(message.text.strip()) if message.text else 0
        client = db_tickets.get_client_by_id(cid)
        if not client:
            return bot.send_message(message.chat.id, "❌ Клиент не найден.")
        bot.send_message(message.chat.id, f"Найден клиент: {client.get('name', 'Неизвестно')}\nКомментарий: {client.get('info', '—')}")
        bot.send_message(message.chat.id, "✏ Введите новое имя:")
        bot.register_next_step_handler(message, lambda m: process_client_name_update(bot, m, cid))
    except (ValueError, TypeError):
        bot.send_message(message.chat.id, "⚠ Введите корректный ID клиента")

def process_client_name_update(bot, message, cid):
    if message.text:
        new_name = message.text.strip()
        db_tickets.update_client_name(cid, new_name)
        bot.send_message(message.chat.id, "✅ Имя обновлено. Введите новый комментарий:")
        bot.register_next_step_handler(message, lambda m: process_client_info_update(bot, m, cid))

def process_client_info_update(bot, message, cid):
    if message.text:
        new_info = message.text.strip()
        db_tickets.update_client_info(cid, new_info)
        bot.send_message(message.chat.id, "✅ Комментарий обновлён.")

def process_admin_request(bot, message):
    if message.text:
        text = message.text.strip()
        db_tickets.add_ticket_comment(0, message.from_user.id, f"[ADMIN REQUEST] {text}")
        bot.send_message(message.chat.id, "📨 Запрос администратору отправлен.")

def process_report_range(bot, message):
    if message.text:
        bot.send_message(message.chat.id, "📊 Введите диапазон дат для отчёта (пример: 2025-01-01:2025-12-31):")
        bot.register_next_step_handler(message, lambda m: generate_filtered_report(bot, m, "all"))

# === Генерация PDF отчёта по заявкам ===
def generate_filtered_report(bot, message, status):
    try:
        dates = message.text.strip().split(":")
        start, end = dates[0], dates[1]
        rows = db_tickets.get_tickets_by_date_range(start, end)

        if status != "all":
            rows = [r for r in rows if r['status'] == status]

        if not rows:
            return bot.send_message(message.chat.id, "📭 Заявки не найдены.")

        try:
            if FPDF is None:
                return bot.send_message(message.chat.id, "❌ Библиотека для генерации PDF не установлена. Установите fpdf2.")
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=f"Отчёт по заявкам ({start} — {end})", ln=True, align="C")

            for row in rows:
                row_id = row.get('id', 'N/A')
                row_title = row.get('title', 'Без названия')
                row_status = row.get('status', 'N/A')
                pdf.cell(200, 10, txt=f"#{row_id}: {row_title} / Статус: {row_status}", ln=True)

            buffer = io.BytesIO()
            pdf.output(buffer)
            buffer.seek(0)
            bot.send_document(message.chat.id, buffer, visible_file_name="report.pdf")
        except Exception as pdf_error:
            bot.send_message(message.chat.id, f"❌ Ошибка генерации PDF: {pdf_error}")

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка генерации отчёта: {e}")

# Бот инициализируется в main_bot.py
