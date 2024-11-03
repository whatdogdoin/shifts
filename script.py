import os
import base64
import re
import time
import hashlib
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/calendar']

def authenticate_gmail_calendar():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=57053)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def load_processed_emails(filename='processed_emails.txt'):
    if not os.path.exists(filename):
        return set()
    with open(filename, 'r') as f:
        return set(line.strip() for line in f)

def save_processed_email(email_id, filename='processed_emails.txt'):
    with open(filename, 'a') as f:
        f.write(f"{email_id}\n")

def fetch_emails(service, sender_email="no.reply@innout.com", earliest_date="2024/11/01"):
    try:
        # Add the after filter to the query to only include emails after the specified date
        query = f"from:{sender_email} subject:INO # Schedule after:{earliest_date}"
        results = service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])
        return messages
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def parse_event_details(subject, email_content):
    # Parse HTML content and clean it
    soup = BeautifulSoup(email_content, "html.parser")
    plain_text = soup.get_text(separator=" ")
        
    # Extract week range from subject line
    week_match = re.search(r"Schedule (\d{2}/\d{2}/\d{2}) - (\d{2}/\d{2}/\d{2})", subject)
    if not week_match:
        print("No week range found in subject line.")
        return None

    week_start = datetime.strptime(week_match.group(1), '%m/%d/%y')
    shifts = []

    # Updated regex to capture days and shift times, including "OFF" status
    day_pattern = re.compile(r"(\b\w{3}\b):\s*(\d{2}/\d{2})\s*([0-9]{1,2}:[0-9]{2}(?:am|pm)-[0-9]{1,2}:[0-9]{2}(?:am|pm)|OFF)", re.IGNORECASE)

    # Check for a mandatory meeting if it exists
    meeting_match = re.search(r"Mandatory Store Meeting on (\d{2}/\d{2}/\d{4}) at (\d{1,2}:\d{2} (?:AM|PM))", plain_text)
    if meeting_match:
        meeting_date = datetime.strptime(meeting_match.group(1), '%m/%d/%Y')
        meeting_time = datetime.strptime(meeting_match.group(2), '%I:%M %p').time()
        meeting_datetime = datetime.combine(meeting_date, meeting_time)
        
        shifts.append({
            "summary": "Mandatory Store Meeting",
            "start": meeting_datetime,
            "end": meeting_datetime + timedelta(hours=1)  # Assume 1-hour meeting duration
        })

    for match in day_pattern.finditer(plain_text):
        day, date, time_range = match.groups()
        shift_date = datetime.strptime(date, '%m/%d').replace(year=week_start.year)
        
        if time_range.upper() == "OFF":
            continue
        
        start_time, end_time = time_range.split('-')
        start_datetime = datetime.strptime(f"{shift_date.strftime('%Y-%m-%d')} {start_time}", '%Y-%m-%d %I:%M%p')
        end_datetime = datetime.strptime(f"{shift_date.strftime('%Y-%m-%d')} {end_time}", '%Y-%m-%d %I:%M%p')
        
        # If the end time is before the start time, add one day to the end time
        if end_datetime <= start_datetime:
            end_datetime += timedelta(days=1)

        shifts.append({
            "summary": f"{day} Shift",
            "start": start_datetime,
            "end": end_datetime
        })

    return shifts

def generate_event_id(event_details):
    event_string = f"{event_details['summary']}-{event_details['start']}-{event_details['end']}"
    return hashlib.md5(event_string.encode()).hexdigest()


def event_exists(calendar_service, calendar_id, event_id):
    try:
        events_result = calendar_service.events().list(
            calendarId=calendar_id,
            q=event_id,  # Search for the event ID in the event description
            singleEvents=True
        ).execute()

        events = events_result.get('items', [])
        for event in events:
            if event_id in event.get('description', ''):
                print(f"Event already exists for event ID: {event_id}")
                return True
        return False
    except Exception as e:
        print("Error during event_exists check:", e)
        return False

def create_calendar_event(calendar_service, calendar_id, event_details):
    event_id = generate_event_id(event_details)
    if event_exists(calendar_service, calendar_id, event_id):
        print(f"Event '{event_details['summary']}' already exists for event ID: {event_id}. Skipping.")
        return

    event = {
        'summary': "INO",
        'description': f"Event ID: {event_id}",
        'start': {'dateTime': event_details["start"].isoformat(), 'timeZone': 'PST'},
        'end': {'dateTime': event_details["end"].isoformat(), 'timeZone': 'PST'},
    }
    calendar_service.events().insert(calendarId=calendar_id, body=event).execute()
    print(f"Event created: {event_details['summary']} from {event_details['start']} to {event_details['end']}.")
    
def check_for_new_emails():
    creds = authenticate_gmail_calendar()
    gmail_service = build('gmail', 'v1', credentials=creds)
    calendar_service = build('calendar', 'v3', credentials=creds)

    target_calendar_id = "dd6bbc8230435c66819832f4d34ad3fc3000eb386db4e1fbff8d1a36bee93f58@group.calendar.google.com"  # Replace with your actual calendar ID
    processed_emails = load_processed_emails()

    while True:
        emails = fetch_emails(gmail_service)
        if not emails:
            print("No new event emails found.")
        else:
            for email in emails:
                email_id = email['id']

                if email_id in processed_emails:
                    print(f"Skipping duplicate email ID: {email_id}")
                    continue

                message = gmail_service.users().messages().get(userId='me', id=email_id).execute()
                subject = next(header['value'] for header in message['payload']['headers'] if header['name'] == 'Subject')
                email_content = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')
                
                shifts = parse_event_details(subject, email_content)

                if shifts:
                    for shift in shifts:
                        create_calendar_event(calendar_service, target_calendar_id, shift)
                    save_processed_email(email_id)
                else:
                    print(f'No valid event details found in email: {subject}')
        
        print("Waiting for 12 hours before checking for new emails...")
        time.sleep(43200)

if __name__ == '__main__':
    check_for_new_emails()
