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
    """Calculate age on a specific date"""
    return target_date.year - birthdate.year - ((target_date.month, target_date.day) < (birthdate.month, birthdate.day))

def is_milestone_age(age):
    """Check if an age is a milestone/round birthday"""
    milestone_ages = [18, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]
    return age in milestone_ages

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

def setup_bot_commands():
    """Set up bot commands menu (call this once to register commands)"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands"
        commands = [
            {
                "command": "birthdays",
                "description": "Show all upcoming birthdays"
            },
            {
                "command": "start",
                "description": "Start the bot"
            }
        ]
        
        payload = {"commands": commands}
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        if result.get('ok'):
            print("✅ Bot commands set up successfully!")
            return True
        else:
            print(f"❌ Failed to set up commands: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Error setting up bot commands: {e}")
        return False

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

def check_for_commands():
    """Check for new Telegram messages and handle commands"""
    try:
        # Get updates with offset to only get new messages
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        params = {"timeout": 10, "limit": 10}
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        print(f"Telegram API response: {data}")
        
        if data.get('ok') and data.get('result'):
            messages = data['result']
            print(f"Found {len(messages)} messages")
            
            for message_data in messages:
                if 'message' in message_data:
                    message = message_data['message']
                    message_text = message.get('text', '').strip()
                    chat_id = message.get('chat', {}).get('id')
                    
                    print(f"Message: '{message_text}' from chat: {chat_id}")
                    
                    # Check if it's from our chat
                    if str(chat_id) == str(CHAT_ID):
                        # Mark this update as processed
                        update_id = message_data['update_id']
                        offset_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
                        offset_params = {"offset": update_id + 1}
                        requests.get(offset_url, params=offset_params)
                        
                        # Handle different commands
                        if message_text == '/birthdays':
                            print(f"✅ Found /birthdays command!")
                            return 'birthdays'
                        elif message_text == '/start':
                            print(f"✅ Found /start command!")
                            return 'start'
        
        return None
    except Exception as e:
        print(f"Error checking for commands: {e}")
        return None

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
    
    # Use timezone-aware datetime (UTC+3)
    today = datetime.now(timezone.utc).date() + timedelta(hours=3)
    print(f"Today's date (UTC+3): {today}")
    
    # Check for commands first
    command = check_for_commands()
    if command:
        print(f"Processing command: {command}")
        
        try:
            birthdays = fetch_birthdays()
        except Exception as e:
            print(f"❌ Error fetching birthdays: {e}")
            send_message("❌ Error fetching birthday data. Please try again later.")
            return
        
        if command == 'start':
            start_message = """🤖 Birthday Bot

Welcome! I help track birthdays and send reminders.

Available commands:
/birthdays - Show all upcoming birthdays
/start - Show this welcome message

I automatically send reminders:
• 7 days before birthdays
• 1 day before birthdays  
• On the birthday itself

The bot runs daily at midnight (UTC+3)."""
            send_message(start_message)
            
        elif command == 'birthdays':
            send_all_birthdays_list(birthdays, today)
            
        return  # Exit after handling command
    
    # Continue with regular daily birthday checking
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
    
    # Debug: Show all found birthdays with calculations
    for name, bday, row in birthdays:
        next_bday = bday.replace(year=today.year)
        if next_bday < today:
            next_bday = bday.replace(year=today.year + 1)
        delta = (next_bday - today).days
        print(f"  DEBUG: {name}: {bday} -> Next: {next_bday} (in {delta} days)")
    
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
            days_text = "days" if delta == 7 else "day"
            
            # Calculate age and check if it's a milestone
            age = calculate_age(bday, next_bday)
            milestone_text = ""
            if is_milestone_age(age):
                milestone_text = f"\n🎊 MILESTONE BIRTHDAY! Turning {age}! 🎊"
            
            message = f"❗ Birthday Reminder ({delta} {days_text} left)\n\n{person_info}\n\n❗ Birthday: {next_bday:%Y-%m-%d}{milestone_text}"
            send_message(message)
            print(f"  ✅ Sent reminder for {name}")
            reminders_sent += 1
        elif delta == 0:
            person_info = format_person_info(name, row)
            
            # Calculate age and check if it's a milestone
            age = calculate_age(bday, next_bday)
            milestone_text = ""
            if is_milestone_age(age):
                milestone_text = f"\n🎊 MILESTONE BIRTHDAY! They're turning {age} today! 🎊"
            
            message = f"🟢 Happy Birthday! 🟢\n\n{person_info}\n\n🛑 Don`t forget to greet!{milestone_text}"
            send_message(message)
            print(f"  🎉 Sent birthday greeting for {name}")
            reminders_sent += 1
    
    # Always send a simple control message
    if reminders_sent == 0:
        control_msg = f"✅ Control Message\n🤖 Bot is working! Today is {today}"
        print("No reminders sent today")
    else:
        control_msg = f"✅ Control Message\n🤖 Bot is working! Today is {today}"
        print(f"✅ Sent {reminders_sent} birthday reminders")
    
    send_message(control_msg)
    print("✅ Sent control message")

if __name__ == "__main__":
    main()