# UofT Hacks 2026 - Indigenous Land Sustainability Platform

> **Quick Start**: See [SETUP.md](SETUP.md) for API keys and installation

## What This Does

Three-part system for visualizing and proposing sustainable land development with indigenous perspectives:

1. **Panorama Generation** - Street View stitching for 360° land visualization
2. **Sustainability Analysis** - AI-powered redesign suggestions respecting indigenous land stewardship
3. **Workflow Automation** - Gmail + Calendly integration for stakeholder outreach + AI-driven execution

---

## Core Features

### 🌍 Panorama Generation
- Generates 360° equirectangular panoramas from Street View
- Supports any latitude/longitude coordinates
- Outputs high-resolution images for sustainability analysis

### 🌱 Sustainability Chat
- Analyzes land and proposes redesigns
- Generates future-vision images with subtle enhancements (30-40% changes)
- Respects indigenous land use practices (trees on sidewalks, not roads)

### 📧 Workflow Automation
- **Gmail API**: Send personalized outreach emails
- **Calendly API**: Create scheduling links for meetings
- **Slack Integration**: Team notifications on workflow completion
- **AI-Driven**: Describe intent in natural language → AI chooses and executes workflow

---

## Setup (2 minutes)

### 1. Get API Keys
| Service | Key | Where |
|---------|-----|-------|
| Backboard | `BACKBOARD_API_KEY` | backboard.io |
| Google | `GOOGLE_API_MAP_KEY` | Google Cloud Console |
| Calendly | `CALENDLY_API_KEY` | calendly.com/settings |
| Slack | `SLACK_WEBHOOK_URL` | api.slack.com |
| Gmail | `credentials.json` | Google Cloud Console OAuth2 |

**Full setup guide**: [SETUP.md](SETUP.md)

### 2. Install & Run
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Add .env with API keys
python3 main.py
```

Server runs on `http://localhost:8000`

---

## API Examples

### Generate Panorama
```bash
curl -X POST http://localhost:8000/generate-panorama \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 43.6632,
    "longitude": -79.3957,
    "name": "Toronto"
  }'
```

### Add Contact & Send Emails
```bash
# Add contact
curl -X POST http://localhost:8000/workflow/add-contact \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Chief Sarah",
    "email": "chief@tribe.ca",
    "role": "Tribal Leader"
  }'

# Send emails via AI (natural language)
curl -X POST http://localhost:8000/execute-workflow/ai-driven \
  -H "Content-Type: application/json" \
  -d '{
    "user_intent": "Send consultation emails to all stakeholders"
  }'
```

### Schedule Meetings
```bash
curl -X POST http://localhost:8000/execute-workflow/schedule-meetings
```

**More endpoints** in [SETUP.md](SETUP.md)

---

## Run Tests

```bash
# All tests
pytest backend/tests/test_workflows.py -v

# By category
pytest backend/tests/test_workflows.py -m unit          # Unit tests
pytest backend/tests/test_workflows.py -m integration   # Integration tests
pytest backend/tests/test_workflows.py -m ai            # AI workflows

# With coverage
pytest backend/tests/test_workflows.py --cov=backend --cov-report=html
```

---

## Tech Stack

### Backend
- **FastAPI** - REST API server
- **LangChain** - AI tool orchestration
- **Backboard** - Unified LLM access (Claude/Gemini)
- **Google APIs** - Street View + Gemini image generation
- **Gmail API** - Email sending via OAuth2
- **Calendly API** - Meeting scheduling
- **Pytest** - Testing framework

### Frontend
- **Next.js** - React framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling

---

## Three Agents

### 1. SustainabilityAgent
- Analyzes land from panoramic images
- Generates 5 sustainable redesign suggestions
- Creates future-vision images with realistic enhancements
- **Key constraint**: 30-40% visible changes, logical placement

### 2. IndigenousContextAgent
- Provides indigenous land stewardship context
- Recommends water systems, biodiversity, cultural significance
- Integrates with sustainability analysis

### 3. ProposalWorkflowAgent
- Manages 10-step submission workflow
- Contacts list management
- **Workflow execution methods**:
  - `execute_send_emails()` - Generate + send personalized emails
  - `execute_schedule_meetings()` - Create Calendly links
  - `execute_full_outreach_workflow()` - Emails with meeting links
- Sends Slack notifications on completion

---

## AI-Driven Workflow Execution

Instead of just suggesting actions, AI **automatically executes** them:

```python
# User describes intent in natural language
user_intent = "Send consultation emails to all stakeholders"

# AI executor:
# 1. Parses intent
# 2. Chooses appropriate tool (SendEmails, ScheduleMeetings, FullOutreach)
# 3. Extracts parameters
# 4. Executes workflow
# 5. Returns results

result = ai_executor(user_intent)
# Result: {"emails_sent": 3, "recipients": [...]}
```

**How it works**:
1. LLM (Claude via Backboard) receives tool descriptions
2. Returns: `TOOL: SendEmails\nREASONING: ...\nPARAMETERS: {...}`
3. Parser extracts tool name + parameters
4. Executes matching workflow method
5. Returns execution results

---

## Project Structure

```
backend/
├── main.py                    # FastAPI server + endpoints
├── integrations/
│   ├── gmail_integration.py   # Email sending (OAuth2)
│   ├── calendly_integration.py # Meeting scheduling
│   └── slack_integration.py   # Team notifications
├── agents/
│   ├── specialized_agents.py  # Three specialized agents
│   ├── workflow_tools.py      # AI tool definitions + executor
│   ├── backboard_provider.py  # LLM provider wrapper
│   └── prompts_config.py      # Centralized prompt config
└── tests/
    └── test_workflows.py      # Comprehensive test suite

frontend/
├── app/
│   ├── page.tsx              # Main page
│   └── layout.tsx            # Layout
└── public/                   # Static assets
```

---

## Documentation Files

- **[SETUP.md](SETUP.md)** - API keys, installation, configuration, troubleshooting
- **[backend/README.md](backend/README.md)** - Backend architecture & agents
- **[backend/WORKFLOW_SETUP.md](backend/WORKFLOW_SETUP.md)** - Gmail/Calendly setup details
- **[backend/AI_WORKFLOW_GUIDE.md](backend/AI_WORKFLOW_GUIDE.md)** - AI execution guide
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Test suite documentation

---

## Key Files Modified for Workflows

| File | Changes |
|------|---------|
| `main.py` | 7 workflow endpoints added |
| `specialized_agents.py` | ProposalWorkflowAgent + Slack notifications |
| `workflow_tools.py` | AI-driven tool selection via Backboard |
| `slack_integration.py` | NEW - Team notifications |
| `test_workflows.py` | NEW - 50+ test cases |

---

## Next Steps

1. **Get API keys** → [SETUP.md](SETUP.md)
2. **Install dependencies** → `pip install -r requirements.txt`
3. **Configure .env** → Copy API keys
4. **Run tests** → `pytest backend/tests/test_workflows.py -v`
5. **Start server** → `python3 main.py`
6. **Test endpoints** → Use curl examples above

---

## Questions?

Check the docs:
- **Setup issues?** → [SETUP.md](SETUP.md)
- **API endpoints?** → [SETUP.md](SETUP.md#api-endpoints)
- **Test suite?** → [TESTING_GUIDE.md](TESTING_GUIDE.md)
- **Architecture?** → [backend/README.md](backend/README.md)
- **Workflows?** → [backend/AI_WORKFLOW_GUIDE.md](backend/AI_WORKFLOW_GUIDE.md)

**Last updated**: January 17, 2026
