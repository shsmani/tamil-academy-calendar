import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

URL = "http://www.catamilacademy.org/MckinneyTamilAcademy.html"

def fetch_and_generate():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    response = requests.get(URL, headers=headers)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Extract clean text from the entire page body
    page_text = soup.get_text(separator=" ", strip=True)

    # Regex pattern to capture dates like "Aug 09th 2026", "Aug 09, 2026", "Nov 15th", or "Jan 31st 2027"
    date_pattern = re.compile(
        r"([A-Za-z]{3})\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{4}))?",
        re.IGNORECASE
    )

    events = set() # Use a set to eliminate duplicate date entries
    
    # Default year context (academic year spans 2026-2027)
    current_year = 2026

    for match in date_pattern.finditer(page_text):
        month, day, year = match.groups()
        
        # If year isn't explicitly attached, infer based on month
        if not year:
            if month.capitalize() in ["Jan", "Feb", "Mar", "Apr", "May"]:
                year = "2027"
            else:
                year = "2026"

        try:
            date_obj = datetime.strptime(f"{month} {day} {year}", "%b %d %Y")
            formatted_date = date_obj.strftime("%Y%m%d")
            
            # Filter out dates outside the school year range
            if 20260801 <= int(formatted_date) <= 20270601:
                events.add(formatted_date)
        except ValueError:
            continue

    sorted_dates = sorted(list(events))

    # Build .ics content
    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//McKinney Tamil Academy//Schedule//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Tamil Academy Schedule",
        "X-WR-TIMEZONE:America/Chicago"
    ]

    for date_str in sorted_dates:
        ics_lines.extend([
            "BEGIN:VEVENT",
            "SUMMARY:Tamil Class - McKinney",
            f"DTSTART;TZID=America/Chicago:{date_str}T160000",
            f"DTEND;TZID=America/Chicago:{date_str}T173000",
            "LOCATION:Children's Lighthouse of McKinney, 7900 Stacy Rd, McKinney, TX 75070",
            "END:VEVENT"
        ])

    ics_lines.append("END:VCALENDAR")

    with open("calendar.ics", "w", encoding="utf-8") as f:
        f.write("\n".join(ics_lines))

if __name__ == "__main__":
    fetch_and_generate()
