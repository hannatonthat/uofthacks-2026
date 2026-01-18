"""Google Calendar utility for creating meetings directly on calendar."""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any


def get_calendar_service():
    """Get authenticated Google Calendar API service."""
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        print("[ERROR] Google Calendar libraries not installed. Run: pip install google-auth-oauthlib google-api-python-client")
        return None
    
    # Scopes for Google Calendar
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    
    # Path to credentials
    credentials_path = Path(__file__).parent.parent / "credentials.json"
    token_path = Path(__file__).parent.parent / "token_calendar.json"
    
    creds = None
    
    # Load existing token
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except Exception as e:
            print(f"[WARNING] Could not load calendar token: {e}")
    
    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"[ERROR] Could not refresh token: {e}")
                creds = None
        
        if not creds:
            if not credentials_path.exists():
                print(f"[ERROR] credentials.json not found at {credentials_path}")
                return None
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path), SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                print(f"[ERROR] Could not authenticate: {e}")
                return None
        
        # Save the credentials
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    
    try:
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        print(f"[ERROR] Could not build calendar service: {e}")
        return None


def create_calendar_meeting(
    contact_name: str,
    contact_email: str,
    event_title: str,
    description: str = "",
    duration_minutes: int = 30
) -> Optional[Dict[str, Any]]:
    """
    Create a meeting directly on Google Calendar and invite the contact.
    Meeting is booked on nuthanan06@gmail.com calendar.
    
    Args:
        contact_name: Name of the person to invite
        contact_email: Email address to invite
        event_title: Title of the meeting
        description: Meeting description
        duration_minutes: Duration in minutes (default 30)
    
    Returns:
        Dict with meeting details (id, link, start_time) or None if failed
    """
    service = get_calendar_service()
    
    if not service:
        print(f"[ERROR] Could not get calendar service")
        return None
    
    try:
        # Schedule meeting for 3 days from now at 2 PM (adjust as needed)
        start_time = datetime.utcnow() + timedelta(days=3)
        start_time = start_time.replace(hour=14, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        # Create event - will be on nuthanan06@gmail.com calendar
        event = {
            'summary': event_title,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat() + 'Z',
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat() + 'Z',
                'timeZone': 'UTC',
            },
            'attendees': [
                {'email': 'tharmarajahnuthanan@gmail.com', 'displayName': 'Nuthanan Tharmarajah'}
            ],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                    {'method': 'popup', 'minutes': 30},  # 30 minutes before
                ],
            },
            'conferenceData': {
                'createRequest': {
                    'requestId': f"meeting-{datetime.utcnow().timestamp()}",
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            }
        }
        
        # Insert event - on primary calendar (nuthanan06@gmail.com)
        event_result = service.events().insert(
            calendarId='primary',
            body=event,
            conferenceDataVersion=1,
            sendUpdates='all'  # Send email invitation to both
        ).execute()
        
        meeting_link = event_result.get('htmlLink')
        hangout_link = event_result.get('hangoutLink', 'N/A')
        
        print(f"✓ Google Calendar meeting created:")
        print(f"  Title: {event_title}")
        print(f"  Invited: tharmarajahnuthanan@gmail.com")
        print(f"  Contact Reference: {contact_name} ({contact_email})")
        print(f"  Time: {start_time.strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"  Link: {meeting_link}")
        print(f"  Meet: {hangout_link}")
        
        return {
            'id': event_result['id'],
            'link': meeting_link,
            'meet_link': hangout_link,
            'start_time': start_time.isoformat(),
            'contact_name': contact_name,
            'contact_email': contact_email
        }
        
    except Exception as e:
        print(f"[ERROR] Failed to create calendar meeting: {str(e)}")
        if hasattr(e, 'content'):
            print(f"  Response: {e.content}")
        return None


def list_upcoming_meetings(max_results: int = 10) -> list:
    """
    List upcoming meetings on the calendar.
    
    Args:
        max_results: Maximum number of meetings to return
    
    Returns:
        List of event dicts
    """
    service = get_calendar_service()
    
    if not service:
        return []
    
    try:
        now = datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            print('[INFO] No upcoming meetings found')
            return []
        
        print(f'[INFO] Found {len(events)} upcoming meetings:')
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(f"  - {event['summary']} at {start}")
        
        return events
        
    except Exception as e:
        print(f"[ERROR] Could not list meetings: {str(e)}")
        return []
