@echo off
echo Запуск Telegram бота...
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
    echo Виртуальное окружение не найдено!
    echo Создаю виртуальное окружение...
    python -m venv venv
    echo Активирую виртуальное окружение...
    call venv\Scripts\activate.bat
    echo Устанавливаю зависимости...
    pip install pyTelegramBotAPI fpdf2
) else (
    call venv\Scripts\activate.bat
)
echo.
echo Запускаю бота...
python main_bot.py
pause

