@echo off
echo 🤖 Sending Birthday List Request...
echo.

curl -k -X POST "https://api.telegram.org/bot8460155189:AAExnU8vhSAYiLZdBEG08sQFeAJAu1iNBX0/sendMessage" ^
     -H "Content-Type: application/json" ^
     -d "{\"chat_id\": \"1029934657\", \"text\": \"📋 Manual Birthday List Request - %date%\"}"

if %errorlevel% equ 0 (
    echo.
    echo ✅ Message sent successfully!
) else (
    echo.
    echo ❌ Failed to send message
)

echo.
echo Press any key to close...
pause >nul
