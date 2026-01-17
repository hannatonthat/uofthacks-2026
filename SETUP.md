# Setup & Configuration Guide

## API Keys Required

### 1. **Backboard API Key** (LLM Access - Claude/Gemini)
```bash
BACKBOARD_API_KEY=your_backboard_key_here
```
- Get from: https://backboard.io
- Used for: AI-driven workflow execution, email generation, sustainability analysis
- Add to: `.env` file

### 2. **Google API Key** (Street View Panorama Generation)
```bash
GOOGLE_API_MAP_KEY=your_google_api_key_here
```
- Get from: [Google Cloud Console](https://console.cloud.google.com/)
- Enable APIs: 
  - Street View Static API
  - Gemini API (for image generation)
- Add to: `.env` file

### 3. **Gmail Integration** (Email Sending via OAuth2)
```bash
# Download credentials from Google Cloud Console OAuth2 setup
# Place file as: backend/credentials.json
```
- Go to: [Google Cloud Console](https://console.cloud.google.com/)
- Create OAuth2 credentials (Desktop app)
- Download JSON file → save as `backend/credentials.json`
- First run will create `backend/token.pickle` automatically
- Used for: Sending outreach emails, bulk email campaigns

### 4. **Calendly API Key** (Meeting Scheduling)
```bash
CALENDLY_API_KEY=your_calendly_api_key_here
```
- Get from: [Calendly Settings](https://calendly.com/app/settings)
- Navigate to: Integrations → API & Webhooks → Generate new token
- Add to: `.env` file
- Used for: Creating scheduling links, booking consultation meetings

### 5. **Slack Webhook URL** (Optional - Team Notifications)
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```
- Get from: [Slack App Console](https://api.slack.com/apps)
- Create incoming webhook for your workspace channel
- Add to: `.env` file
- Used for: Workflow status notifications, completion alerts

---

## Installation Steps

### 1. Clone & Setup Backend
```bash
cd /Users/nuthanantharmarajah/uofthacks-2026

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
cd backend
pip install -r requirements.txt
pip install -r requirements-test.txt  # For testing
```

### 2. Configure Environment Variables
```bash
# Create .env file in backend/ directory
cat > backend/.env << EOF
# LLM & APIs
BACKBOARD_API_KEY=your_backboard_key_here
GOOGLE_API_MAP_KEY=your_google_api_key_here
CALENDLY_API_KEY=your_calendly_api_key_here
SLACK_WEBHOOK_URL=your_slack_webhook_url_here

# Optional: Anthropic API (if using separately)
# ANTHROPIC_API_KEY=your_anthropic_key_here
EOF
```

### 3. Setup Gmail OAuth2
```bash
# Download OAuth2 credentials from Google Cloud Console
# Save to: backend/credentials.json

# First run of Gmail integration will open browser for OAuth approval
# Creates backend/token.pickle automatically for future runs
```

### 4. Verify Setup
```bash
# Test imports
python3 << EOF
from integrations import GmailIntegration, CalendlyIntegration, SlackIntegration
from agents import SustainabilityAgent, IndigenousContextAgent, ProposalWorkflowAgent
print("✓ All integrations loaded successfully")
EOF
```

---

## API Key Quick Reference

| Service | Key Name | Where to Get | Purpose |
|---------|----------|-------------|---------|
| **Backboard** | `BACKBOARD_API_KEY` | backboard.io | AI models (Claude/Gemini) |
| **Google** | `GOOGLE_API_MAP_KEY` | Google Cloud Console | Street View + Gemini image generation |
| **Gmail** | `credentials.json` | Google Cloud Console | OAuth2 email sending |
| **Calendly** | `CALENDLY_API_KEY` | calendly.com/settings | Meeting scheduling links |
| **Slack** | `SLACK_WEBHOOK_URL` | api.slack.com | Team notifications |

---

## Run Application

### Start Backend Server
```bash
cd backend
python3 main.py
# Server runs on http://localhost:8000
```

### Start Frontend (if needed)
```bash
cd frontend
npm install
npm run dev
# Frontend runs on http://localhost:3000
```

---

## Run Tests

### All Tests
```bash
pytest backend/tests/test_workflows.py -v
```

### By Category
```bash
pytest backend/tests/test_workflows.py -m unit        # Unit tests only
pytest backend/tests/test_workflows.py -m integration # Integration tests
pytest backend/tests/test_workflows.py -m ai          # AI workflow tests
```

### With Coverage
```bash
pytest backend/tests/test_workflows.py --cov=backend --cov-report=html
open htmlcov/index.html
```

### Specific Test
```bash
pytest backend/tests/test_workflows.py::TestGmailIntegration::test_send_email_success -v
```

---

## API Endpoints

### Panorama Generation
```bash
curl -X POST http://localhost:8000/generate-panorama \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 43.6632,
    "longitude": -79.3957,
    "name": "Toronto Street View"
  }'
```

### Sustainability Chat
```bash
curl -X POST http://localhost:8000/create-sustainability-chat \
  -H "Content-Type: application/json" \
  -d '{
    "image_path": "path/to/panorama.png",
    "thread_id": "optional_thread_id"
  }'
```

### Add Contact
```bash
curl -X POST http://localhost:8000/workflow/add-contact \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Chief Sarah",
    "email": "chief@tribe.ca",
    "role": "Tribal Leader"
  }'
