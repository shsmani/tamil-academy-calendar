import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import calendar

def create_mckinney_calendar():
    url = "https://www.catamilacademy.org/MckinneyTamilAcademy.html"
    
    # Data extracted from the academy's official schedule
    # Format: (Month Name, Day, Year, Description)
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

    # 1. Prepare the base ICS structure
    ics_content = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Hermes Agent//Mckinney Tamil Academy//EN",
        "CALSCALE:GREGOIAN"
    ]

    # Mapping for months
    month_map = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
    }

    # 2. Process Important Dates
    # We use a set of dates to check for overlaps with normal class days
    processed_dates = set()

    for month_str, day, year, desc in important_dates:
        month_num = month_map.get(month_str)
        dt = datetime(year, month_num, day)
        processed_dates.add(dt.date())
        
        ics_content.append("BEGIN:VEVENT")
        ics_content.append(f"SUMMARY:{desc}")
        ics_content.append(f"DTSTART:{dt.strftime('%Y%m%dT000000Z')}")
        ics_content.append(f"DTEND:{dt.strftime('%Y%m%dT01000000Z')}")
        ics_content.append("DESCRIPTION:Academic milestone from Mckinney Tamil Academy schedule")
        ics_content.append("END:VEVENT")

    # 3. Generate "Normal Class" days (Sundays)
    # Range: Start of school to final test
    start_date = datetime(2026, 8, 9)
    end_date = datetime(2027, 5, 2)
    
    current_date = start_date
    while current_date <= end_date:
        # Sunday is 6 in the weekday() system (Monday=0, Sunday=6)
        if current_date.weekday() == 6:
            # Only add if it's not an "Important Date" or a "Holiday" already listed
            if current_date.date() not in processed_dates:
                ics_content.append("BEGIN:VEVENT")
                ics_content.append("SUMMARY:Normal Class Day")
                ics_content.append(f"DTSTART:{current_date.strftime('%Y%m%dT000000Z')}")
                ics_content.append(f"DTEND:{current_date.strftime('%Y%m%dT01000000Z')}")
                ics_content.append("DESCRIPTION:Regular weekly academy class")
                ics_content.append("END:VEVENT")
        
        current_date += timedelta(days=1)

    ics_content.append("END:VCALENDAR")

    # 4. Write to file
    file_name = "mckinney_academy_schedule_full.ics"
    with open(file_name, "w") as f:
        f.write("\n".join(ics_content))
    
    print(f"Successfully created {file_name}")

if __name__ == "__main__":
    create_mckinney_calendar()
