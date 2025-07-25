import csv, io, os, time
from datetime import datetime, timedelta, timezone
import requests
from dateutil import parser as dateparser  # for aggressive date parsing

# Config from environment
CSV_URL = os.environ.get("SHEET_CSV_URL", "")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")

def safe_fetch(url, retries=3, delay=5):
    """Fetch with retries and safe fallback."""
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            return r
        except Exception as e:
            print(f"⚠️ Fetch attempt {attempt+1}/{retries} failed: {e}")
            time.sleep(delay)
    print("❌ All fetch attempts failed. Returning empty CSV.")
    return type("Response", (), {"text": "", "content": b"", "encoding": None})()

def fetch_birthdays():
    print(f"Fetching CSV from: {CSV_URL}")
    r = safe_fetch(CSV_URL)
    text_content = r.text

    # Try multiple encodings
    for enc in ("utf-8", "windows-1251", "latin1"):
        try:
            text_content = r.content.decode(enc)
            print(f"Decoded as {enc}")
            break
        except Exception:
            continue

    print(f"First 200 characters of CSV: {text_content[:200]}")
    data = csv.DictReader(io.StringIO(text_content))
    birthdays = []
    row_count = 0
    for row in data:
        row_count += 1
        row = {k.strip(): (v or "").strip() for k, v in row.items() if k}  # normalize
        print(f"Processing row {row_count}: {row}")

        # Find name & birthday columns (case-insensitive)
        def get_any(row, keys):
            for k in keys:
                for key in row.keys():
                    if key.lower() == k.lower():
                        return row[key]
            return None

        name = get_any(row, ["Ім'я", "імя", "name"])
        birthday = get_any(row, ["Дата народження", "дата", "birthday"])

        if not name or not birthday:
            print(f"⚠️ Skipping row {row_count}: missing name/birthday.")
            continue

        try:
            bday_date = None
            # Try known formats first
            for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d.%m.%y", "%d/%m/%y"):
                try:
                    bday_date = datetime.strptime(birthday, fmt).date()
                    break
                except ValueError:
                    continue
            # Last resort: dateutil
            if not bday_date:
                bday_date = dateparser.parse(birthday, dayfirst=True, fuzzy=True).date()

            birthdays.append((name, bday_date, row))
            print(f"  ✅ Added: {name} - {bday_date}")
        except Exception as e:
            print(f"❌ Failed to parse birthday for {name}: {birthday} ({e})")

    print(f"Total rows processed: {row_count}")
    print(f"Valid birthdays found: {len(birthdays)}")
    return birthdays

def calculate_age(birthdate, target_date):
    return target_date.year - birthdate.year - ((target_date.month, target_date.day) < (birthdate.month, birthdate.day))

def is_milestone_age(age):
    return age in [18, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]

def format_person_info(name, row):
    phone = next((row.get(f) for f in ["Телефон", "Phone", "Номер телефону"] if row.get(f)), None)
    telegram = next((row.get(f) for f in ["Telegram", "TG", "Телеграм"] if row.get(f)), None)
    lines = [f"👤 {name}"]
    if phone:
        phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if phone.startswith("380") and not phone.startswith("+"): phone = f"+{phone}"
        elif len(phone) == 9: phone = f"+380{phone}"
        lines.append(f"📞 Phone: {phone}")
    if telegram:
        if not telegram.startswith("@"): telegram = f"@{telegram}"
        lines.append(f"💬 Telegram: {telegram}")
    return "\n".join(lines)

def send_message(text):
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️ Missing BOT_TOKEN or CHAT_ID. Skipping message.")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        print(f"✅ Message sent: {r.json()}")
    except Exception as e:
        print(f"❌ Failed to send message: {e}")

def send_all_birthdays_list(birthdays, today):
    if not birthdays:
        send_message("📋 No birthdays found.")
        return
    birthday_info = []
    for name, bday, row in birthdays:
        next_bday = bday.replace(year=today.year)
        if next_bday < today:
            next_bday = bday.replace(year=today.year + 1)
        delta = (next_bday - today).days
        age = calculate_age(bday, next_bday)
        birthday_info.append((delta, f"• {name}: {next_bday:%d.%m} ({delta} days){' 🎊' if is_milestone_age(age) else ''}"))
    birthday_info.sort(key=lambda x: x[0])
    message = "📋 All Birthdays List\n\n" + "\n".join(line for _, line in birthday_info)
    send_message(message)

def main():
    print("🤖 Birthday Bot Starting...")
    today = (datetime.now(timezone.utc) + timedelta(hours=3)).date()
    print(f"Today's date (UTC+3): {today} ({today.strftime('%A')})")

    try:
        birthdays = fetch_birthdays()
    except Exception as e:
        print(f"❌ Critical error fetching birthdays: {e}")
        birthdays = []

    if today.weekday() == 6:  # Sunday
        send_message(f"📅 Weekly Birthday Overview - {today.strftime('%B %d, %Y')}")
        send_all_birthdays_list(birthdays, today)

    for name, bday, row in birthdays:
        next_bday = bday.replace(year=today.year)
        if next_bday < today:
            next_bday = bday.replace(year=today.year + 1)
        delta = (next_bday - today).days
        if delta in (7, 1):
            send_message(f"🎂 Reminder: {name}'s birthday in {delta} days!\n{format_person_info(name, row)}")

if __name__ == "__main__":
    main()
