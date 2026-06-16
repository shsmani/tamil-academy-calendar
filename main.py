import os
import re
import requests
from bs4 import BeautifulSoup
from icalendar import Calendar, Event
from datetime import datetime
import pytz

def build_calendar():
    url = "https://www.catamilacademy.org/MckinneyTamilAcademy.html"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract all text to easily search for their date format
    page_text = soup.get_text(separator=' ')
    
    # Regex pattern to match their format: "Aug 11th. First day of school."
    pattern = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})(?:st|nd|rd|th)\.\s+([^.]+)'
    matches = re.findall(pattern, page_text)
    
    cal = Calendar()
    cal.add('prodid', '-//McKinney Tamil Academy Calendar//')
    cal.add('version', '2.0')
    cal.add('x-wr-calname', 'Tamil Academy Schedule')
    
    tz = pytz.timezone('America/Chicago')
    
    # Determine the school year based on the current date
    current_year = datetime.now().year
    current_month = datetime.now().month
    start_year = current_year if current_month >= 6 else current_year - 1
    
    months = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6, 
              'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
    
    for month_str, day_str, description in matches:
        month = months[month_str]
        day = int(day_str)
        
        # August to December belong to the start year, Jan to May belong to the next year
        event_year = start_year if month >= 8 else start_year + 1
        
        # The site says classes are 4:00 PM to 5:30 PM
        event_date = tz.localize(datetime(event_year, month, day, 16, 0, 0))
        end_date = tz.localize(datetime(event_year, month, day, 17, 30, 0))
        
        event = Event()
        event.add('summary', description.strip())
        
        # If the text mentions a holiday, make it an all-day event so it doesn't block your afternoon schedule
        if "Holiday" in description or "break" in description.lower():
            event.add('dtstart', event_date.date())
        else:
            event.add('dtstart', event_date)
            event.add('dtend', end_date)
            
        cal.add_component(event)
        
    # Save the file into a public folder
    os.makedirs('public', exist_ok=True)
    with open('public/calendar.ics', 'wb') as f:
        f.write(cal.to_ical())

if __name__ == "__main__":
    build_calendar()
