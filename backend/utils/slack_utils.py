"""Slack utility for sending notifications."""

import os
import json
import requests
from typing import Optional


def send_slack_notification(message: str, webhook_url: Optional[str] = None) -> bool:
    """
    Send a notification to Slack.
    
    Args:
        message: Message to send to Slack
        webhook_url: Slack webhook URL (uses SLACK_WEBHOOK_URL env var if not provided)
    
    Returns:
        True if sent successfully, False otherwise
    
    Raises:
        ValueError: If no webhook URL is configured
    """
    if not webhook_url:
        webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    
    if not webhook_url:
        print("[MOCK] Slack notification (no webhook configured):")
        print(f"  Message: {message}")
        return False
    
    try:
        payload = {
            'text': message,
            'mrkdwn': True
        }
        
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        
        print(f"✓ Slack notification sent: {message}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to send Slack notification: {str(e)}")
        print(f"  Message was: {message}")
        return False


def log_workflow_event(event_type: str, details: dict) -> None:
    """
    Log a workflow event for debugging.
    
    Args:
        event_type: Type of event (email_sent, meeting_scheduled, etc)
        details: Event details as dict
    """
    log_entry = {
        'event_type': event_type,
        'details': details
    }
    
    # Log to console
    print(f"[WORKFLOW] {event_type}: {json.dumps(details, indent=2)}")
    
    # Optionally log to file
    log_file = os.getenv('WORKFLOW_LOG_FILE')
    if log_file:
        try:
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            print(f"[WARNING] Could not write to log file: {e}")
