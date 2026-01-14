# main_bot.py — стартовый бот, переключающий панели по ролям

import telebot
from telebot import types
import config
import db
import db_tickets
import operator_manager_bot
import admin_bot
import time
import sys

# Инициализация бота
print("🔧 Инициализация бота...")
try:
    bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode="HTML")
    print("✅ Бот инициализирован")
except Exception as e:
    print(f"❌ Ошибка при инициализации бота: {e}")
    sys.exit(1)

# Проверка подключения к Telegram API
print("🔍 Проверка подключения к Telegram API...")
try:
    bot_info = bot.get_me()
    print(f"✅ Подключение успешно! Бот: @{bot_info.username}")
except Exception as e:
    print(f"❌ Ошибка подключения к Telegram API: {e}")
    print("\n💡 Возможные причины:")
    print("   1. Проблемы с интернет-соединением")
    print("   2. Файрвол или антивирус блокирует соединение")
    print("   3. Неверный токен бота (проверьте config.py)")
    print("   4. Проблемы с SSL сертификатами")
    print("\n🔧 Попробуйте:")
    print("   - Проверить интернет-соединение")
    print("   - Временно отключить антивирус/файрвол")
    print("   - Проверить токен бота в @BotFather")
    print("   - Использовать VPN, если Telegram заблокирован")
    sys.exit(1)

# Инициализация баз данных
db.check_database()
db.ensure_and_get_users()
db_tickets.init_ticket_db()

# === Команда /start — проверка роли ===
@bot.message_handler(commands=['start'])
def handle_start(message):
    uid = message.from_user.id
    if db.has_access(uid, ['admin']):
        return admin_bot.admin_panel(bot, message)
    elif operator_manager_bot.is_operator(uid):
        return operator_manager_bot.operator_panel(bot, message)
    elif operator_manager_bot.is_manager(uid):
        return operator_manager_bot.manager_panel(bot, message)
    else:
        # Клиент - показываем приветствие и инструкции
        welcome_text = (
            "👋 Добро пожаловать!\n\n"
            "Я помогу вам связаться с нашей службой поддержки.\n\n"
            "💬 Просто напишите ваше сообщение, и я создам заявку.\n"
            "Оператор свяжется с вами в ближайшее время.\n\n"
            "📝 Вы можете описать проблему, задать вопрос или оставить обращение."
        )
        bot.send_message(message.chat.id, welcome_text)

# === Команда /admin — панель администратора ===
@bot.message_handler(commands=['admin'])
def handle_admin(message):
    if db.has_access(message.from_user.id, ['admin']):
        admin_bot.admin_panel(bot, message)
    else:
        bot.send_message(message.chat.id, "❌ У вас нет доступа к административной панели.")

