from db.employees import get_user_role

def require_role(*allowed_roles):
    def decorator(handler):
        def wrapper(message, *args, **kwargs):
            role = get_user_role(message.from_user.id)

            if role not in allowed_roles:
                message.bot.send_message(
                    message.chat.id,
                    "⛔ У вас нет прав для этого действия."
                )
                return

            return handler(message, *args, **kwargs)

        return wrapper
    return decorator
