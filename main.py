import csv, io, os
from datetime import datetime, timedelta
import requests

# Config from environment
CSV_URL   = os.environ["https://docs.google.com/spreadsheets/d/e/2PACX-1vTMhZ0NIeVO7XUe9pF4nf3cdbYt9WgEFCfreEBP2nQIhYOTBjFK3PwRqLLfNhJBt9YhPvbjKVVZl1M8/pubhtml"]
BOT_TOKEN = os.environ["8460155189:AAExnU8vhSAYiLZdBEG08sQFeAJAu1iNBX0"]
CHAT_ID   = os.environ["1029934657"]

def fetch_birthdays():
    r = requests.get(CSV_URL)
    r.raise_for_status()
    data = csv.DictReader(io.StringIO(r.text))
    return [(row["Name"], datetime.fromisoformat(row["Birthday"]).date())
            for row in data]

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, json=payload).raise_for_status()

def main():
    today = datetime.utcnow().date() + timedelta(hours=3)
    birthdays = fetch_birthdays()
    for name, bday in birthdays:
        next_bday = bday.replace(year=today.year)
        delta = (next_bday - today).days
        if delta in (7, 1):
            send_message(f"🎂 Reminder: {name}'s birthday is in {delta} day(s) on {next_bday:%Y‑%m‑%d}")

if __name__ == "__main__":
    main()