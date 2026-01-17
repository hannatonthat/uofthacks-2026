# How to Try AI-Driven Workflows

## 🎯 The Flow

```
1. User message: "I want to reach out to tribal leaders about sustainable forestry"
           ↓
2. AI analyzes: "They want to send emails"
           ↓
3. AI creates confirmation: "About to send 3 emails to: Chief Sarah, Dr. James, Manager Sue"
           ↓
4. User approves via API call
           ↓
5. Emails actually get sent + Slack notification
```

---

## ⚡ Quick Start (5 minutes)

### Step 1: Add API Keys to `.env`
```bash
cd backend
cat > .env << 'EOF'
BACKBOARD_API_KEY=your_backboard_key_here
GOOGLE_API_MAP_KEY=your_google_key_here
CALENDLY_API_KEY=your_calendly_key_here
SLACK_WEBHOOK_URL=your_slack_webhook_here
EOF
```

### Step 2: Start Backend
```bash
cd backend
python3 main.py
```

### Step 3: Create a Thread (in another terminal)
```bash
curl -X POST 'http://localhost:8000/chat/start' \
  -H "Content-Type: application/json" \
  -d '{"agent":"proposal"}' | jq
```

Response:
```json
{
  "thread_id": "abc123xyz",
  "agent": "proposal",
  "message": "I'm ready to help coordinate outreach..."
}
```

### Step 4: Send Initial Context
```bash
THREAD_ID="abc123xyz"

curl -X POST "http://localhost:8000/chat?threadid=$THREAD_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "agent": "proposal",
    "message": "We have 3 tribal leaders to contact about sustainable forestry: Chief Sarah (chief@tribe.ca), Dr. James (dr@env.org), Manager Sue (sue@company.ca)"
  }' | jq
```

### Step 5: Add Contacts (Optional but Recommended)
```bash
THREAD_ID="abc123xyz"

# Add contact 1
curl -X POST "http://localhost:8000/workflow/add-contact?threadid=$THREAD_ID&name=Chief%20Sarah&role=Tribal%20Leader&email=chief@tribe.ca&phone=250-555-1234"

# Add contact 2
curl -X POST "http://localhost:8000/workflow/add-contact?threadid=$THREAD_ID&name=Dr%20James&role=Environmental%20Scientist&email=dr@env.org&phone=604-555-5678"

# Add contact 3
curl -X POST "http://localhost:8000/workflow/add-contact?threadid=$THREAD_ID&name=Manager%20Sue&role=Project%20Manager&email=sue@company.ca&phone=778-555-9999"
```

### Step 6: Request AI-Driven Workflow
```bash
THREAD_ID="abc123xyz"

curl -X POST "http://localhost:8000/execute-workflow/ai-driven?threadid=$THREAD_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "user_intent": "Send professional emails to all tribal leaders about our sustainable forestry proposal"
  }' | jq
```

Response (creates pending confirmation):
```json
{
  "status": "pending_approval",
  "action_id": "send_email_xyz789",
  "details": {
    "count": 3,
    "recipients": ["Chief Sarah", "Dr. James", "Manager Sue"],
    "description": "Send outreach emails about sustainable forestry proposal",
    "action_type": "send_email"
  }
}
```

### Step 7: User Reviews & Approves
```bash
ACTION_ID="send_email_xyz789"

# See what's pending
curl http://localhost:8000/confirmations/pending | jq

# Approve it
curl -X POST "http://localhost:8000/confirmations/$ACTION_ID/approve" | jq
```

Response:
```json
{
  "status": "approved",
  "action_id": "send_email_xyz789",
  "emails_sent": 3,
  "recipients": ["chief@tribe.ca", "dr@env.org", "sue@company.ca"],
  "results": [...]
}
```

---

## 🧪 Test Scenarios

### Scenario 1: Send Emails
```bash
# Prerequisites: Create thread, add 2-3 contacts

curl -X POST "http://localhost:8000/execute-workflow/ai-driven?threadid=$THREAD_ID" \
  -H "Content-Type: application/json" \
  -d '{"user_intent": "Send emails proposing a meeting about land sustainability"}'
```

**What happens:**
- ✓ AI recognizes "send emails" intent
- ✓ Creates confirmation with email preview
- ✓ Waits for user approval
- ✓ On approval: sends emails, notifies Slack, returns results

---

### Scenario 2: Schedule Meetings
```bash
curl -X POST "http://localhost:8000/execute-workflow/ai-driven?threadid=$THREAD_ID" \
  -H "Content-Type: application/json" \
  -d '{"user_intent": "Set up 30-minute consultation meetings with the team for next week"}'
```

**What happens:**
- ✓ AI recognizes "schedule meetings" intent
- ✓ Creates confirmation with Calendly links preview
- ✓ Waits for approval
- ✓ On approval: generates Calendly links, notifies Slack

---

### Scenario 3: Full Outreach Campaign
```bash
curl -X POST "http://localhost:8000/execute-workflow/ai-driven?threadid=$THREAD_ID" \
  -H "Content-Type: application/json" \
  -d '{"user_intent": "Launch full outreach: send emails with meeting links and notify the team on Slack"}'
```

**What happens:**
- ✓ AI recognizes "full outreach" intent
- ✓ Creates ONE confirmation for entire campaign
- ✓ On approval: sends emails + scheduling links + Slack notification all at once

---

