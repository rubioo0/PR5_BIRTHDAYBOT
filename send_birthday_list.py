#!/usr/bin/env python3
"""
Manual birthday list sender
Run this anytime to get the complete birthday overview
"""

import os
import sys
from main import fetch_birthdays, send_all_birthdays_list, send_message
from datetime import datetime, timezone, timedelta

def main():
    print("📋 Manual Birthday List Sender")
    
    # Check if environment variables are set
    required_vars = ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "SHEET_CSV_URL"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print("❌ Missing environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set them first:")
        for var in missing_vars:
            if os.name == 'nt':  # Windows
                print(f'$env:{var}="your_value_here"')
            else:  # Unix/Linux/Mac
                print(f'export {var}="your_value_here"')
        return
    
    today = datetime.now(timezone.utc).date() + timedelta(hours=3)
    
    try:
        print("📥 Fetching birthday data...")
        birthdays = fetch_birthdays()
        print(f"✅ Loaded {len(birthdays)} birthdays")
    except Exception as e:
        print(f"❌ Error fetching birthdays: {e}")
        return
    
    if not birthdays:
        send_message("📋 Manual Birthday Check\n\n❌ No birthday data available. Check your CSV URL.")
        return
    
    # Send the birthday list
    print("📤 Sending birthday list...")
    header = f"📋 Manual Birthday List Request - {today.strftime('%B %d, %Y')}\n\nHere's your complete birthday list:"
    send_message(header)
    send_all_birthdays_list(birthdays, today)
    print("✅ Birthday list sent successfully!")

if __name__ == "__main__":
    main()
