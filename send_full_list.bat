@echo off
echo 🎂 Sending FULL Birthday List with Calculations...
echo.

set TELEGRAM_BOT_TOKEN=8460155189:AAExnU8vhSAYiLZdBEG08sQFeAJAu1iNBX0
set TELEGRAM_CHAT_ID=1029934657
set SHEET_CSV_URL=https://docs.google.com/spreadsheets/d/e/2PACX-1vTMhZ0NIeVO7XUe9pF4nf3cdbYt9WgEFCfreEBP2nQIhYOTBjFK3PwRqLLfNhJBt9YhPvbjKVVZl1M8/pub?output=csv

python send_birthday_list.py

if %errorlevel% equ 0 (
    echo.
    echo ✅ Full birthday list sent successfully!
) else (
    echo.
    echo ❌ Failed to send birthday list
    echo Make sure Python is installed and send_birthday_list.py exists
)

echo.
echo Press any key to close...
pause >nul
