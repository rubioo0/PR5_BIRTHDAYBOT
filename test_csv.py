#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to check CSV format and encoding
Run this to debug your CSV file issues
"""

import requests
import csv
import io
from datetime import datetime

def test_csv_url():
    """Test function to check CSV format - replace with your actual CSV URL"""
    
    # You need to replace this with your actual CSV URL
    CSV_URL = "YOUR_CSV_URL_HERE"
    
    print("=== CSV Format Test ===")
    print(f"Testing URL: {CSV_URL}")
    
    try:
        r = requests.get(CSV_URL)
        r.raise_for_status()
        print(f"✅ Successfully fetched CSV (Status: {r.status_code})")
        print(f"Content length: {len(r.text)} characters")
        print(f"Response encoding: {r.encoding}")
        
        # Show raw content
        print("\n=== Raw CSV Content (first 500 chars) ===")
        print(repr(r.text[:500]))
        
        # Try different encodings
        print("\n=== Testing Different Encodings ===")
        
        # Test UTF-8
        try:
            utf8_content = r.content.decode('utf-8')
            print("✅ UTF-8 decoding successful")
            print(f"UTF-8 first 200 chars: {utf8_content[:200]}")
        except UnicodeDecodeError as e:
            print(f"❌ UTF-8 decoding failed: {e}")
        
        # Test Windows-1251 (Cyrillic)
        try:
            win1251_content = r.content.decode('windows-1251')
            print("✅ Windows-1251 decoding successful")
            print(f"Windows-1251 first 200 chars: {win1251_content[:200]}")
        except UnicodeDecodeError as e:
            print(f"❌ Windows-1251 decoding failed: {e}")
        
        # Parse CSV
        print("\n=== CSV Parsing Test ===")
        data = csv.DictReader(io.StringIO(r.text))
        
        print("Column names found:", data.fieldnames)
        
        rows = list(data)
        print(f"Total rows: {len(rows)}")
        
        if rows:
            print("\n=== First 3 rows ===")
            for i, row in enumerate(rows[:3]):
                print(f"Row {i+1}: {dict(row)}")
                
                # Test name extraction
                name = (row.get("Ім'я") or row.get("name") or row.get("Name") or 
                       row.get("ім'я") or row.get("NAME") or row.get("Імя"))
                
                # Test birthday extraction
                birthday = (row.get("Дата народження") or row.get("Birthday") or 
                           row.get("birthday") or row.get("дата народження") or 
                           row.get("BIRTHDAY") or row.get("Дата"))
                
                print(f"  Extracted name: {repr(name)}")
                print(f"  Extracted birthday: {repr(birthday)}")
                
                if birthday:
                    # Test date parsing
                    try:
                        birthday = birthday.strip()
                        if '-' in birthday and len(birthday) == 10:
                            bday_date = datetime.fromisoformat(birthday).date()
                            print(f"  ✅ Parsed as ISO date: {bday_date}")
                        elif '.' in birthday:
                            parts = birthday.split('.')
                            if len(parts) == 3:
                                day, month, year = parts
                                if len(year) == 2:
                                    year = f"19{year}" if int(year) > 50 else f"20{year}"
                                bday_date = datetime(int(year), int(month), int(day)).date()
                                print(f"  ✅ Parsed as DD.MM.YYYY date: {bday_date}")
                        else:
                            print(f"  ❌ Unknown date format: {birthday}")
                    except Exception as e:
                        print(f"  ❌ Date parsing failed: {e}")
                
                print()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("To use this test:")
    print("1. Replace 'YOUR_CSV_URL_HERE' with your actual CSV URL")
    print("2. Run: python test_csv.py")
    print()
    
    # Uncomment the line below and add your CSV URL to run the test
    # test_csv_url()
