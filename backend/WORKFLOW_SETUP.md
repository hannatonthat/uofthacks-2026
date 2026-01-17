# Workflow Automation Setup Guide

## Overview
The ProposalWorkflowAgent now executes workflows directly instead of just providing suggestions. It integrates with Gmail API and Calendly API to automatically send outreach emails and schedule consultation meetings.

## Features
- ✅ **Generate personalized emails** using LLM (Claude/Gemini)
- ✅ **Send emails automatically** via Gmail API
- ✅ **Create scheduling links** via Calendly API
- ✅ **Full workflow automation** (generate + schedule + send in one call)
- ✅ **Track workflow history** (emails sent, meetings scheduled)

---

## Setup Instructions

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements-integrations.txt
```

### 2. Gmail API Setup

#### Step 1: Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or select existing)
3. Enable Gmail API:
   - Navigate to "APIs & Services" → "Library"
   - Search for "Gmail API"
   - Click "Enable"

#### Step 2: Create OAuth Credentials
1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Configure consent screen:
   - User type: External (for testing) or Internal (for organization)
   - App name: "Indigenous Land Perspectives"
   - Support email: Your email
   - Authorized domains: localhost (for testing)
4. Create OAuth client ID:
   - Application type: Desktop app
   - Name: "Indigenous Land Perspectives - Desktop"
5. Download credentials JSON file
6. Save as `credentials.json` in `backend/` directory

#### Step 3: First-Time Authentication
```bash
# Run backend server
python main.py

# Make any workflow request (will trigger OAuth flow)
# Browser will open for authentication
# Grant permissions (send emails on your behalf)
# Token saved to token.pickle for future use
```

### 3. Calendly API Setup

#### Step 1: Create Calendly Account
1. Sign up at [calendly.com](https://calendly.com)
2. Create event types for consultations:
   - Go to "Event Types"
   - Create "Indigenous Consultation" (60 min)
   - Set availability preferences

#### Step 2: Generate API Key
1. Go to "Integrations & Apps" → "API & Webhooks"
2. Click "Generate Personal Access Token"
3. Copy the token

#### Step 3: Add to Environment
```bash
# Add to backend/.env
CALENDLY_API_KEY=your_calendly_token_here
```

---

## API Endpoints

### 1. Add Contacts to Workflow

```bash
curl -X POST 'http://localhost:8000/workflow/add-contact?threadid=THREAD_ID&name=Chief%20Sarah&role=Tribal%20Leader&email=chief@tribe.ca&phone=250-555-1234'
```

### 2. Get Contacts List

```bash
curl 'http://localhost:8000/workflow/contacts?threadid=THREAD_ID'
```

### 3. Execute: Send Emails Only

```bash
curl -X POST 'http://localhost:8000/execute-workflow/send-emails?threadid=THREAD_ID' \
  -H "Content-Type: application/json" \
  -d '{"proposal_title":"Sustainable Land Development with Indigenous Partnership"}'
```

### 4. Execute: Generate Scheduling Links Only

```bash
curl -X POST 'http://localhost:8000/execute-workflow/schedule-meetings?threadid=THREAD_ID' \
  -H "Content-Type: application/json" \
  -d '{"event_type_name":"Indigenous Consultation"}'
```

### 5. Execute: Full Workflow (Emails + Scheduling)

```bash
curl -X POST 'http://localhost:8000/execute-workflow/full-outreach?threadid=THREAD_ID' \
  -H "Content-Type: application/json" \
  -d '{
    "proposal_title":"Sustainable Land Development",
    "event_type_name":"Indigenous Consultation"
  }'
```

### 6. Get Workflow History

```bash
curl 'http://localhost:8000/workflow/history?threadid=THREAD_ID'
```

---

## Example Workflow

### Step 1: Create Proposal Workflow Thread

```bash
curl -X POST http://localhost:8000/create-chat \
  -H "Content-Type: application/json" \
  -d '{"agent":"proposal"}'
```

**Response:**
```json
{
  "thread_id": "abc-123-def-456",
  "agent": "ProposalWorkflowAgent",
  ...
}
```

### Step 2: Add Contacts

```bash
# Add tribal leader
curl -X POST 'http://localhost:8000/workflow/add-contact?threadid=abc-123-def-456&name=Chief%20Sarah&role=Tribal%20Leader&email=chief@tribe.ca'

