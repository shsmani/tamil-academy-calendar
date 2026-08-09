import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

URL = "http://www.catamilacademy.org/MckinneyTamilAcademy.html"

def fetch_and_generate():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(URL, headers=headers, timeout=15)
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        print(f"Error fetching page: {e}")
        return

    # Extract all visible text strings as an ordered list
    strings = [s.strip() for s in soup.stripped_strings if s.strip()]
    
    events = {}
    base_year = datetime.now().year

    # Regex to identify date strings like "Aug 09", "Aug 09, 2026", "08/09/2026"
    date_pattern = re.compile(r"^\b([A-Za-z]{3})\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{4}))?\b", re.IGNORECASE)

    for i, token in enumerate(strings):
        match = date_pattern.search(token)
        if match:
            month_str, day_str, year_str = match.groups()
            
            # Infer academic year if year is omitted (Aug-Dec -> 2026, Jan-May -> 2027)
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

            # Check if there is remaining description text in the same token after the date
            remaining = token[match.end():].strip(" :-|")
            description = ""

            if len(remaining) > 2:
                description = remaining
            else:
                # Look ahead at subsequent tokens to find the event title
                lookahead_idx = i + 1
                while lookahead_idx < len(strings):
                    next_token = strings[lookahead_idx]
                    # Stop if we hit another date marker
                    if date_pattern.search(next_token):
                        break
                    # Ignore short noise tokens
                    if len(next_token) > 2:
                        description = next_token
                        break
                    lookahead_idx += 1

            if not description:
                description = "Regular Class"

            # Categorize dynamically based on text keywords
            combined_text = f"{token} {description}".lower()
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
