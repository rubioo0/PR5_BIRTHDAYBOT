#!/usr/bin/env python3
"""
Setup script to register bot commands with Telegram.
Run this once to set up the /birthdays and /start commands in your bot menu.
"""

import os
import requests

# Get credentials from environment
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN environment variable not set!")
    print("Please set it first:")
    print("export TELEGRAM_BOT_TOKEN='your_bot_token_here'")
    exit(1)

def setup_bot_commands():
    """Set up bot commands menu"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands"
        commands = [
            {
                "command": "birthdays",
                "description": "Show all upcoming birthdays"
            },
            {
                "command": "start", 
                "description": "Show welcome message and help"
            }
        ]
        
        payload = {"commands": commands}
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        if result.get('ok'):
            print("✅ Bot commands set up successfully!")
            print("Commands registered:")
            for cmd in commands:
                print(f"  /{cmd['command']} - {cmd['description']}")
            print("\nYou should now see these commands in your Telegram bot menu!")
            return True
        else:
            print(f"❌ Failed to set up commands: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Error setting up bot commands: {e}")
        return False

if __name__ == "__main__":
    print("🤖 Setting up Birthday Bot commands...")
    print(f"Bot Token: {BOT_TOKEN[:10]}...")
    
    if setup_bot_commands():
        print("\n🎉 Setup complete! Your bot now has a command menu.")
        print("Try typing '/' in your Telegram chat with the bot to see the menu.")
    else:
        print("\n❌ Setup failed. Please check your bot token and try again.")
