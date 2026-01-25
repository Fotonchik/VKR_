# bot.py
import telebot
import config
import create_db

import client_bot
import admin_bot

BOT_TOKEN = config.BOT_TOKEN
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")


def main():
    print("===================================")
    print(" Orders Telegram Bot starting ")
    print("===================================")

    create_db.init_database()

    client_bot.register_handlers(bot)
    admin_bot.register_handlers(bot)

    print("[START] Bot polling started")
    bot.infinity_polling()


if __name__ == "__main__":
    main()
