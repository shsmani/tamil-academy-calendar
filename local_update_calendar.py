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

    # 1. Extract Location Dynamically
    location = "Mckinney, TX"  # Default fallback
    location_text = soup.find(string=lambda t: "Classes are conducted at:" in t)
    if location_text:
        parent_text = location_text.parent.get_text()
        # Regex for: Numbers + Street + TX + Zip (e.g., 7900 Stacy Rd, TX 75070)
        addr_match = re.search(r'\d+ [\w\s]+, TX \d{5}', parent_text)
        if addr_match:
            location = addr_match.group(0)
        else:
            # Specific fallback if regex fails but text is found
            location = "Children's Lighthouse of McKinney, 7900 Stacy Rd, TX 75070"

    # 2. Extract Dates Dynamically
    important_dates = []
    processed_dates = set()
    
    # Get the entire text content to find the "IMPORTANT DATES" section
    full_text = soup.get_text()
    header_index = full_text.find("IMPORTANT DATES")
    
    if header_index != -1:
        # Slice text from the header to the end of the page
        target_text = full_text[header_index:]
        
        # Regex Breakdown:
        # ([A-Z][a-z]+) -> Month (e.g., Aug)
        # \s(\d{1,2}) -> Day (e.g., 09)
        # (?:st|nd|rd|th)? -> Optional suffix (e.g., 09th)
        # ,\s(\d{4}) -> Year (e.g., 2026)
        # \s-\s(.+?) -> The description, non-greedy
        # (?=\n|Term Dates|$) -> Stop at a newline, the next section, or end of string
        matches = re.findall(r'([A-Z][a-z]+)\s(\d{1,2})(?:st|nd|rd|th)?,\s(\d{4})\s-\s(.+?)(?=\n|Term Dates|$)', target_text)
        
        for month_str, day, year, desc in matches:
            # Clean up description to remove trailing punctuation/newlines
            desc = desc.strip().replace('\n', ' ')
            
            try:
                month_num = calendar.month_num[month_str]
                dt = datetime(int(year), month_num, int(day))
                important_dates.append((dt, desc))
                processed_dates.add(dt.date())
            except (KeyError, ValueError):
                continue

    # Error handling if the website changed so much that the regex failed
    if not important_dates:
        print("Error: Could not parse dates from the page using current logic.")
        return

    # Determine the bounds of the school year for Sunday generation
    sorted_dates = sorted(important_dates, key=lambda x: x[0])
    start_date = sorted_dates[0][0]
    end_date = sorted_dates[-1][0]

    # 3. Build the ICS
    ics_content = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Hermes Agent//Mckinney Tamil Academy//EN",
        "CALSCALE:GREGORIAN"
    ]

    timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    source_url = url

    # Process Extracted Dates
    for dt, desc in important_dates:
        unique_id = f"{dt.strftime('%Y%m%d')}_{desc.replace(' ', '_')[:10]}"
        
        ics_content.append("BEGIN:VEVENT")
        ics_content.append(f"UID:{unique_id}")
        ics_content.append(f"DTSTAMP:{timestamp}")
        ics_content.append(f"SUMMARY:{desc}")
        ics_content.append(f"LOCATION:{location}")
        ics_content.append(f"DESCRIPTION:Mckinney Tamil Academy: {desc}")
        ics_content.append(f"URL:{source_url}")
        # Standard All-Day format
        ics_content.append(f"DTSTART;VALUE=DATE:{dt.strftime('%Y%m%d')}")
        ics_content.append(f"DTEND;VALUE=DATE:{(dt + timedelta(days=1)).strftime('%Y%m%d')}")
        ics_content.append("END:VEVENT")

    # 4. Generate Sundays (Normal Class Days)
    current_date = start_date
    while current_date <= end_date:
        # Weekday 6 is Sunday
        if current_date.weekday() == 6:
            if current_date.date() not in processed_dates:
                unique_id = f"{current_date.strftime('%Y%m%d')}_normal_class"
                ics_content.append("BEGIN:VEVENT")
                ics_content.append(f"UID:{unique_id}")
                ics_content.append(f"DTSTAMP:{timestamp}")
                ics_content.append("SUMMARY:Normal Class Day")
                ics_content.append(f"LOCATION:{location}")
                ics_content.append("DESCRIPTION:Mckinney Tamil Academy: Regular weekly academy class")
                ics_content.append(f"URL:{source_url}")
                ics_content.append(f"DTSTART;VALUE=DATE:{current_date.strftime('%Y%m%d')}")
                ics_content.append(f"DTEND;VALUE=DATE:{(current_date + timedelta(days=1)).strftime('%Y%m%d')}")
                ics_content.append("END:VEVENT")
        
        current_date += timedelta(days=1)

    ics_content.append("END:VCALENDAR")

    file_name = "mckinney_academy_live_fully_dynamic.ics"
    with open(file_name, "w") as f:
        f.write("\n".join(ics_content))
    
    print(f"Successfully created {file_name}")
    print(f"Extracted Location: {location}")
    print(f"Extracted Start Date: {start_date.date()}")
    print(f"Extracted End Date: {end_date.date()}")

if __name__ == "__main__":
    create_live_calendar()
