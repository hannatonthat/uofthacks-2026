"""Gmail API integration for sending outreach emails."""

import os
import base64
from email.mime.text import MIMEText
from typing import Optional, Dict, List
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle


class GmailIntegration:
    """Send emails via Gmail API with OAuth2 authentication."""
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.send']
    
    def __init__(self, credentials_path: str = "credentials.json", token_path: str = "token.pickle"):
        """
        Initialize Gmail API client.
        
        SETUP INSTRUCTIONS:
        1. Go to Google Cloud Console (console.cloud.google.com)
        2. Create a project and enable Gmail API
        3. Create OAuth 2.0 credentials (Desktop app)
        4. Download credentials.json
        5. Place in backend/ directory
        
        PARAMETERS:
          credentials_path: Path to OAuth credentials JSON file
          token_path: Path to store/load authentication token
        
        AUTHENTICATION FLOW:
          - First run: Opens browser for OAuth consent
          - Stores token in token.pickle for future use
          - Subsequent runs: Reuses stored token
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API using OAuth2."""
        creds = None
        
        # Load existing token if available
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Gmail credentials not found at {self.credentials_path}. "
                        "Download from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save token for next run
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('gmail', 'v1', credentials=creds)
        print("✓ Gmail API authenticated successfully")
    
    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        from_name: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Send an email via Gmail API.
        
        PARAMETERS:
          to: Recipient email address
          subject: Email subject line
          body: Email body (plain text or HTML)
          from_name: Optional display name for sender
        
        RETURNS:
          Dict with:
            - id: Gmail message ID
            - threadId: Gmail thread ID
            - status: "sent"
        
        EXAMPLE:
          gmail = GmailIntegration()
          result = gmail.send_email(
              to="chief@tribe.ca",
              subject="Consultation Request: Sustainable Land Development",
              body="Dear Chief Sarah,\n\nWe respectfully request...",
              from_name="Indigenous Land Perspectives Team"
          )
          print(f"Email sent! ID: {result['id']}")
        
        ERROR HANDLING:
          Raises HttpError if Gmail API fails
        """
        try:
            # Create message
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            if from_name:
                message['from'] = from_name
            
            # Encode message
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Send via Gmail API
            send_message = {'raw': raw}
            result = self.service.users().messages().send(
                userId='me',
                body=send_message
            ).execute()
            
            print(f"✓ Email sent to {to}: {result['id']}")
            
            return {
                "id": result['id'],
                "threadId": result['threadId'],
                "status": "sent",
                "to": to,
                "subject": subject
            }
        
        except HttpError as error:
            raise RuntimeError(f"Gmail API error: {error}")
    
    def send_batch_emails(
        self,
        recipients: List[Dict[str, str]],
        subject_template: str,
        body_template: str
    ) -> List[Dict[str, str]]:
        """
        Send personalized emails to multiple recipients.
        
        PARAMETERS:
          recipients: List of dicts with keys: email, name, role
          subject_template: Subject with {name} placeholder
          body_template: Body with {name}, {role} placeholders
        
        RETURNS:
          List of send results (one per recipient)
        
        EXAMPLE:
          contacts = [
              {"email": "chief@tribe.ca", "name": "Chief Sarah", "role": "Tribal Leader"},
              {"email": "env@gov.bc.ca", "name": "Dr. James", "role": "Environmental Officer"}
          ]
          
          results = gmail.send_batch_emails(
              recipients=contacts,
              subject_template="Consultation Request for {name}",
              body_template="Dear {name},\n\nAs {role}, your input is vital..."
          )
        """
        results = []
        
        for recipient in recipients:
            # Personalize subject and body
            subject = subject_template.format(**recipient)
            body = body_template.format(**recipient)
            
            # Send email
            result = self.send_email(
                to=recipient['email'],
                subject=subject,
                body=body
            )
            results.append(result)
        
        return results
    
    def get_sent_emails(self, max_results: int = 10) -> List[Dict[str, str]]:
        """
        Retrieve recently sent emails.
        
        PARAMETERS:
          max_results: Number of emails to fetch
        
        RETURNS:
          List of sent emails with id, subject, to, date
        
        USAGE:
          Check which outreach emails have been sent
        """
        try:
            results = self.service.users().messages().list(
                userId='me',
                labelIds=['SENT'],
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            sent_emails = []
            
            for msg in messages:
                message = self.service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['Subject', 'To', 'Date']
                ).execute()
                
                headers = {h['name']: h['value'] for h in message['payload']['headers']}
                sent_emails.append({
                    'id': msg['id'],
                    'subject': headers.get('Subject', ''),
                    'to': headers.get('To', ''),
                    'date': headers.get('Date', '')
                })
            
            return sent_emails
        
        except HttpError as error:
            raise RuntimeError(f"Gmail API error: {error}")
