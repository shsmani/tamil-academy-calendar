import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

URL = "https://www.catamilacademy.org/MckinneyTamilAcademy.html"

def fetch_and_generate():
    response = requests.get(URL)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Locate table rows with schedule data
    rows = soup.find_all("tr")
    events = []

    for row in rows:
        cols = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
        if len(cols) >= 2:
            # Match date pattern e.g., "Aug 09, 2026" or "08/09/2026"
            date_match = re.search(r"([A-Za-z]{3}\s+\d{1,2},\s+\d{4})", cols[0])
            if date_match:
                date_str = date_match.group(1)
                description = cols[1]
                
                try:
                    dt = datetime.strptime(date_str, "%b %d, %Y")
                    formatted_date = dt.strftime("%Y%m%d")
                    events.append((formatted_date, description))
                except ValueError:
                    continue

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

    for date_str, desc in events:
        ics_lines.extend([
            "BEGIN:VEVENT",
            f"SUMMARY:Tamil Class - {desc}",
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