```

### Send Emails (AI-driven)
```bash
curl -X POST http://localhost:8000/execute-workflow/ai-driven \
  -H "Content-Type: application/json" \
  -d '{
    "user_intent": "Send consultation emails to all stakeholders about the land project"
  }'
```

### Schedule Meetings
```bash
curl -X POST http://localhost:8000/execute-workflow/schedule-meetings
```

### View Contacts
```bash
curl http://localhost:8000/workflow/contacts
```

### View Workflow History
```bash
curl http://localhost:8000/workflow/history
```

---

## Troubleshooting

### Gmail Auth Issues
```bash
# Remove cached token and re-authenticate
rm backend/token.pickle
python3 main.py
# Browser will open for OAuth approval
```

### Backboard API Errors
```bash
# Verify API key is set
echo $BACKBOARD_API_KEY

# Check if using correct model
# Claude: gpt-4o-mini, gpt-4o
# Gemini: gemini-2.5-flash
```

### Calendly Errors
```bash
# Verify API key format (should be "Bearer YOUR_KEY")
curl -H "Authorization: Bearer $CALENDLY_API_KEY" \
  https://api.calendly.com/users/me

# Should return your user info
```

### Port Already in Use
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or change port in main.py
```

---

## Project Structure

```
backend/
├── main.py                          # FastAPI server
├── requirements.txt                 # Dependencies
├── requirements-test.txt            # Testing dependencies
├── credentials.json                 # Gmail OAuth2 (create yourself)
├── token.pickle                     # Gmail token (auto-generated)
├── .env                            # API keys (create yourself)
├── integrations/
│   ├── gmail_integration.py        # Email sending
│   ├── calendly_integration.py     # Meeting scheduling
│   └── slack_integration.py        # Team notifications
├── agents/
│   ├── agents.py                   # Base agent class
│   ├── specialized_agents.py       # Three specialized agents
│   ├── workflow_tools.py           # AI-driven tool selection
│   ├── backboard_provider.py       # LLM provider wrapper
│   └── prompts_config.py           # Centralized prompts
└── tests/
    └── test_workflows.py           # Comprehensive test suite

frontend/
├── package.json
├── next.config.ts
├── app/
│   ├── page.tsx                    # Main page
│   ├── layout.tsx                  # Layout
│   └── globals.css                 # Styles
└── public/                         # Static assets
```

---

## Next Steps

1. ✅ Get all API keys (see table above)
2. ✅ Create `.env` file with keys
3. ✅ Create `backend/credentials.json` for Gmail
4. ✅ Run `pip install -r requirements.txt`
5. ✅ Start server: `python3 main.py`
6. ✅ Test endpoints with curl or Postman
7. ✅ Run test suite: `pytest backend/tests/test_workflows.py -v`

**That's it! You're ready to go.** 🚀
