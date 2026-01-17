"""Slack integration for team notifications."""

import os
import requests
from typing import Optional, Dict


class SlackIntegration:
    """Send notifications to Slack channels via webhooks."""
    
    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialize Slack integration with webhook URL.
        
        SETUP INSTRUCTIONS:
        1. Go to Slack workspace settings
        2. Navigate to Apps → Manage → Custom Integrations
        3. Click "Incoming Webhooks"
        4. Add to channel (e.g., #consultations)
        5. Copy webhook URL
        6. Add SLACK_WEBHOOK_URL to .env
        
        PARAMETERS:
          webhook_url: Slack webhook URL (or load from env)
        """
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        if not self.webhook_url:
            raise ValueError("SLACK_WEBHOOK_URL not found in environment")
        
        print("✓ Slack integration initialized")
    
    def send_message(
        self,
        message: str,
        channel: Optional[str] = None,
        username: str = "Workflow Bot",
        icon_emoji: str = ":robot_face:"
    ) -> Dict[str, str]:
        """
        Send a message to Slack channel.
        
        PARAMETERS:
          message: Message text to send
          channel: Optional channel override (e.g., "#consultations")
          username: Display name for bot
          icon_emoji: Emoji icon for bot
        
        RETURNS:
          Dict with status and response
        
        EXAMPLE:
          slack = SlackIntegration()
          result = slack.send_message(
              message="✓ 3 consultation emails sent successfully!",
              channel="#consultations"
          )
        """
        payload = {
            "text": message,
            "username": username,
            "icon_emoji": icon_emoji
        }
        
        if channel:
            payload["channel"] = channel
        
        response = requests.post(
            self.webhook_url,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"✓ Slack message sent: {message[:50]}...")
            return {
                "status": "sent",
                "message": message,
                "channel": channel or "default"
            }
        else:
            raise RuntimeError(f"Slack API error: {response.status_code} - {response.text}")
    
    def send_workflow_update(
        self,
        action: str,
        details: Dict[str, any]
    ) -> Dict[str, str]:
        """
        Send formatted workflow update to Slack.
        
        PARAMETERS:
          action: Type of workflow action (e.g., "emails_sent", "meetings_scheduled")
          details: Dict with action details
        
        EXAMPLE:
          slack.send_workflow_update(
              action="emails_sent",
              details={"count": 3, "recipients": ["Chief Sarah", "Dr. James"]}
          )
        """
        # Format message based on action type
        if action == "emails_sent":
            count = details.get("count", 0)
            recipients = details.get("recipients", [])
            message = f"📧 *Emails Sent*\n• Count: {count}\n• Recipients: {', '.join(recipients)}"
        
        elif action == "meetings_scheduled":
            count = details.get("count", 0)
            event_type = details.get("event_type", "Consultation")
            message = f"📅 *Meetings Scheduled*\n• Count: {count}\n• Type: {event_type}"
        
        elif action == "full_outreach_complete":
            emails = details.get("emails_sent", 0)
            meetings = details.get("meetings_scheduled", 0)
            message = f"🚀 *Full Outreach Complete*\n• Emails: {emails}\n• Meetings: {meetings}"
        
        else:
            message = f"ℹ️ *Workflow Update*\n• Action: {action}\n• Details: {details}"
        
        return self.send_message(message)
    
    def send_consultation_booked(
        self,
        attendee_name: str,
        attendee_email: str,
        meeting_time: str
    ) -> Dict[str, str]:
        """
        Send notification when a consultation is booked.
        
        EXAMPLE:
          slack.send_consultation_booked(
              attendee_name="Chief Sarah",
              attendee_email="chief@tribe.ca",
              meeting_time="2026-01-20 10:00 AM"
          )
        """
        message = (
            f"✅ *New Consultation Booked*\n"
            f"• Attendee: {attendee_name}\n"
            f"• Email: {attendee_email}\n"
            f"• Time: {meeting_time}"
        )
        return self.send_message(message)