# === Обработка callback-запросов ===
@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    """Обрабатывает все callback-запросы и направляет их в соответствующие модули"""
    uid = call.from_user.id
    data = call.data
    
    # Проверяем, является ли пользователь администратором
    if db.has_access(uid, ['admin']):
        # Администраторские callback
        admin_bot.handle_admin_callback(bot, call)
        return
    
    # Проверяем оператора или менеджера
    if operator_manager_bot.is_manager(uid):
        # Callback менеджера
        if data.startswith("manager_"):
            operator_manager_bot.handle_manager_callbacks(bot, call)
        elif data.startswith("chat_op_") or data.startswith("chat_ticket_"):
            # Специальные обработчики для менеджера
            if data.startswith("chat_op_"):
                operator_manager_bot.manager_chat_with_operator(bot, call)
            elif data.startswith("chat_ticket_"):
                operator_manager_bot.set_chat_ticket(bot, call)
        else:
            operator_manager_bot.handle_operator_manager_callbacks(bot, call)
        return
    
    if operator_manager_bot.is_operator(uid):
        # Callback оператора
        if data.startswith("take_"):
            # Принятие заявки оператором
            try:
                ticket_id = int(data.split("_")[1])
                db_tickets.assign_ticket_to_operator(ticket_id, uid)
                ticket = db_tickets.get_ticket_by_id(ticket_id)
                if ticket:
                    client = db_tickets.get_client_by_id(ticket.get('client_id', 0))
                    client_name = client.get('name', 'Неизвестный') if client else 'Неизвестный'
                    bot.answer_callback_query(call.id, f"✅ Заявка #{ticket_id} принята в работу")
                    bot.send_message(
                        call.message.chat.id,
                        f"✅ Вы приняли заявку #{ticket_id} в работу.\n"
                        f"👤 Клиент: {client_name}\n"
                        f"📝 Текст: {ticket.get('title', 'Без описания')}"
                    )
                    # Уведомляем клиента
                    try:
                        bot.send_message(
                            ticket.get('client_id'),
                            f"✅ Ваша заявка #{ticket_id} принята оператором в работу. Ожидайте ответа."
                        )
                    except:
                        pass
                else:
                    bot.answer_callback_query(call.id, "❌ Заявка не найдена")
            except Exception as e:
                bot.answer_callback_query(call.id, f"❌ Ошибка: {e}")
        elif data.startswith("chat_ticket_"):
            operator_manager_bot.set_chat_ticket(bot, call)
        else:
            operator_manager_bot.handle_operator_manager_callbacks(bot, call)
        return
    
    # Нет доступа
    bot.answer_callback_query(call.id, "❌ Нет доступа")

# === Обработка текстовых сообщений ===
@bot.message_handler(content_types=['text', 'photo', 'document'])
def handle_messages(message):
    """Обрабатывает текстовые сообщения, фото и документы"""
    uid = message.from_user.id
    
    # Проверяем, есть ли активная сессия чата между оператором и менеджером
    if uid in operator_manager_bot.chat_sessions:
        operator_manager_bot.relay_chat_message(bot, message)
        return
    
    # Если пользователь - админ, оператор или менеджер, игнорируем (у них есть свои панели)
    if db.has_access(uid, ['admin']) or operator_manager_bot.is_operator(uid) or operator_manager_bot.is_manager(uid):
        return
    
    # Если это клиент - создаем заявку
    if message.text:
        create_ticket_from_message(message)
    elif message.photo or message.document:
        # Для фото и документов создаем заявку с описанием типа контента
        create_ticket_from_message(message)

def create_ticket_from_message(message):
    """Создает заявку от клиента и уведомляет операторов"""
    client_id = message.from_user.id
    client_name = message.from_user.first_name or "Неизвестный"
    
    # Формируем текст заявки
    if message.text:
        message_text = message.text
    elif message.photo:
        message_text = f"[Фото] {message.caption or 'Клиент отправил фотографию'}"
    elif message.document:
        message_text = f"[Документ: {message.document.file_name}] {message.caption or 'Клиент отправил документ'}"
    else:
        message_text = "Новое сообщение от клиента"
    
    # Создаем заявку
    try:
        ticket_id = db_tickets.create_ticket_from_client(client_id, client_name, message_text)
        
        # Уведомляем клиента
        bot.send_message(
            client_id,
            f"✅ Ваша заявка #{ticket_id} создана и передана оператору.\n"
            f"📝 Текст: {message_text[:200]}"
        )
        
        # Уведомляем всех операторов о новой заявке
        notify_operators_about_new_ticket(ticket_id, client_name, message_text)
        
    except Exception as e:
        print(f"❌ Ошибка при создании заявки: {e}")
        bot.send_message(client_id, "❌ Произошла ошибка при создании заявки. Попробуйте позже.")

