import os
import base64
import re
import time
import hashlib
from datetime import datetime, timedelta
import subprocess
import sys
import json

# List of required dependencies
required_packages = [
    'beautifulsoup4',  # Correct package name for BeautifulSoup
    'google-auth',
    'google-auth-oauthlib',
    'google-auth-httplib2',
    'google-api-python-client'
]

def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def check_and_install_packages(packages):
    installed_packages = {pkg.key for pkg in pkg_resources.working_set}
    for package in packages:
        if package not in installed_packages:
            print(f"Package '{package}' not found. Installing...")
            install_package(package)
        else:
            print(f"Package '{package}' is already installed.")


def main():
    marker_file = 'dependencies_installed.txt'
    
    if not os.path.exists(marker_file):
        print("Marker file not found. Installing dependencies...")
        check_and_install_packages(required_packages)
        with open(marker_file, 'w') as file:
            file.write('Dependencies installed')
        print("Marker file created.")
    else:
        print("Marker file found. Skipping dependency installation.")

# Now import the required modules after ensuring they are installed
import pkg_resources
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from bs4 import BeautifulSoup

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

def fetch_emails(service, sender_email="no.reply@innout.com", earliest_date= (datetime.now() - timedelta(days=2)).strftime("%Y/%m/%d")):
    try:
        query = f"from:{sender_email} subject:INO # Schedule after:{earliest_date}"
        results = service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])
        return messages
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def parse_event_details(subject, email_content):
    soup = BeautifulSoup(email_content, "html.parser")
    plain_text = soup.get_text(separator=" ")
        
    week_match = re.search(r"Schedule.*?(\d{2}/\d{2}/\d{2}) - (\d{2}/\d{2}/\d{2})", subject)
    if not week_match:
        print("No week range found in subject line.")
        return None

    week_start = datetime.strptime(week_match.group(1), '%m/%d/%y')
    shifts = []

    day_pattern = re.compile(r"(\b\w{3}\b):\s*(\d{2}/\d{2})\s*([0-9]{1,2}:[0-9]{2}(?:am|pm)-[0-9]{1,2}:[0-9]{2}(?:am|pm)|OFF)", re.IGNORECASE)

    meeting_match = re.search(r"Mandatory Store Meeting on (\d{2}/\d{2}/\d{4}) at (\d{1,2}:\d{2} (?:AM|PM))", plain_text)
    if meeting_match:
        meeting_date = datetime.strptime(meeting_match.group(1), '%m/%d/%Y')
        meeting_time = datetime.strptime(meeting_match.group(2), '%I:%M %p').time()
        meeting_datetime = datetime.combine(meeting_date, meeting_time)
        
        shifts.append({
            "summary": "Mandatory Store Meeting",
            "start": meeting_datetime,
            "end": meeting_datetime + timedelta(hours=1)
        })

    for match in day_pattern.finditer(plain_text):
        day, date, time_range = match.groups()
        shift_date = datetime.strptime(date, '%m/%d').replace(year=week_start.year)
        
        if time_range.upper() == "OFF":
            continue
        
        start_time, end_time = time_range.split('-')
        start_datetime = datetime.strptime(f"{shift_date.strftime('%Y-%m-%d')} {start_time}", '%Y-%m-%d %I:%M%p')
        end_datetime = datetime.strptime(f"{shift_date.strftime('%Y-%m-%d')} {end_time}", '%Y-%m-%d %I:%M%p')
        
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
            q=event_id,
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

def create_calendar_event(calendar_service, calendar_ids, event_details):
    event_id = generate_event_id(event_details)
    for calendar_id in calendar_ids:
        if event_exists(calendar_service, calendar_id, event_id):
            print(f"Event '{event_details['summary']}' already exists in calendar {calendar_id} for event ID: {event_id}. Skipping.")
            continue

        event = {
            'summary': "INO",
            'description': f"Event ID: {event_id}",
            'start': {'dateTime': event_details["start"].isoformat(), 'timeZone': 'PST'},
            'end': {'dateTime': event_details["end"].isoformat(), 'timeZone': 'PST'},
        }
        calendar_service.events().insert(calendarId=calendar_id, body=event).execute()
        print(f"Event created in calendar {calendar_id}: {event_details['summary']} from {event_details['start']} to {event_details['end']}.")

def list_user_calendars(calendar_service):
    try:
        calendar_list = calendar_service.calendarList().list().execute()
        calendars = calendar_list.get('items', [])
        return calendars
    except HttpError as error:
        print(f'An error occurred: {error}')
        return []

def get_user_selected_calendars(calendar_service):
    if os.path.exists('selected_calendars.json'):
        with open('selected_calendars.json', 'r') as file:
            selected_calendar_ids = json.load(file)
        print("Loaded selected calendars from file.")
        return selected_calendar_ids

    calendars = list_user_calendars(calendar_service)
    if not calendars:
        print("No calendars found.")
        return []

    print("Available calendars:")
    for i, calendar in enumerate(calendars):
        print(f"{i + 1}. {calendar['summary']} (ID: {calendar['id']})")

    selected_indices = input("Enter the numbers of the calendars you want to use, separated by commas: ")
    selected_indices = [int(index.strip()) - 1 for index in selected_indices.split(',') if index.strip().isdigit()]

    selected_calendar_ids = [calendars[i]['id'] for i in selected_indices if 0 <= i < len(calendars)]

    with open('selected_calendars.json', 'w') as file:
        json.dump(selected_calendar_ids, file)
    print("Saved selected calendars to file.")

    return selected_calendar_ids

if __name__ == '__main__':
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/calendar']

    main()

    creds = authenticate_gmail_calendar()
    gmail_service = build('gmail', 'v1', credentials=creds)
    calendar_service = build('calendar', 'v3', credentials=creds)

    target_calendar_ids = get_user_selected_calendars(calendar_service)

    while True:
        emails = fetch_emails(gmail_service)
        if not emails:
            print("No new event emails found.")
        else:
            for email in emails:
                email_id = email['id']

                message = gmail_service.users().messages().get(userId='me', id=email_id).execute()
                subject = next(header['value'] for header in message['payload']['headers'] if header['name'] == 'Subject')
                email_content = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')
                
                shifts = parse_event_details(subject, email_content)

                if shifts:
                    for shift in shifts:
                        create_calendar_event(calendar_service, target_calendar_ids, shift)
                else:
                    print(f'No valid event details found in email: {subject}')
        
        print("Waiting for 12 hours before checking for new emails...")
        time.sleep(43200)
