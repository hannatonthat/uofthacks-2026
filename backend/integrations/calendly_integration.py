"""Calendly API integration for scheduling consultation meetings."""

import os
import requests
from typing import Optional, Dict, List
from datetime import datetime, timedelta


class CalendlyIntegration:
    """Schedule meetings via Calendly API."""
    
    BASE_URL = "https://api.calendly.com"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Calendly API client.
        
        SETUP INSTRUCTIONS:
        1. Sign up for Calendly (calendly.com)
        2. Go to Integrations & Apps > API & Webhooks
        3. Generate a Personal Access Token
        4. Add CALENDLY_API_KEY to .env
        
        PARAMETERS:
          api_key: Calendly Personal Access Token (or load from env)
        
        AUTHENTICATION:
          Uses Bearer token authentication
          Token format: eyJraWQiOiIxY2UxZ...
        """
        self.api_key = api_key or os.getenv("CALENDLY_API_KEY")
        if not self.api_key:
            raise ValueError("CALENDLY_API_KEY not found in environment")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Get current user info
        self.user = self._get_current_user()
        print(f"✓ Calendly API authenticated: {self.user['name']}")
    
    def _get_current_user(self) -> Dict:
        """Get current Calendly user information."""
        response = requests.get(
            f"{self.BASE_URL}/users/me",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()['resource']
    
    def get_event_types(self) -> List[Dict]:
        """
        Get available event types (meeting templates).
        
        RETURNS:
          List of event types with:
            - uri: Event type URI for scheduling
            - name: Event name (e.g., "Consultation Meeting")
            - duration: Meeting duration in minutes
            - scheduling_url: Public booking link
        
        USAGE:
          event_types = calendly.get_event_types()
          consultation_event = next(
              e for e in event_types if "Consultation" in e['name']
          )
          print(f"Book at: {consultation_event['scheduling_url']}")
        """
        response = requests.get(
            f"{self.BASE_URL}/event_types",
            headers=self.headers,
            params={"user": self.user['uri']}
        )
        response.raise_for_status()
        
        event_types = []
        for item in response.json()['collection']:
            event_types.append({
                'uri': item['uri'],
                'name': item['name'],
                'duration': item['duration'],
                'scheduling_url': item['scheduling_url'],
                'description': item.get('description_plain', '')
            })
        
        return event_types
    
    def create_scheduling_link(
        self,
        event_type_name: str,
        recipient_name: str,
        recipient_email: str
    ) -> Dict[str, str]:
        """
        Generate a personalized scheduling link for a recipient.
        
        PARAMETERS:
          event_type_name: Name of event type (e.g., "Consultation Meeting")
          recipient_name: Name to pre-fill in booking form
          recipient_email: Email to pre-fill in booking form
        
        RETURNS:
          Dict with:
            - scheduling_url: Personalized Calendly booking link
            - event_type: Event type name
            - recipient: Recipient info
        
        EXAMPLE:
          link = calendly.create_scheduling_link(
              event_type_name="Indigenous Consultation",
              recipient_name="Chief Sarah",
              recipient_email="chief@tribe.ca"
          )
          
          # Send this link in outreach email:
          print(f"Book your consultation: {link['scheduling_url']}")
        
        NOTES:
          - Calendly API doesn't support creating invitations directly
          - Instead, generates a pre-filled booking link
          - Recipient clicks link and selects their preferred time
          - You receive notification when they book
        """
        # Find matching event type
        event_types = self.get_event_types()
        event_type = next(
            (e for e in event_types if event_type_name.lower() in e['name'].lower()),
            None
        )
        
        if not event_type:
            raise ValueError(
                f"Event type '{event_type_name}' not found. "
                f"Available: {[e['name'] for e in event_types]}"
            )
        
        # Build pre-filled URL
        scheduling_url = event_type['scheduling_url']
        personalized_url = (
            f"{scheduling_url}?"
            f"name={requests.utils.quote(recipient_name)}&"
            f"email={requests.utils.quote(recipient_email)}"
        )
        
        return {
            'scheduling_url': personalized_url,
            'event_type': event_type['name'],
            'duration': event_type['duration'],
            'recipient': {
                'name': recipient_name,
                'email': recipient_email
            }
        }
    
    def get_scheduled_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_results: int = 20
    ) -> List[Dict]:
        """
        Get scheduled events (booked meetings).
        
        PARAMETERS:
          start_date: Filter events starting from this date (default: now)
          end_date: Filter events until this date (default: 30 days from now)
          max_results: Maximum number of events to return
        
        RETURNS:
          List of scheduled events with:
            - name: Event name
            - start_time: ISO 8601 datetime
            - end_time: ISO 8601 datetime
            - invitee_name: Guest name
            - invitee_email: Guest email
            - status: "active" or "canceled"
        
        EXAMPLE:
          events = calendly.get_scheduled_events()
          for event in events:
              print(f"{event['name']} with {event['invitee_name']}")
              print(f"  Time: {event['start_time']}")
        """
        # Default date range
        if not start_date:
            start_date = datetime.utcnow()
        if not end_date:
            end_date = start_date + timedelta(days=30)
        
        # Format dates for API
        params = {
            "user": self.user['uri'],
            "min_start_time": start_date.isoformat() + "Z",
            "max_start_time": end_date.isoformat() + "Z",
            "count": max_results,
            "status": "active"
        }
        
        response = requests.get(
            f"{self.BASE_URL}/scheduled_events",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        
        events = []
        for item in response.json()['collection']:
            # Get invitee details
            invitees_response = requests.get(
                f"{self.BASE_URL}/scheduled_events/{item['uri'].split('/')[-1]}/invitees",
                headers=self.headers
            )
            invitees = invitees_response.json()['collection']
            
            invitee = invitees[0] if invitees else {}
            
            events.append({
                'uri': item['uri'],
                'name': item['name'],
                'start_time': item['start_time'],
                'end_time': item['end_time'],
                'status': item['status'],
                'invitee_name': invitee.get('name', ''),
                'invitee_email': invitee.get('email', ''),
                'location': item.get('location', {}).get('join_url', '')
            })
        
        return events
    
    def create_batch_scheduling_links(
        self,
        event_type_name: str,
        recipients: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """
        Generate scheduling links for multiple recipients.
        
        PARAMETERS:
          event_type_name: Event type to use for all links
          recipients: List of dicts with keys: name, email
        
        RETURNS:
          List of personalized scheduling links
        
        EXAMPLE:
          contacts = [
              {"name": "Chief Sarah", "email": "chief@tribe.ca"},
              {"name": "Dr. James", "email": "james@env.gov.bc.ca"}
          ]
          
          links = calendly.create_batch_scheduling_links(
              event_type_name="Consultation",
              recipients=contacts
          )
          
          for link in links:
              print(f"Send to {link['recipient']['name']}: {link['scheduling_url']}")
        """
        links = []
        
        for recipient in recipients:
            link = self.create_scheduling_link(
                event_type_name=event_type_name,
                recipient_name=recipient['name'],
                recipient_email=recipient['email']
            )
            links.append(link)
        
        return links
