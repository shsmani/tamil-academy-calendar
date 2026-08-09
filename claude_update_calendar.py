#!/usr/bin/env python3
"""
mta_calendar_to_ics.py

Scrapes the Metroplex Tamil Academy - McKinney schedule page and produces
a clean .ics calendar file with:
  - School Open dates   (first day of school / term restarts)
  - School Close dates  (term end dates)
  - Test dates
  - Holidays
  - Regular class days   (every Sunday session in between, 4:00-5:30 PM)

Data source:
  https://www.catamilacademy.org/MckinneyTamilAcademy.html

How it works
------------
The page has two overlapping sources of the same information:
  1. A month-by-month HTML calendar grid where individual day numbers are
     styled (bold/colored/underlined) to indicate class days, holidays,
     tests, and special days (legend at the top of the "Schedule" section).
  2. An "IMPORTANT DATES" text table that spells out the same events with
     an explicit date + description (e.g. "Aug 30th -> Test 1 - Project 1").

This script parses BOTH:
  - `parse_calendar_grid()` walks each month's <table> and pulls out any
    day whose cell has an inline style indicating red/yellow/underline
    (site's own legend: red=Holiday, yellow=Test, underline=special day).
  - `parse_important_dates()` parses the "IMPORTANT DATES" text block,
    which is more descriptive (has the actual holiday/test names).

The two sources are then merged by date: the descriptive text-table entry
wins for the event title, but if the calendar grid flags a date that has
no matching table entry, it's still included (labeled generically) so
nothing gets dropped. Per the request, "Term Dates" summary lines
(the Term-1/2/3 start-end range recap near the bottom of the page) are
intentionally skipped -- that info is redundant with the per-event
Open/Close entries already captured above it.

On top of that, `fill_regular_class_days()` figures out each term's date
range directly from the parsed Open/Close events (pairing each "school
open" date with the next "school close" date), then adds a "Class Day"
event for every Sunday in between that isn't already a Holiday. This
covers the ordinary weeks where nothing special happens but class is
still in session. Since the page states class runs 4:00-5:30 PM Sundays,
any date with a Class/Open/Close/Test tag (i.e. an actual session) is
given that as a timed event; pure Holidays stay all-day (no class).

Usage:
    pip install requests beautifulsoup4
    python3 mta_calendar_to_ics.py
    # -> writes MTA_McKinney_2026-2027.ics in the current directory
"""

import re
import sys
import uuid
import datetime
from collections import defaultdict

import requests
from bs4 import BeautifulSoup

URL = "https://www.catamilacademy.org/MckinneyTamilAcademy.html"
OUTPUT_FILE = "MTA_McKinney_2026-2027.ics"

MONTH_MAP = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

# Categories, in priority order for the emoji/prefix used in the summary
CATEGORY_PREFIX = {
    "Open": "\U0001F7E2 Open",       # green circle
    "Close": "\U0001F534 Close",     # red circle
    "Test": "\U0001F4DD Test",       # memo
    "Holiday": "\U0001F3D6 Holiday",  # beach (matches red "holiday" theme)
    "Class": "\U0001F4DA Class",     # books
}

# Regular Sunday session time, per the page ("4.00 PM - 5.30 PM")
CLASS_START_TIME = (16, 0)   # 4:00 PM
CLASS_END_TIME = (17, 30)    # 5:30 PM
CLASS_TZID = "America/Chicago"  # McKinney, TX

# Categories that represent an actual in-session Sunday (get a timed event
# instead of an all-day marker)
SESSION_CATEGORIES = {"Open", "Close", "Test", "Class"}


def fetch_soup(url=URL):
    resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def school_year_for_month(month):
    """Aug-Dec belong to 2026, Jan-May belong to 2027, per the page title
    'Schedule 2026-2027'. Adjust here if the page year ever changes."""
    return 2026 if month >= 8 else 2027


def ordinal_date_to_iso(date_str, month_hint=None):
    """Convert strings like 'Aug 09th' -> datetime.date(2026, 8, 9)."""
    m = re.match(r"([A-Za-z]{3})\w*\s+(\d{1,2})", date_str)
    if not m:
        return None
    mon_abbr, day = m.group(1)[:3].title(), int(m.group(2))
    month = MONTH_MAP.get(mon_abbr)
    if not month:
        return None
    year = school_year_for_month(month)
    try:
        return datetime.date(year, month, day)
    except ValueError:
        return None


def categorize(desc):
    """Return a list of categories that apply to a table description."""
    d = desc.lower()
    cats = []
    if "first day of school" in d or ("term" in d and "start" in d):
        cats.append("Open")
    if "term" in d and "end" in d:
        cats.append("Close")
    if "final test" in d:
        cats.append("Close")
    if "test" in d or "project" in d or "review" in d:
        cats.append("Test")
    if "holiday" in d:
        cats.append("Holiday")
    if not cats:
        cats.append("Other")
    return cats


def parse_important_dates(soup):
    """Parse the 'IMPORTANT DATES' block: alternating date / description
    lines, stopping before the 'Term Dates:' recap section (skipped per
    the user's request)."""
    text = soup.get_text("\n")
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

    try:
        start = next(i for i, ln in enumerate(lines) if "IMPORTANT DATES" in ln.upper())
    except StopIteration:
        return []
    try:
        end = next(i for i, ln in enumerate(lines) if i > start and ln.strip().rstrip(":").upper() == "TERM DATES")
    except StopIteration:
        end = len(lines)

    section = lines[start + 1:end]

    date_re = re.compile(r"^[A-Za-z]{3}\w*\s+\d{1,2}(st|nd|rd|th)$")
    events = []
    i = 0
    while i < len(section):
        line = section[i]
        if date_re.match(line):
            desc = section[i + 1] if i + 1 < len(section) else ""
            date_obj = ordinal_date_to_iso(line)
            if date_obj:
                events.append({"date": date_obj, "desc": desc, "categories": categorize(desc)})
            i += 2
        else:
            i += 1
    return events


def parse_calendar_grid(soup):
    """Best-effort parse of the colored month-by-month calendar grid.
    Flags any day cell whose inline style/attrs suggest red (holiday),
    yellow (test), or underline (special day), per the page's own legend.
    Returns generic-label events, used only to fill gaps not already
    covered by the IMPORTANT DATES table."""
    events = []
    month_headers = soup.find_all(string=re.compile(r"^[A-Za-z]{3} 20\d{2}$"))

    for header in month_headers:
        m = re.match(r"([A-Za-z]{3})\s+(\d{4})", header.strip())
        if not m:
            continue
        month = MONTH_MAP.get(m.group(1)[:3].title())
        year = int(m.group(2))
        if not month:
            continue

        table = header.find_parent().find_next("table") if header.find_parent() else None
        if table is None:
            continue

        for cell in table.find_all(["td", "th"]):
            style = (cell.get("style") or "").lower()
            classes = " ".join(cell.get("class") or []).lower()
            txt = cell.get_text(strip=True)
            if not txt.isdigit():
                continue
            day = int(txt)

            has_font_red = cell.find("font", attrs={"color": re.compile("red", re.I)}) is not None
            has_font_yellow = cell.find("font", attrs={"color": re.compile("yellow|#ff.?00", re.I)}) is not None
            is_underline = "underline" in style or cell.find("u") is not None

            cats = []
            if "red" in style or has_font_red or "holiday" in classes:
                cats.append("Holiday")
            if "yellow" in style or has_font_yellow or "test" in classes:
                cats.append("Test")
            if is_underline:
                cats.append("Open")

            if cats:
                try:
                    d = datetime.date(year, month, day)
                except ValueError:
                    continue
                events.append({"date": d, "desc": "(from calendar formatting)", "categories": cats})
    return events


def merge_events(table_events, calendar_events):
    """Merge by date. Descriptive table entries take priority; calendar
    flags only fill in categories/dates the table didn't already cover."""
    merged = defaultdict(lambda: {"desc": None, "categories": set()})

    for ev in table_events:
        rec = merged[ev["date"]]
        rec["desc"] = ev["desc"]
        rec["categories"].update(ev["categories"])

    for ev in calendar_events:
        rec = merged[ev["date"]]
        rec["categories"].update(ev["categories"])
        if rec["desc"] is None:
            rec["desc"] = ev["desc"]

    return merged


def infer_term_ranges(merged_events):
    """Pair each 'Open' date with the next chronological 'Close' date to
    reconstruct term start/end ranges, without needing to separately parse
    the (skipped) 'Term Dates:' recap section."""
    opens = sorted(d for d, rec in merged_events.items() if "Open" in rec["categories"])
    closes = sorted(d for d, rec in merged_events.items() if "Close" in rec["categories"])

    ranges = []
    used_closes = set()
    for start in opens:
        end = next((c for c in closes if c >= start and c not in used_closes), None)
        if end:
            ranges.append((start, end))
            used_closes.add(end)
    return ranges


