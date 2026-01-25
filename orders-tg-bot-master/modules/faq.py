# modules/faq.py

from telebot import types
import db.db_faq as faq_db
from core.permissions import is_admin
from core.state import StateManager

state = StateManager()


# =========================================================
# CLIENT FAQ
# =========================================================

def show_faq(bot, message):
    items = faq_db.get_faq_for_clients()

    if not items:
        bot.send_message(message.chat.id, "FAQ пока пуст.")
        return

    markup = types.InlineKeyboardMarkup()
    for f in items:
        markup.add(
            types.InlineKeyboardButton(
                f["title"],
                callback_data=f"faq:view:{f['id']}"
            )
        )

    bot.send_message(
        message.chat.id,
        "❓ <b>Часто задаваемые вопросы</b>",
        reply_markup=markup
    )


def faq_view(bot, call, faq_id):
    item = faq_db.get_faq_by_id(faq_id)
    if not item or not item["is_active"]:
        bot.answer_callback_query(call.id, "FAQ недоступен")
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⬅ Назад", callback_data="faq:list"))

    bot.edit_message_text(
        f"<b>{item['title']}</b>\n\n{item['content']}",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


# =========================================================
# ADMIN PANEL
# =========================================================

def manage_faq(bot, message, current_user):
    if not is_admin(current_user["role"]):
        bot.send_message(message.chat.id, "⛔ Только для администратора")
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("📋 Список FAQ", callback_data="faq:admin:list"),
        types.InlineKeyboardButton("➕ Добавить FAQ", callback_data="faq:admin:add")
    )

    bot.send_message(
        message.chat.id,
        "⚙ <b>Управление FAQ</b>",
        reply_markup=markup
    )


def admin_faq_list(bot, call):
    items = faq_db.get_all_faq(include_inactive=True)
    markup = types.InlineKeyboardMarkup()

    for f in items:
        status = "🟢" if f["is_active"] else "🔴"
        markup.add(
            types.InlineKeyboardButton(
                f"{status} {f['title']}",
                callback_data=f"faq:admin:view:{f['id']}"
            )
        )

    markup.add(types.InlineKeyboardButton("⬅ Назад", callback_data="faq:admin:menu"))

    bot.edit_message_text(
        "📋 <b>Все FAQ</b>",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


def admin_faq_add_start(bot, call):
    state.set(call.from_user.id, "faq_add_title", {})
    bot.send_message(call.message.chat.id, "Введите заголовок FAQ:")


def admin_faq_add_title(bot, message):
    data = {"title": message.text}
    state.set(message.from_user.id, "faq_add_content", data)
    bot.send_message(message.chat.id, "Введите текст ответа (HTML разрешён):")


def admin_faq_add_content(bot, message, current_user):
    data = state.get(message.from_user.id)
    data["content"] = message.text

    faq_db.add_faq(
        user_id=current_user["user_id"],
        title=data["title"],
        content=data["content"]
    )

    state.clear(message.from_user.id)
    bot.send_message(message.chat.id, "✅ FAQ добавлен")


def admin_faq_view(bot, call, faq_id):
    f = faq_db.get_faq_by_id(faq_id)

    text = (
        f"<b>{f['title']}</b>\n\n"
        f"{f['content']}\n\n"
        f"Статус: {'Активен' if f['is_active'] else 'Неактивен'}"
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "✏️ Редактировать",
            callback_data=f"faq:admin:edit:{faq_id}"
        ),
        types.InlineKeyboardButton(
            "🔁 Вкл/Выкл",
            callback_data=f"faq:admin:toggle:{faq_id}"
        )
    )
    markup.add(types.InlineKeyboardButton("⬅ Назад", callback_data="faq:admin:list"))

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )
