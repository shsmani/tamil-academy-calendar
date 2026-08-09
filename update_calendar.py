import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

URL = "http://www.catamilacademy.org/MckinneyTamilAcademy.html"

def fetch_and_generate():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    response = requests.get(URL, headers=headers)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")
    
    # 1. Dynamically parse the legend/key to map background colors or text markers to types
    # CTA pages generally use color coding or inline styles for Test / Holiday / Regular
    legend_map = {}
    for td in soup.find_all(["td", "th", "div", "span"]):
        text = td.get_text(strip=True).lower()
        style = td.get("style", "").lower()
        bgcolor = td.get("bgcolor", "").lower()
        
        color_info = f"{style} {bgcolor}"
        if "test" in text:
            legend_map["test"] = "TEST"
        elif "holiday" in text or "closed" in text:
            legend_map["holiday"] = "CLOSED"

    # 2. Extract schedule entries dynamically
    events = {}
    rows = soup.find_all("tr")

    # Tracking year context across academic years (e.g. Aug-Dec -> 2026, Jan-May -> 2027)
    base_year = datetime.now().year
    
    for row in rows:
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue
            
        col1_text = cells[0].get_text(" ", strip=True)
        col2_text = cells[1].get_text(" ", strip=True)
        
        # Match date formats like "Aug 09", "Aug 09, 2026", "08/09/2026", "Aug 09th"
        date_match = re.search(r"([A-Za-z]{3})\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{4}))?", col1_text)
        if not date_match:
            continue
            
        month_str, day_str, year_str = date_match.groups()
        
        # Infer academic year if not explicitly stated in the row
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

        description = col2_text if col2_text else "Class Day"
        row_str = (row.get_text() + " " + str(row)).lower()
        
        # Dynamic type determination based on row content or style attributes
        event_type = "OPEN"
        if "test" in row_str or "exam" in row_str:
            event_type = "TEST"
        elif "holiday" in row_str or "closed" in row_str or "no class" in row_str or "break" in row_str:
            event_type = "CLOSED"

        events[formatted_date] = {
            "title": description,
            "type": event_type
        }

    # 3. Generate .ics file output
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