### Scenario 4: Add Contact
```bash
curl -X POST "http://localhost:8000/execute-workflow/ai-driven?threadid=$THREAD_ID" \
  -H "Content-Type: application/json" \
  -d '{"user_intent": "Add a new contact: Patricia Nelson, Environmental Coordinator, patricia@env.ca, 604-555-4321"}'
```

**What happens:**
- ✓ AI recognizes "add contact" intent
- ✓ Parses contact details
- ✓ Adds to thread's contact list
- ✓ Returns confirmation

---

## 🔧 Troubleshooting

### Issue: "Thread not found"
```bash
# Make sure you created a thread first
curl -X POST 'http://localhost:8000/chat/start' \
  -H "Content-Type: application/json" \
  -d '{"agent":"proposal"}'
```

### Issue: "Import error - AI workflow tools not available"
```bash
# The workflow_tools module doesn't exist yet
# For now, use /execute-workflow/send-emails, /schedule-meetings directly
```

### Issue: "No contacts in thread"
```bash
# Add contacts before sending emails
curl -X POST "http://localhost:8000/workflow/add-contact?threadid=$THREAD_ID&name=Name&role=Role&email=email@test.com"
```

### Issue: API keys not working
```bash
# Check .env file has all 4 keys
# Make sure backend restarted after adding .env
# Test each key manually first
```

---

## 📋 Full Example Script

Save as `test_workflow.sh`:

```bash
#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}1. Creating thread...${NC}"
THREAD_ID=$(curl -s -X POST 'http://localhost:8000/chat/start' \
  -H "Content-Type: application/json" \
  -d '{"agent":"proposal"}' | jq -r '.thread_id')

echo -e "${GREEN}Thread ID: $THREAD_ID${NC}"

echo -e "${BLUE}2. Adding contacts...${NC}"
curl -s -X POST "http://localhost:8000/workflow/add-contact?threadid=$THREAD_ID&name=Chief%20Sarah&role=Tribal%20Leader&email=test1@example.com"
curl -s -X POST "http://localhost:8000/workflow/add-contact?threadid=$THREAD_ID&name=Dr%20James&role=Scientist&email=test2@example.com"

echo -e "${GREEN}Contacts added${NC}"

echo -e "${BLUE}3. Requesting AI workflow (send emails)...${NC}"
RESPONSE=$(curl -s -X POST "http://localhost:8000/execute-workflow/ai-driven?threadid=$THREAD_ID" \
  -H "Content-Type: application/json" \
  -d '{"user_intent": "Send professional emails about sustainable development"}')

echo -e "${GREEN}Response:${NC}"
echo "$RESPONSE" | jq

# Extract action_id if pending
ACTION_ID=$(echo "$RESPONSE" | jq -r '.action_id // empty')

if [ -n "$ACTION_ID" ]; then
  echo -e "${BLUE}4. Checking pending confirmations...${NC}"
  curl -s http://localhost:8000/confirmations/pending | jq
  
  echo -e "${BLUE}5. Approving action ($ACTION_ID)...${NC}"
  curl -s -X POST "http://localhost:8000/confirmations/$ACTION_ID/approve" | jq
fi
```

Run it:
```bash
chmod +x test_workflow.sh
./test_workflow.sh
```

---

## 🚀 What's Actually Happening Inside

### Backend Flow:
1. User sends intent → `execute_ai_driven_workflow()` endpoint
2. Endpoint checks if thread exists
3. Extracts ProposalWorkflowAgent from thread
4. Calls `create_workflow_agent(agent)` → Creates AI decision-maker
5. AI analyzes intent and decides:
   - "send_emails" → calls `agent.execute_send_emails()`
   - "schedule_meetings" → calls `agent.execute_schedule_meetings()`
   - "full_outreach" → calls `agent.execute_full_outreach_workflow()`
   - "add_contact" → calls `agent.add_contact()`

### ProposalWorkflowAgent Methods:
```python
# These are what the AI can call:
agent.execute_send_emails()           # Sends emails to all contacts
agent.execute_schedule_meetings()     # Creates Calendly links
agent.execute_full_outreach_workflow() # Both + Slack notification
agent.add_contact()                   # Adds person to contact list
agent.get_contacts()                  # Lists all contacts
agent.get_workflow_history()          # Shows past actions
```

### Confirmation System:
```python
# When an action is about to execute:
confirmation_service.create_confirmation(
    action_type=ActionType.SEND_EMAIL,
    description="Send 3 emails",
    details={...}
)
# Returns: action_id (user must approve before execution)
```

---

## 📊 Current Implementation Status

✅ **Done:**
- ProposalWorkflowAgent (can send emails, schedule meetings, notify Slack)
- ConfirmationService (prevents accidental actions)
- API endpoints (/chat/start, /chat, /execute-workflow/*, /confirmations/*)
- Contact management (/workflow/add-contact)

⏳ **Needs Integration:**
- AI decision-maker (workflow_tools.py module) - determines which action to take
- Frontend UI - shows pending confirmations with approve/reject buttons
- Database persistence - currently confirmations clear on restart

---

## 💡 Next Steps (Optional Enhancements)

1. **Create workflow_tools.py module** - AI decision-maker for intent recognition
2. **Frontend page** - Show pending confirmations, approve/reject buttons
3. **Persistent storage** - Save confirmations to database
4. **Webhook handling** - Listen for Gmail replies, Calendly responses
5. **Analytics** - Track which workflows succeed/fail, email open rates

---

**Ready to go!** Start the backend and run test_workflow.sh
