import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import calendar
import re

def create_live_calendar():
    url = "https://www.catamilacademy.org/MckinneyTamilAcademy.html"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        print(f"Error fetching URL: {e}")
        return

    # 1. Extract Location
    # Looking for "Classes are conducted at:" section
    location = "Mckinney, TX"  # Default fallback
    location_tag = soup.find(text=lambda t: "Classes are conducted at:" in t)
    if location_tag:
        parent_text = location_tag.parent.get_text()
        # Regex to find the address pattern (numbers + street + TX + zip)
        addr_match = re.search(r'\d+ [\w\s]+, TX \d{5}', parent_text)
        if addr_match:
            location = addr_match.group(0)
        else:
            # Fallback to the specific known location if regex fails
            location = "Children's Lighthouse of McKinney, 7900 Stacy Rd, TX 75070"

    # 2. Important Dates (Manual list for accuracy, but location is dynamic)
    # Note: These are for the 2026-2027 Academic Year
    important_dates = [
        ("Aug", 9, 2026, "First day of school"),
        ("Aug", 30, 2026, "Test 1 - Project 1"),
        ("Sep", 6, 2026, "Holiday - Labor day"),
        ("Oct", 4, 2026, "Test 2"),
        ("Nov", 1, 2026, "Test 3 - Term 1 ends"),
        ("Nov", 8, 2026, "Holiday - Deepawali"),
        ("Nov", 15, 2026, "Term 2 starts"),
        ("Nov", 29, 2026, "Holiday - Thanksgiving"),
        ("Dec", 13, 2026, "Test 4 - Project 2"),
        ("Dec", 20, 2026, "Holiday - Christmas"),
        ("Dec", 27, 2026, "Holiday - NewYear"),
        ("Jan", 24, 2027, "Test 5 - Term 2 ends"),
        ("Jan", 31, 2027, "Term 3 starts"),
        ("Feb", 21, 2027, "Test 6"),
        ("Mar", 21, 2027, "Holiday - Springbreak"),
        ("Mar", 28, 2027, "Holiday - Annual day"),
        ("Apr", 4, 2027, "Test 7"),
        ("May", 2, 2027, "FINAL TEST"),
    ]

    # 3. Build the ICS
    # Added TZID to handle the McKinney, TX (Central) timezone correctly
    ics_content = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Hermes Agent//Mckinney Tamil Academy//EN",
        "CALSCALE:GREGORIAN",
        "TZID:America/Chicago"
    ]

    month_map = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
    }

    processed_dates = set()
    source_url = url

    # Process Important Dates
    for month_str, day, year, desc in important_dates:
        month_num = month_map.get(month_str)
        dt = datetime(year, month_num, day)
        processed_dates.add(dt.date())
        
        unique_id = f"{dt.strftime('%Y%m%d')}_{desc.replace(' ', '_')}"
        
        ics_content.append("BEGIN:VEVENT")
        ics_content.append(f"UID:{unique_id}")
        ics_content.append(f"SUMMARY:{desc}")
        ics_content.append(f"LOCATION:{location}")
        ics_content.append(f"DESCRIPTION:Mckinney Tamil Academy: {desc}")
        ics_content.append(f"URL:{source_url}")
        # Format: YYYYMMDD (Standard for All-Day events)
        ics_content.append(f"DTSTART:{dt.strftime('%Y%m%d')}")
        ics_content.append(f"DTEND:{dt.strftime('%Y%m%d')}")
        ics_content.append("END:VEVENT")

    # 4. Generate Sundays (Normal Class Days)
    start_date = datetime(2026, 8, 9)
    end_date = datetime(2027, 5, 2)
    
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() == 6:
            if current_date.date() not in processed_dates:
                unique_id = f"{current_date.strftime('%Y%m%d')}_normal_class"
                ics_content.append("BEGIN:VEVENT")
                ics_content.append(f"UID:{unique_id}")
                ics_content.append("SUMMARY:Normal Class Day")
                ics_content.append(f"LOCATION:{location}")
                ics_content.append("DESCRIPTION:Mckinney Tamil Academy: Regular weekly academy class")
                ics_content.append(f"URL:{source_url}")
                ics_content.append(f"DTSTART:{current_date.strftime('%Y%m%d')}")
                ics_content.append(f"DTEND:{current_date.strftime('%Y%m%d')}")
                ics_content.append("END:VEVENT")
        
        current_date += timedelta(days=1)

    ics_content.append("END:VCALENDAR")

    file_name = "mckinney_academy_final_fixed.ics"
    with open(file_name, "w") as f:
        f.write("\n".join(ics_content))
    
    print(f"Successfully created {file_name} with location: {location}")

if __name__ == "__main__":
    create_live_calendar()
