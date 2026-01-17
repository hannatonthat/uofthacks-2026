# Quick Reference Card

## 🚀 Get Started (5 minutes)

### API Keys You Need
```bash
BACKBOARD_API_KEY=...           # backboard.io
GOOGLE_API_MAP_KEY=...          # Google Cloud Console
CALENDLY_API_KEY=...            # calendly.com/settings
SLACK_WEBHOOK_URL=...           # api.slack.com (optional)
credentials.json                 # Gmail OAuth2 (Google Cloud Console)
```

### Install
```bash
cd backend
pip install -r requirements.txt
echo 'BACKBOARD_API_KEY=...' >> .env
echo 'GOOGLE_API_MAP_KEY=...' >> .env
echo 'CALENDLY_API_KEY=...' >> .env
python3 main.py
```

---

## 📡 Core Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/generate-panorama` | POST | Create 360° Street View image |
| `/create-sustainability-chat` | POST | Analyze land + get redesigns |
| `/workflow/add-contact` | POST | Add stakeholder to list |
| `/execute-workflow/ai-driven` | POST | Send emails (natural language) |
| `/execute-workflow/schedule-meetings` | POST | Create Calendly links |
| `/workflow/contacts` | GET | View all contacts |
| `/workflow/history` | GET | View workflow audit trail |

---

## 🧪 Testing

```bash
pytest backend/tests/test_workflows.py -v          # All tests
pytest backend/tests/test_workflows.py -m unit     # Unit only
pytest --cov=backend --cov-report=html             # Coverage
```

---

## 📝 Workflow Examples

### Send Emails (AI chooses everything)
```bash
curl -X POST http://localhost:8000/execute-workflow/ai-driven \
  -d '{"user_intent": "Send consultation emails to all stakeholders"}' \
  -H "Content-Type: application/json"
```

### Add Contact + Schedule Meetings
```bash
# Add contact
curl -X POST http://localhost:8000/workflow/add-contact \
  -d '{"name":"Chief Sarah","email":"chief@tribe.ca","role":"Leader"}' \
  -H "Content-Type: application/json"

# Schedule meetings
curl -X POST http://localhost:8000/execute-workflow/schedule-meetings
```

---

## 🔧 Troubleshooting

| Issue | Fix |
|-------|-----|
| `BACKBOARD_API_KEY not found` | Add to `.env` in `backend/` |
| Gmail auth fails | Delete `backend/token.pickle`, run again |
| Port 8000 in use | `lsof -ti:8000 \| xargs kill -9` |
| Import errors | Run `pip install -r requirements.txt` |

---

## 📚 Full Docs

- **[SETUP.md](SETUP.md)** - Complete setup & API keys
- **[README.md](README.md)** - Project overview
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Test documentation
- **[backend/README.md](backend/README.md)** - Architecture

---

## 🎯 What You Built

✅ Panorama generation from Street View  
✅ AI sustainability analysis + future-vision images  
✅ Gmail + Calendly workflow automation  
✅ Slack team notifications  
✅ AI-driven tool selection (natural language → execution)  
✅ 50+ test cases covering all workflows  
✅ Backboard API integration for unified LLM access  

**That's it!** See [SETUP.md](SETUP.md) for full configuration.
