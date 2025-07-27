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
    
    # Try to detect and fix encoding issues
    text_content = r.text
    if r.encoding:
        print(f"Response encoding: {r.encoding}")
    
    # Try UTF-8 decoding if there are encoding issues
    try:
        if r.content:
            text_content = r.content.decode('utf-8')
            print("Successfully decoded as UTF-8")
    except UnicodeDecodeError:
        try:
            text_content = r.content.decode('windows-1251')
            print("Decoded as Windows-1251")
        except UnicodeDecodeError:
            print("Using original text content")
    
    print(f"First 200 characters of CSV: {text_content[:200]}")
    
    data = csv.DictReader(io.StringIO(text_content))
    
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
                # Try multiple date formats
                bday_date = None
                birthday = birthday.strip()
                
                # Try ISO format first (YYYY-MM-DD)
                if '-' in birthday and len(birthday) == 10:
                    bday_date = datetime.fromisoformat(birthday).date()
                # Try DD.MM.YYYY format
                elif '.' in birthday:
                    parts = birthday.split('.')
                    if len(parts) == 3:
                        day, month, year = parts
                        if len(year) == 2:
                            year = f"19{year}" if int(year) > 50 else f"20{year}"
                        bday_date = datetime(int(year), int(month), int(day)).date()
                # Try DD/MM/YYYY format
                elif '/' in birthday:
                    parts = birthday.split('/')
                    if len(parts) == 3:
                        day, month, year = parts
                        if len(year) == 2:
                            year = f"19{year}" if int(year) > 50 else f"20{year}"
                        bday_date = datetime(int(year), int(month), int(day)).date()
                
                if bday_date:
                    birthdays.append((name, bday_date, row))
                    print(f"  ✅ Added: {name} - {bday_date}")
                else:
                    print(f"  ❌ Could not parse date format: {birthday}")
                    
            except (ValueError, IndexError) as e:
                print(f"  ❌ Invalid date format for {name}: {birthday} - Error: {e}")
                continue
        else:
            print(f"  ⚠️ Missing required fields in row: {row}")
            print(f"    Name found: {name}")
            print(f"    Birthday found: {birthday}")
    
    print(f"Total rows processed: {row_count}")
    print(f"Valid birthdays found: {len(birthdays)}")
    return birthdays

def calculate_age(birthdate, target_date):
    return target_date.year - birthdate.year - ((target_date.month, target_date.day) < (birthdate.month, birthdate.day))

def is_milestone_age(age):
    return age in [18, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]

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
        
        info_lines.append(f"📞 Phone: {clean_phone}")
    
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

def send_all_birthdays_list(birthdays, today):
    """Send a formatted list of all birthdays with days remaining"""
    if not birthdays:
        send_message("📋 Birthday List\n\nNo birthdays found in database.")
        return
    
    # Calculate days for all birthdays and sort by next occurrence
    birthday_info = []
    for name, bday, row in birthdays:
        next_bday = bday.replace(year=today.year)
        if next_bday < today:
            next_bday = bday.replace(year=today.year + 1)
        
        delta = (next_bday - today).days
        age = calculate_age(bday, next_bday)
        
        # Format each birthday entry
        milestone_indicator = " 🎊" if is_milestone_age(age) else ""
        birthday_info.append((delta, f"• {name}: {next_bday:%d.%m} ({delta} days){milestone_indicator}"))
    
    # Sort by days remaining (closest first)
    birthday_info.sort(key=lambda x: x[0])
    
    # Create the message
    message_lines = ["📋 All Birthdays List\n"]
    
    for _, birthday_line in birthday_info:
        message_lines.append(birthday_line)
    
    message = "\n".join(message_lines)
    
    # Split message if too long (Telegram limit is ~4000 characters)
    if len(message) > 3500:
        # Send in chunks
        chunk_lines = ["📋 All Birthdays List (Part 1)\n"]
        current_length = len(chunk_lines[0])
        part_num = 1
        
        for _, birthday_line in birthday_info:
            if current_length + len(birthday_line) + 1 > 3500:
                # Send current chunk
                send_message("\n".join(chunk_lines))
                # Start new chunk
                part_num += 1
                chunk_lines = [f"📋 All Birthdays List (Part {part_num})\n"]
                current_length = len(chunk_lines[0])
            
            chunk_lines.append(birthday_line)
            current_length += len(birthday_line) + 1
        
        # Send final chunk
        if len(chunk_lines) > 1:
            send_message("\n".join(chunk_lines))
    else:
        send_message(message)