# Add environmental officer
curl -X POST 'http://localhost:8000/workflow/add-contact?threadid=abc-123-def-456&name=Dr.%20James&role=Environmental%20Officer&email=james@env.gov.bc.ca'
```

### Step 3: Execute Full Outreach

```bash
curl -X POST 'http://localhost:8000/execute-workflow/full-outreach?threadid=abc-123-def-456' \
  -H "Content-Type: application/json" \
  -d '{
    "proposal_title":"Sustainable Urban Development with Indigenous Partnership",
    "event_type_name":"Indigenous Consultation"
  }'
```

**Response:**
```json
{
  "emails_sent": 2,
  "meetings_scheduled": 2,
  "results": [
    {
      "recipient": "Chief Sarah",
      "email": "chief@tribe.ca",
      "status": "sent",
      "email_id": "18f1a2b3c4d5e6f7",
      "scheduling_link": "https://calendly.com/your-link?name=Chief%20Sarah&email=chief@tribe.ca"
    },
    {
      "recipient": "Dr. James",
      "email": "james@env.gov.bc.ca",
      "status": "sent",
      "email_id": "28f1a2b3c4d5e6f8",
      "scheduling_link": "https://calendly.com/your-link?name=Dr.%20James&email=james@env.gov.bc.ca"
    }
  ],
  "errors": []
}
```

### Step 4: Check Workflow History

```bash
curl 'http://localhost:8000/workflow/history?threadid=abc-123-def-456'
```

**Response:**
```json
{
  "history": [
    {
      "action": "scheduling_link_created",
      "recipient": "Chief Sarah",
      "event_type": "Indigenous Consultation",
      "scheduling_url": "https://calendly.com/..."
    },
    {
      "action": "email_sent",
      "recipient": "Chief Sarah",
      "email": "chief@tribe.ca",
      "timestamp": "2026-01-17T10:30:00Z"
    },
    ...
  ],
  "count": 4
}
```

---

## What Gets Executed

### Email Generation (via LLM)
- **Subject:** Professional, culturally sensitive
- **Body:** 
  - Respectful greeting
  - Context about proposal
  - Emphasis on indigenous sovereignty and partnership
  - Clear call-to-action
  - Scheduling link embedded
- **Tone:** Professional, respectful, collaborative

### Email Sending (via Gmail API)
- Sent from your authenticated Gmail account
- Delivered to recipient's inbox
- Tracked with email ID
- Appears in your Gmail "Sent" folder

### Meeting Scheduling (via Calendly)
- Personalized booking link pre-filled with recipient's info
- Recipient clicks link → selects preferred time
- You receive automatic notification when booked
- Calendar invitation sent automatically

---

## Security & Privacy

### Gmail Permissions
- **Scope:** `gmail.send` (send emails only)
- **Token storage:** `token.pickle` (local file, not committed to git)
- **Revoke access:** Google Account → Security → Third-party apps

### Calendly Permissions
- **Scope:** Read event types, create scheduling links
- **Token storage:** Environment variable (`.env`)
- **Revoke access:** Calendly → Integrations & Apps → Revoke token

### Best Practices
- ✅ Use environment variables for API keys
- ✅ Add `token.pickle` to `.gitignore`
- ✅ Add `credentials.json` to `.gitignore`
- ✅ Use OAuth (not API keys) for Gmail
- ✅ Test with personal email before production

---

## Troubleshooting

### Gmail: "Credentials not found"
```
FileNotFoundError: Gmail credentials not found at credentials.json
```
**Solution:** Download OAuth credentials from Google Cloud Console and save as `credentials.json`

### Gmail: "OAuth consent screen required"
**Solution:** Configure OAuth consent screen in Google Cloud Console first

### Calendly: "API key not found"
```
ValueError: CALENDLY_API_KEY not found in environment
```
**Solution:** Add `CALENDLY_API_KEY=your_token` to `.env` file

### Calendly: "Event type not found"
```
ValueError: Event type 'Consultation' not found
```
**Solution:** Check available event types in Calendly dashboard, use exact name

---

## Future Enhancements

- [ ] **Email templates** - Save and reuse email templates
- [ ] **Follow-up automation** - Auto-send reminders if no response
- [ ] **Calendar integration** - Sync Calendly with Google Calendar
- [ ] **Webhook listeners** - React to booking confirmations
- [ ] **Analytics dashboard** - Track email open rates, response rates
- [ ] **Multi-language support** - Generate emails in multiple languages
- [ ] **Attachment support** - Include proposal PDFs in emails

---

## Support

For issues or questions:
- Check logs in terminal for detailed error messages
- Review Gmail API quotas (free tier: 100 emails/day)
- Verify Calendly API limits (free tier: 100,000 requests/month)
- Consult official docs: [Gmail API](https://developers.google.com/gmail/api) | [Calendly API](https://developer.calendly.com)