def notify_operators_about_new_ticket(ticket_id, client_name, message_text):
    """Уведомляет всех операторов о новой заявке"""
    try:
        # Получаем всех операторов из конфига и БД
        operators = []
        
        # Операторы из конфига
        if hasattr(config, 'TP_CHAT_ID'):
            operators.extend(config.TP_CHAT_ID)
        
        # Операторы из БД
        db_operators = db_tickets.get_users_by_role('tp')
        operators.extend([op[0] for op in db_operators])
        
        # Убираем дубликаты
        operators = list(set(operators))
        
        # Формируем сообщение
        ticket_text = message_text[:300] + "..." if len(message_text) > 300 else message_text
        notification = (
            f"🔔 <b>Новая заявка #{ticket_id}</b>\n\n"
            f"👤 Клиент: <b>{client_name}</b>\n"
            f"📝 Сообщение: {ticket_text}\n\n"
            f"Используйте панель оператора для просмотра и принятия заявки."
        )
        
        # Отправляем уведомления
        for operator_id in operators:
            try:
                kb = types.InlineKeyboardMarkup()
                kb.add(types.InlineKeyboardButton("📋 Открыть заявку", callback_data=f"view_{ticket_id}"))
                kb.add(types.InlineKeyboardButton("✅ Взять в работу", callback_data=f"take_{ticket_id}"))
                bot.send_message(operator_id, notification, reply_markup=kb)
            except Exception as e:
                print(f"❌ Не удалось отправить уведомление оператору {operator_id}: {e}")
                
    except Exception as e:
        print(f"❌ Ошибка при уведомлении операторов: {e}")

# Запуск бота
if __name__ == "__main__":
    print("\n🚀 Запуск бота...")
    print("=" * 50)
    
    retry_count = 0
    max_retries = 5
    
    while retry_count < max_retries:
        try:
            print(f"🔄 Попытка подключения {retry_count + 1}/{max_retries}...")
            bot.infinity_polling(none_stop=True, interval=0, timeout=20, long_polling_timeout=20)
        except KeyboardInterrupt:
            print("\n⏹ Остановка бота по запросу пользователя")
            break
        except Exception as e:
            error_msg = str(e)
            
            # Специальная обработка ошибки 409 (конфликт экземпляров)
            if "409" in error_msg or "Conflict" in error_msg or "other getUpdates" in error_msg:
                print("\n" + "=" * 60)
                print("⚠️ ОШИБКА: Обнаружен конфликт экземпляров бота!")
                print("=" * 60)
                print("\n💡 Проблема: Запущено несколько экземпляров бота одновременно.")
                print("   Telegram API позволяет только один активный экземпляр.\n")
                print("📋 Решение:")
                print("   1. Запустите файл stop_bot.bat для остановки всех процессов")
                print("      ИЛИ выполните команду: taskkill /F /IM python.exe")
                print("   2. Подождите 5-10 секунд")
                print("   3. Запустите бота снова: python main_bot.py\n")
                print("🔍 Проверка запущенных процессов Python:")
                import subprocess
                try:
                    result = subprocess.run(['tasklist'], capture_output=True, text=True, shell=True)
                    python_processes = [line for line in result.stdout.split('\n') if 'python.exe' in line]
                    if python_processes:
                        print("   Найдены процессы:")
                        for proc in python_processes:
                            print(f"   - {proc.strip()}")
                    else:
                        print("   Процессы Python не найдены")
                except:
                    print("   Не удалось проверить процессы")
                print("\n" + "=" * 60)
                sys.exit(1)  # Немедленно останавливаем, так как нужно вручную решить проблему
            
            retry_count += 1
            print(f"❌ Ошибка при работе бота (попытка {retry_count}/{max_retries}): {error_msg}")
            
            if "SSL" in error_msg or "SSLError" in error_msg:
                print("🔒 Обнаружена SSL ошибка")
                print("💡 Попробуйте:")
                print("   - Проверить интернет-соединение")
                print("   - Отключить VPN/прокси, если используется")
                print("   - Проверить настройки файрвола")
            
            if retry_count < max_retries:
                wait_time = min(2 ** retry_count, 30)  # Экспоненциальная задержка, максимум 30 сек
                print(f"⏳ Повторная попытка через {wait_time} секунд...")
                time.sleep(wait_time)
            else:
                print("\n❌ Превышено максимальное количество попыток")
                print("💡 Проверьте:")
                print("   1. Интернет-соединение")
                print("   2. Токен бота в config.py")
                print("   3. Настройки файрвола/антивируса")
                print("   4. Доступность api.telegram.org")
                sys.exit(1)