def fill_regular_class_days(merged_events):
    """Add a 'Class' category (and a 'Regular Class Day' entry where no
    other description exists yet) for every Sunday inside each term's
    open->close range that isn't a Holiday."""
    ranges = infer_term_ranges(merged_events)

    for start, end in ranges:
        # jump to the first Sunday on/after start
        offset = (6 - start.weekday()) % 7  # Monday=0 ... Sunday=6
        d = start + datetime.timedelta(days=offset)
        while d <= end:
            rec = merged_events[d]  # defaultdict creates it if new
            if "Holiday" not in rec["categories"]:
                rec["categories"].add("Class")
                if rec["desc"] is None:
                    rec["desc"] = "Regular Class Day"
            d += datetime.timedelta(days=7)

    return merged_events


def build_ics(merged_events, calendar_name="Metroplex Tamil Academy - McKinney"):
    now = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//MTA McKinney Calendar Scraper//EN",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{calendar_name}",
    ]

    for date_obj in sorted(merged_events):
        rec = merged_events[date_obj]
        cats = rec["categories"] - {"Other"} or {"Other"}
        # priority order for display prefix (Holiday wins - no class that day)
        primary = next((c for c in ["Holiday", "Close", "Open", "Test", "Class"] if c in cats), "Other")
        prefix = CATEGORY_PREFIX.get(primary, "")
        desc = rec["desc"] or primary
        summary = f"{prefix}: {desc}" if prefix else desc

        is_session = bool(cats & SESSION_CATEGORIES) and "Holiday" not in cats

        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{uuid.uuid4()}@mta-mckinney")
        lines.append(f"DTSTAMP:{now}")

        if is_session:
            sh, sm = CLASS_START_TIME
            eh, em = CLASS_END_TIME
            dtstart = date_obj.strftime("%Y%m%d") + f"T{sh:02d}{sm:02d}00"
            dtend = date_obj.strftime("%Y%m%d") + f"T{eh:02d}{em:02d}00"
            lines.append(f"DTSTART;TZID={CLASS_TZID}:{dtstart}")
            lines.append(f"DTEND;TZID={CLASS_TZID}:{dtend}")
        else:
            dtstart = date_obj.strftime("%Y%m%d")
            dtend = (date_obj + datetime.timedelta(days=1)).strftime("%Y%m%d")
            lines.append(f"DTSTART;VALUE=DATE:{dtstart}")
            lines.append(f"DTEND;VALUE=DATE:{dtend}")

        lines.append(f"SUMMARY:{summary}")
        lines.append(f"CATEGORIES:{','.join(sorted(cats))}")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    # ICS spec wants CRLF line endings
    return "\r\n".join(lines) + "\r\n"


def main():
    print(f"Fetching {URL} ...")
    try:
        soup = fetch_soup()
    except requests.exceptions.RequestException as e:
        print(f"ERROR: could not fetch the page: {e}", file=sys.stderr)
        sys.exit(1)

    table_events = parse_important_dates(soup)
    print(f"Parsed {len(table_events)} events from the IMPORTANT DATES table.")

    calendar_events = parse_calendar_grid(soup)
    print(f"Parsed {len(calendar_events)} flagged days from the calendar grid.")

    merged = merge_events(table_events, calendar_events)
    print(f"Merged into {len(merged)} unique dated events.")

    merged = fill_regular_class_days(merged)
    n_class_only = sum(1 for rec in merged.values() if rec["categories"] == {"Class"})
    print(f"Added {n_class_only} regular class-day entries (plus Class tag on Open/Close/Test days).")

    if not merged:
        print("No events found -- the page structure may have changed.", file=sys.stderr)
        raw_text = soup.get_text("\n")
        print(f"DEBUG: fetched page text length = {len(raw_text)} characters", file=sys.stderr)
        print("DEBUG: first 1000 characters of fetched text:", file=sys.stderr)
        print(raw_text[:1000], file=sys.stderr)
        print("DEBUG: does raw text contain 'IMPORTANT DATES'? ->",
              "IMPORTANT DATES" in raw_text.upper(), file=sys.stderr)
        sys.exit(1)

    ics_text = build_ics(merged)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(ics_text)

    print(f"Wrote {OUTPUT_FILE}")

    # Quick summary printout
    for date_obj in sorted(merged):
        rec = merged[date_obj]
        print(f"  {date_obj.isoformat()}  [{','.join(sorted(rec['categories']))}]  {rec['desc']}")


if __name__ == "__main__":
    main()
