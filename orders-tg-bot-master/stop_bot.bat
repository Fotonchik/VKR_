@echo off
echo ========================================
echo Остановка всех процессов Python...
echo ========================================
echo.
taskkill /F /IM python.exe 2>nul
if %errorlevel% equ 0 (
    echo Успешно остановлены все процессы Python
) else (
    echo Процессы Python не найдены или уже остановлены
)
echo.
timeout /t 3 /nobreak >nul
echo Проверка оставшихся процессов...
tasklist | findstr python
if %errorlevel% equ 0 (
    echo ВНИМАНИЕ: Обнаружены процессы Python!
) else (
    echo Все процессы Python остановлены.
)
echo.
echo ========================================
echo Готово! Теперь можно запустить бота снова.
echo Используйте: python main_bot.py
echo ========================================
pause