def main():
    print("🤖 Birthday Bot Starting...")
    print(f"Bot Token: {BOT_TOKEN[:10]}...")
    print(f"Chat ID: {CHAT_ID}")
    print(f"CSV URL: {CSV_URL}")
    
    # Use timezone-aware datetime (UTC+3 for Kyiv time)
    today = datetime.now(ZoneInfo("Europe/Kyiv")).date()
    print(f"Today's date (UTC+3): {today}")
    print(f"Day of week: {today.strftime('%A')} (0=Monday, 6=Sunday: {today.weekday()})")
    
    # Fetch birthdays
    try:
        birthdays = fetch_birthdays()
    except Exception as e:
        print(f"❌ Error fetching birthdays: {e}")
        error_msg = f"🤖 Birthday Bot Error: Failed to fetch birthdays.\n\n📅 Today: {today}\n❌ Error: {str(e)}"
        send_message(error_msg)
        return
    
    if not birthdays:
        print("❌ No valid birthdays found in CSV")
        error_msg = f"🤖 Birthday Bot Error: No valid birthdays found in CSV file.\n\n📅 Today: {today}\n⚠️ Please check your CSV format."
        send_message(error_msg)
        return
    
    print(f"Today's date: {today}")
    print(f"Found {len(birthdays)} birthdays in CSV:")
    
    # Debug: Show all found birthdays with calculations
    for name, bday, row in birthdays:
        next_bday = bday.replace(year=today.year)
        if next_bday < today:
            next_bday = bday.replace(year=today.year + 1)
        delta = (next_bday - today).days
        print(f"  DEBUG: {name}: {bday} -> Next: {next_bday} (in {delta} days)")
    
    # Track what messages we need to send
    messages_sent = []
    reminders_sent = 0
    birthday_greetings_sent = 0
    
    # Check for birthday reminders and greetings
    for name, bday, row in birthdays:
        next_bday = bday.replace(year=today.year)
        # If birthday already passed this year, check next year
        if next_bday < today:
            next_bday = bday.replace(year=today.year + 1)
            
        delta = (next_bday - today).days
        print(f"  {name}: {bday} -> Next: {next_bday} (in {delta} days)")
        
        if delta == 7:
            person_info = format_person_info(name, row)
            
            # Calculate age and check if it's a milestone
            age = calculate_age(bday, next_bday)
            milestone_text = ""
            if is_milestone_age(age):
                milestone_text = f"\n🎊 MILESTONE BIRTHDAY! Turning {age}! 🎊"
            
            message = f"❗ Birthday Reminder (7 days left)\n\n{person_info}\n\n❗ Birthday: {next_bday:%Y-%m-%d}{milestone_text}"
            send_message(message)
            messages_sent.append(f"7-day reminder for {name}")
            print(f"  ✅ Sent 7-day reminder for {name}")
            reminders_sent += 1
            
        elif delta == 1:
            person_info = format_person_info(name, row)
            
            # Calculate age and check if it's a milestone
            age = calculate_age(bday, next_bday)
            milestone_text = ""
            if is_milestone_age(age):
                milestone_text = f"\n🎊 MILESTONE BIRTHDAY! Turning {age}! 🎊"
            
            message = f"❗ Birthday Reminder (1 day left)\n\n{person_info}\n\n❗ Birthday: {next_bday:%Y-%m-%d}{milestone_text}"
            send_message(message)
            messages_sent.append(f"1-day reminder for {name}")
            print(f"  ✅ Sent 1-day reminder for {name}")
            reminders_sent += 1
            
        elif delta == 0:
            person_info = format_person_info(name, row)
            
            # Calculate age and check if it's a milestone
            age = calculate_age(bday, next_bday)
            milestone_text = ""
            if is_milestone_age(age):
                milestone_text = f"\n🎊 MILESTONE BIRTHDAY! They're turning {age} today! 🎊"
            
            message = f"🎉 Happy Birthday! 🎉\n\n{person_info}\n\n🎂 Don't forget to greet!{milestone_text}"
            send_message(message)
            messages_sent.append(f"Birthday greeting for {name}")
            print(f"  🎉 Sent birthday greeting for {name}")
            birthday_greetings_sent += 1
    
    # Check if it's Sunday (6) and send weekly birthday list
    is_sunday = today.weekday() == 6  # Sunday = 6 (Monday=0, Tuesday=1, ..., Sunday=6)
    if is_sunday:
        print("📅 It's Sunday! Sending weekly birthday list...")
        weekly_header = f"📅 Weekly Birthday Overview - {today.strftime('%B %d, %Y')}\n\nHere's your complete birthday list with days remaining:"
        send_message(weekly_header)
        send_all_birthdays_list(birthdays, today)
        messages_sent.append("Weekly birthday list")
        print("✅ Sent weekly birthday list")
    
    # Always send ONE control message with verification
    control_parts = [f"✅ Control Message - {today}"]
    control_parts.append(f"🤖 Bot is working! ({len(birthdays)} birthdays tracked)")
    
    # Add verification based on what happened
    if birthday_greetings_sent > 0:
        control_parts.append(f"🎉 Sent {birthday_greetings_sent} birthday greeting(s)")
    
    if reminders_sent > 0:
        control_parts.append(f"⏰ Sent {reminders_sent} birthday reminder(s)")
    
    if is_sunday:
        control_parts.append("📅 Sent weekly birthday overview")
    
    if not messages_sent or (len(messages_sent) == 1 and "Weekly birthday list" in messages_sent):
        # No birthdays coming up (or only weekly list sent)
        control_parts.append("✅ No upcoming birthdays today")
    
    control_msg = "\n".join(control_parts)
    send_message(control_msg)
    
    print(f"✅ Sent control message. Total messages sent: {len(messages_sent) + 1}")
    if messages_sent:
        print(f"   Messages sent: {', '.join(messages_sent)}")
    else:
        print("   No birthday-related messages sent today")

if __name__ == "__main__":
    main()
