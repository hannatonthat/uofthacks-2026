"""Calendly utility for creating meeting scheduling links (placeholder)."""

import os
import json
import requests
from typing import Optional


# Calendly API base URL
CALENDLY_API_BASE = "https://api.calendly.com"


def create_single_use_link(event_type_name: str, invitee_email: str) -> str:
    """
    Create a Calendly scheduling link.
    
    Args:
        event_type_name: Name of the event type
        invitee_email: Email of the invitee
    
    Returns:
        Calendly scheduling link URL
    """
    api_key = os.getenv('CALENDLY_API_KEY')
    
    if not api_key:
        # No API key - return mock link with logging
        mock_link = f"https://calendly.com/mock/{event_type_name.lower().replace(' ', '-')}/{invitee_email.split('@')[0]}"
        print(f"[MOCK] Calendly link created (no API key):")
        print(f"  Event: {event_type_name}")
        print(f"  Invitee: {invitee_email}")
        print(f"  Link: {mock_link}")
        return mock_link
    
    try:
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # Step 1: Get current user to find event types
        user_response = requests.get(
            f"{CALENDLY_API_BASE}/users/me",
            headers=headers
        )
        user_response.raise_for_status()
        user_data = user_response.json()
        user_uri = user_data['resource']['uri']
        
        # Step 2: Get event types for this user
        event_types_response = requests.get(
            f"{CALENDLY_API_BASE}/event_types",
            headers=headers,
            params={'user': user_uri, 'active': 'true'}
        )
        event_types_response.raise_for_status()
        event_types = event_types_response.json()['collection']
        
        # Step 3: Find matching event type by name (or use first one)
        matching_event = None
        for et in event_types:
            if event_type_name.lower() in et['name'].lower():
                matching_event = et
                break
        
        if not matching_event and event_types:
            matching_event = event_types[0]  # Use first event type if no match
        
        if not matching_event:
            print(f"[ERROR] No event types found in Calendly account")
            return f"https://calendly.com/no-events/{invitee_email.split('@')[0]}"
        
        # Step 4: Create single-use scheduling link
        scheduling_link_response = requests.post(
            f"{CALENDLY_API_BASE}/scheduling_links",
            headers=headers,
            json={
                'max_event_count': 1,
                'owner': matching_event['uri'],
                'owner_type': 'EventType'
            }
        )
        scheduling_link_response.raise_for_status()
        scheduling_data = scheduling_link_response.json()
        
        booking_url = scheduling_data['resource']['booking_url']
        
        print(f"✓ Calendly link created:")
        print(f"  Event: {matching_event['name']}")
        print(f"  Invitee: {invitee_email}")
        print(f"  Link: {booking_url}")
        
        return booking_url
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Calendly API error: {str(e)}")
        if hasattr(e.response, 'text'):
            print(f"  Response: {e.response.text}")
        # Fall back to mock link
        return f"https://calendly.com/error-fallback/{invitee_email.split('@')[0]}"
    except Exception as e:
        print(f"[ERROR] Failed to create Calendly link: {str(e)}")
        # Fall back to mock link
        return f"https://calendly.com/error-fallback/{invitee_email.split('@')[0]}"


def get_event_types() -> list:
    """
    Get list of available event types from Calendly.
    
    Returns:
        List of event type dicts with id and name
    """
    api_key = os.getenv('CALENDLY_API_KEY')
    
    if not api_key:
        print("[INFO] No Calendly API key configured")
        return []
    
    try:
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            f"{CALENDLY_API_BASE}/user/profile",
            headers=headers
        )
        response.raise_for_status()
        
        user_id = response.json()['resource']['uri']
        
        # Get event types
        response = requests.get(
            f"{CALENDLY_API_BASE}/event_types",
            headers=headers,
            params={'user': user_id}
        )
        response.raise_for_status()
        
        event_types = response.json()['collection']
        print(f"✓ Found {len(event_types)} Calendly event types")
        for et in event_types:
            print(f"  - {et['name']}: {et['uri']}")
        
        return event_types
        
    except Exception as e:
        print(f"[ERROR] Failed to get Calendly event types: {str(e)}")
        return []


def verify_calendly_setup() -> dict:
    """
    Verify Calendly is properly configured.
    
    Returns:
        Dict with configuration status
    """
    api_key = os.getenv('CALENDLY_API_KEY')
    
    status = {
        'configured': bool(api_key),
        'api_key_set': bool(api_key),
        'event_types': []
    }
    
    if api_key:
        status['event_types'] = get_event_types()
    else:
        print("[INFO] Calendly API key not configured in environment")
        print("  Set CALENDLY_API_KEY environment variable to enable real Calendly integration")
    
    return status
