# Бот для создания заказов



## Установка

1. Для запуска бота необходимо заполнить файл **config.py** и вписать:
  - Идентификатор чата в Telegram, который всегда будет администратором
  - Идентификатор группы или чата в Telegram, в который будут отправлятся сообщения о поступлении нового заказа (может быть групповой чат)
  - Токен бота

2. Создать виртуальное окружение для Python:

```bash
#!/bin/bash

python -m venv .venv
pip install -r requirements.txt

```

3. Отредактировать файл **orders-bot.service** и дописать в него путь до папки с программой

4. Добавить службу для запуска бота:

```bash
#!/bin/bash

# Копирование файла службы
sudo cp orders-bot.service /etc/systemd/system/
# Включение в автозагрузку и запуск
sudo systemctl enable orders-bot.service
sudo systemctl start orders-bot.service

```

Дополнительные команды:

```bash
#!/bin/bash

# Проверка статуса
sudo systemctl status orders-bot.service

# Просмотр логов
journalctl -u orders-bot.service 

# Выключение автозагрузки
sudo systemctl disable orders-bot.service

# Отключение бота
sudo systemctl stop orders-bot.service

# Перезагрузка бота
sudo systemctl restart orders-bot.service

# В git убрать просмотр изменений в файле config.py
git update-index --assume-unchanged config.py

```
