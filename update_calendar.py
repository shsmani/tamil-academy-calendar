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
    
    # Extract all text content while preserving line breaks to keep descriptions aligned with dates
    text_content = soup.get_text(separator="\n")
    
    events = {}
    
    # Pattern matches line blocks containing dates like "Aug 09, 2026", "Aug 09", or "08/09/2026"
    # followed immediately or closely by description text on the same or next line
    pattern = re.compile(
        r"([A-Za-z]{3}\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*,?\s*\d{4})?|\d{1,2}/\d{1,2}/\d{4})\s*[:\-\|]?\s*(.*)",
        re.IGNORECASE
    )

    base_year = datetime.now().year

    for line in text_content.splitlines():
        line = line.strip()
        if not line:
            continue
            
        match = re.search(r"([A-Za-z]{3})\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{4}))?", line)
        if match:
            month_str, day_str, year_str = match.groups()
            
            # Dynamically handle academic year context (Aug-Dec vs Jan-May)
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

            # Extract the rest of the text on that line as the description
            desc = line[match.end():].strip(" :-|")
            description = desc if desc else "Class Day"
            
            # Dynamic type categorization based on text keywords
            line_lower = line.lower()
            event_type = "OPEN"
            if "test" in line_lower or "exam" in line_lower:
                event_type = "TEST"
            elif "holiday" in line_lower or "closed" in line_lower or "no class" in line_lower or "break" in line_lower or "deepawali" in line_lower or "thanksgiving" in line_lower:
                event_type = "CLOSED"

            events[formatted_date] = {
                "title": description,
                "type": event_type
            }

    # Fallback check: If the page structure isolates text into separate tags, extract by regex pairs
    if not events:
        raw_text = soup.get_text(separator=" ", strip=True)
        # Search for occurrences of Date + Event description
        pair_matches = re.findall(
            r"([A-Za-z]{3}\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*,?\s*\d{4})?)\s+([A-Za-z0-9\s\-\(\)]+)", 
            raw_text
        )
        for date_part, desc_part in pair_matches:
            m = re.search(r"([A-Za-z]{3})\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{4}))?", date_part)
            if m:
                m_str, d_str, y_str = m.groups()
                y = int(y_str) if y_str else (base_year + 1 if m_str.capitalize() in ["Jan", "Feb", "Mar", "Apr", "May"] else base_year)
                try:
                    dt = datetime.strptime(f"{m_str} {d_str} {y}", "%b %d %Y")
                    f_date = dt.strftime("%Y%m%d")
                except ValueError:
                    continue
                
                desc_lower = desc_part.lower()
                e_type = "OPEN"
                if "test" in desc_lower or "exam" in desc_lower:
                    e_type = "TEST"
                elif "holiday" in desc_lower or "closed" in desc_lower or "break" in desc_lower:
                    e_type = "CLOSED"

                events[f_date] = {"title": desc_part.strip(), "type": e_type}

    # Build .ics output
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
