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
        
        # Try different possible column names
        name = row.get("Name") or row.get("name") or row.get("NAME") or row.get("Имя")
        birthday = row.get("Birthday") or row.get("birthday") or row.get("BIRTHDAY") or row.get("Дата рождения")
        
        if name and birthday:
            try:
                bday_date = datetime.fromisoformat(birthday).date()
                birthdays.append((name, bday_date))
                print(f"  ✅ Added: {name} - {bday_date}")
            except ValueError:
                # Skip rows with invalid date format
                print(f"  ❌ Invalid date format for {name}: {birthday}")
                continue
        else:
            print(f"  ⚠️ Missing name or birthday in row: {row}")
    
    print(f"Total rows processed: {row_count}")
    print(f"Valid birthdays found: {len(birthdays)}")
    return birthdays

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
    for name, bday in birthdays:
        next_bday = bday.replace(year=today.year)
        # If birthday already passed this year, check next year
        if next_bday < today:
            next_bday = bday.replace(year=today.year + 1)
            
        delta = (next_bday - today).days
        print(f"  {name}: {bday} -> Next: {next_bday} (in {delta} days)")
        
        if delta in (7, 1):
            send_message(f"🎂 Reminder: {name}'s birthday is in {delta} day(s) on {next_bday:%Y‑%m‑%d}")
            print(f"  ✅ Sent reminder for {name}")
            reminders_sent += 1
        elif delta == 0:
            send_message(f"🎉 Happy Birthday {name}! Today is their special day!")
            print(f"  🎉 Sent birthday greeting for {name}")
            reminders_sent += 1
    
    if reminders_sent == 0:
        print("No reminders sent today (no birthdays in 1, 7 days or today)")
        # Send a test message to verify the bot is working
        send_message(f"🤖 Birthday Bot Test: System is working! Today is {today}. No birthday reminders for today.")
        print("✅ Sent test message to confirm bot is working")

if __name__ == "__main__":
    main()