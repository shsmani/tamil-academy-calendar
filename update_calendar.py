import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

URL = "http://www.catamilacademy.org/MckinneyTamilAcademy.html"

def fetch_and_generate():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    response = requests.get(URL, headers=headers)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")
    
    events = {}
    base_year = datetime.now().year

    # Extract all text blocks from table cells to preserve row relationship
    cells = soup.find_all(["td", "th"])
    
    for i, cell in enumerate(cells):
        text = cell.get_text(" ", strip=True)
        
        # Look for explicit month/day pattern (e.g., "Aug 09", "Nov 15", "Jan 24")
        date_match = re.search(r"\b([A-Za-z]{3})\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{4}))?\b", text)
        if not date_match:
            continue
            
        month_str, day_str, year_str = date_match.groups()
        
        # Calculate dynamic year based on academic year structure (Aug-Dec vs Jan-May)
        if year_str:
            year = int(year_str)
        else:
            if month_str.capitalize() in ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]:
                year = base_year + 1
            else:
                year = base_year

        try:
            dt = datetime.strptime(f"{month_str} {day_str} {year}", "%b %d %Y")
            formatted_date = dt.strftime("%Y%m%d")
        except ValueError:
            continue

        # Look in the current cell or the immediate next cell for the description
        description = ""
        # Check remaining text in the same cell after the date
        remaining_in_cell = text[date_match.end():].strip(" :-|")
        if len(remaining_in_cell) > 2:
            description = remaining_in_cell
        elif i + 1 < len(cells):
            next_text = cells[i + 1].get_text(" ", strip=True)
            if not re.search(r"\b[A-Za-z]{3}\s+\d{1,2}\b", next_text):
                description = next_text

        if not description:
            description = "Class Day"

        # Determine event type dynamically
        desc_lower = description.lower()
        cell_lower = text.lower()
        combined_text = f"{cell_lower} {desc_lower}"

        event_type = "OPEN"
        if "test" in combined_text or "exam" in combined_text:
            event_type = "TEST"
        elif any(k in combined_text for k in ["holiday", "closed", "no class", "break", "deepawali", "thanksgiving", "christmas", "new year", "annual day"]):
            event_type = "CLOSED"

        events[formatted_date] = {
            "title": description,
            "type": event_type
        }

    # Generate .ics output
    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//McKinney Tamil Academy//Schedule//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Tamil Academy Schedule",
        "X-WR-TIMEZONE:America/Chicago"
    ]

    for date_str in sorted(events.keys()):
        item = events[date_str]
        title = item["title"]
        e_type = item["type"]

        if e_type == "CLOSED":
            summary = f"Tamil Class - [CLOSED] {title}"
        elif e_type == "TEST":
            summary = f"Tamil Class - [TEST] {title}"
        else:
            summary = f"Tamil Class - {title}"

        ics_lines.extend([
            "BEGIN:VEVENT",
            f"SUMMARY:{summary}",
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
