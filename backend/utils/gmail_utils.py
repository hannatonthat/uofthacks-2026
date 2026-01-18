"""Gmail utility for sending emails via Gmail API with OAuth2."""

import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


def get_gmail_service():
    """Get authenticated Gmail API service."""
    creds = None
    # Get the directory where this file is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(current_dir)  # Go up to backend/
    
    token_path = os.path.join(backend_dir, 'token.json')
    credentials_path = os.path.join(backend_dir, 'credentials.json')
    
    # Load existing token
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Check if we're using web or installed app credentials
            with open(credentials_path, 'r') as f:
                import json
                cred_data = json.load(f)
                
            if 'web' in cred_data:
                # Web application - need to set redirect URI
                print("ERROR: Web application credentials detected.")
                print("Please create Desktop/Installed app credentials instead:")
                print("1. Go to https://console.cloud.google.com/apis/credentials")
                print("2. Create OAuth 2.0 Client ID")
                print("3. Select 'Desktop app' as application type")
                print("4. Download and replace credentials.json")
                raise ValueError("Web credentials not supported. Please use Desktop app credentials.")
            else:
                # Installed/Desktop app
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
        
        # Save credentials for next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    
    return build('gmail', 'v1', credentials=creds)


def send_gmail(to_email: str, subject: str, body: str, from_email: str = "me"):
    """
    Send an email via Gmail API.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body (plain text)
        from_email: Sender (default: "me" = authenticated user)
    
    Returns:
        Message ID of sent email
    
    Raises:
        Exception: If email sending fails
    """
    try:
        service = get_gmail_service()
        
        # Create message
        message = MIMEMultipart()
        message['to'] = to_email
        message['subject'] = subject
        
        # Add body
        message.attach(MIMEText(body, 'plain'))
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Send
        send_message = service.users().messages().send(
            userId=from_email,
            body={'raw': raw_message}
        ).execute()
        
        print(f"✓ Email sent to {to_email} (Message ID: {send_message['id']})")
        return send_message['id']
        
    except Exception as e:
        raise Exception(f"Failed to send email to {to_email}: {str(e)}")


def send_bulk_emails(recipients: list, subject: str, body: str):
    """
    Send emails to multiple recipients.
    
    Args:
        recipients: List of email addresses
        subject: Email subject
        body: Email body
    
    Returns:
        Dict with sent_count and errors list
    """
    sent_count = 0
    errors = []
    
    for email in recipients:
        try:
            send_gmail(email, subject, body)
            sent_count += 1
        except Exception as e:
            errors.append(f"{email}: {str(e)}")
    
    return {
        "sent_count": sent_count,
        "errors": errors
    }
