import csv, io, os
from datetime import datetime, timedelta, timezone
import requests

# Config from environment
CSV_URL = os.environ["SHEET_CSV_URL"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]

def fetch_birthdays():
    print(f"Fetching CSV from: {CSV_URL}")
    r = requests.get(CSV_URL)
    r.raise_for_status()
    print(f"CSV response status: {r.status_code}")
    print(f"CSV content length: {len(r.text)} characters")
    print(f"First 200 characters of CSV: {r.text[:200]}")
    
    data = csv.DictReader(io.StringIO(r.text))
    
    birthdays = []
    row_count = 0
    for row in data:
        row_count += 1
        print(f"Processing row {row_count}: {row}")
        
        # Try different possible column names for name (Ukrainian)
        name = (row.get("Ім'я") or row.get("name") or row.get("Name") or 
                row.get("ім'я") or row.get("NAME") or row.get("Імя"))
        
        # Try different possible column names for birthday
        birthday = (row.get("Дата народження") or row.get("Birthday") or 
                   row.get("birthday") or row.get("дата народження") or 
                   row.get("BIRTHDAY") or row.get("Дата"))
        
        if name and birthday:
            try:
                bday_date = datetime.fromisoformat(birthday).date()
                # Store the full row data along with parsed name and birthday
                birthdays.append((name, bday_date, row))
                print(f"  ✅ Added: {name} - {bday_date}")
            except ValueError:
                # Skip rows with invalid date format
                print(f"  ❌ Invalid date format for {name}: {birthday}")
                continue
        else:
            print(f"  ⚠️ Missing required fields in row: {row}")
            print(f"    Name found: {name}")
            print(f"    Birthday found: {birthday}")
    
    print(f"Total rows processed: {row_count}")
    print(f"Valid birthdays found: {len(birthdays)}")
    return birthdays

def format_person_info(name, row):
    """Format Ukrainian person information from CSV row"""
    info_lines = [f"👤 {name}"]
    
    # Get phone number (+380 format)
    phone_fields = ["Телефон", "телефон", "Phone", "phone", "Номер телефону", "номер телефону"]
    phone = None
    for field in phone_fields:
        if row.get(field) and row.get(field).strip():
            phone = row.get(field).strip()
            break
    
    # Get telegram ID (@nickname format)  
    telegram_fields = ["Telegram", "telegram", "TG", "tg", "Телеграм", "телеграм", "Telegram ID", "telegram id"]
    telegram = None
    for field in telegram_fields:
        if row.get(field) and row.get(field).strip():
            telegram = row.get(field).strip()
            break
    
    # Add phone if available (handle missing + symbol for Ukrainian numbers)
    if phone:
        # Remove any spaces, dashes, or parentheses
        clean_phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        
        # If it's a Ukrainian number without +, add it
        if clean_phone.startswith("380") and not clean_phone.startswith("+"):
            clean_phone = f"+{clean_phone}"
        elif not clean_phone.startswith("+") and len(clean_phone) == 9:
            # If it's 9 digits (without country code), add +380
            clean_phone = f"+380{clean_phone}"
        
        info_lines.append(f"📞 Телефон: {clean_phone}")
    
    # Add telegram if available
    if telegram:
        # Ensure @ symbol is present
        if not telegram.startswith('@'):
            telegram = f"@{telegram}"
        info_lines.append(f"💬 Telegram: {telegram}")
    
    return "\n".join(info_lines)

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    print(f"Sending message to chat {CHAT_ID}: {text}")
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"✅ Message sent successfully! Response: {response.json()}")
    except Exception as e:
        print(f"❌ Failed to send message: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response content: {e.response.text}")
        raise

def main():
    print("🤖 Birthday Bot Starting...")
    print(f"Bot Token: {BOT_TOKEN[:10]}...")
    print(f"Chat ID: {CHAT_ID}")
    print(f"CSV URL: {CSV_URL}")
    
    # Use timezone-aware datetime (UTC+3)
    today = datetime.now(timezone.utc).date() + timedelta(hours=3)
    print(f"Today's date (UTC+3): {today}")
    
    try:
        birthdays = fetch_birthdays()
    except Exception as e:
        print(f"❌ Error fetching birthdays: {e}")
        return
    
    if not birthdays:
        print("❌ No valid birthdays found in CSV")
        try:
            send_message("🤖 Birthday Bot Error: No valid birthdays found in CSV file. Please check your CSV format.")
        except:
            print("Failed to send error message")
        return
    
    print(f"Today's date: {today}")
    print(f"Found {len(birthdays)} birthdays in CSV:")
    
    reminders_sent = 0
    for name, bday, row in birthdays:
        next_bday = bday.replace(year=today.year)
        # If birthday already passed this year, check next year
        if next_bday < today:
            next_bday = bday.replace(year=today.year + 1)
            
        delta = (next_bday - today).days
        print(f"  {name}: {bday} -> Next: {next_bday} (in {delta} days)")
        
        if delta in (7, 1):
            person_info = format_person_info(name, row)
            days_text = "днів" if delta == 7 else "день"
            message = f"🎂 Нагадування про день народження ({delta} {days_text} залишилось)\n\n{person_info}\n\n📅 День народження: {next_bday:%Y-%m-%d}"
            send_message(message)
            print(f"  ✅ Sent reminder for {name}")
            reminders_sent += 1
        elif delta == 0:
            person_info = format_person_info(name, row)
            message = f"🎉 З Днем народження! 🎉\n\n{person_info}\n\n🎂 Сьогодні особливий день!"
            send_message(message)
            print(f"  🎉 Sent birthday greeting for {name}")
            reminders_sent += 1
    
    if reminders_sent == 0:
        print("No reminders sent today (no birthdays in 1, 7 days or today)")
        
        # Create upcoming birthdays summary (next 30 days)
        upcoming_birthdays = []
        for name, bday, row in birthdays:
            next_bday = bday.replace(year=today.year)
            if next_bday < today:
                next_bday = bday.replace(year=today.year + 1)
            
            delta = (next_bday - today).days
            if 0 < delta <= 30:  # Next 30 days (excluding today)
                upcoming_birthdays.append(f"• {name}: {next_bday:%d.%m} ({delta} днів)")
        
        # Send control message with upcoming birthdays info
        if upcoming_birthdays:
            upcoming_text = "\n".join(upcoming_birthdays[:5])  # Show max 5 upcoming
            if len(upcoming_birthdays) > 5:
                upcoming_text += f"\n... та ще {len(upcoming_birthdays) - 5}"
            control_msg = f"✅ Контрольне повідомлення\n🤖 Бот працює! Сьогодні {today}\n📅 Немає нагадувань на сьогодні\n\n🔜 Найближчі дні народження:\n{upcoming_text}"
        else:
            control_msg = f"✅ Контрольне повідомлення\n🤖 Бот працює! Сьогодні {today}\n📅 Немає днів народження в найближчі 30 днів"
        
        send_message(control_msg)
        print("✅ Sent control message to confirm bot is working")
    else:
        # Send summary control message when reminders were sent
        send_message(f"✅ Контрольне повідомлення\n🤖 Бот працює! Сьогодні {today}\n🎂 Відправлено {reminders_sent} нагадувань про дні народження")
        print(f"✅ Sent control summary: {reminders_sent} reminders sent")

if __name__ == "__main__":
    main()