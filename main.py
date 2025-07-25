import csv, io, os
from datetime import datetime, timedelta, timezone
import requests

# Config from environment
CSV_URL = os.environ["SHEET_CSV_URL"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]

def fetch_birthdays():
    r = requests.get(CSV_URL)
    r.raise_for_status()
    data = csv.DictReader(io.StringIO(r.text))
    
    birthdays = []
    for row in data:
        # Try different possible column names
        name = row.get("Name") or row.get("name") or row.get("NAME") or row.get("Имя")
        birthday = row.get("Birthday") or row.get("birthday") or row.get("BIRTHDAY") or row.get("Дата рождения")
        
        if name and birthday:
            try:
                bday_date = datetime.fromisoformat(birthday).date()
                birthdays.append((name, bday_date))
            except ValueError:
                # Skip rows with invalid date format
                print(f"Warning: Invalid date format for {name}: {birthday}")
                continue
        else:
            print(f"Warning: Missing name or birthday in row: {row}")
    
    return birthdays

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, json=payload).raise_for_status()

def main():
    # Use timezone-aware datetime (UTC+3)
    today = datetime.now(timezone.utc).date() + timedelta(hours=3)
    birthdays = fetch_birthdays()
    
    if not birthdays:
        print("No valid birthdays found in CSV")
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