# AI-Driven Workflow Execution Guide

## Overview
The ProposalWorkflowAgent now includes **AI-driven workflow execution** - just tell the AI what you want in natural language, and it automatically decides which workflow to execute!

## How It Works

### Traditional Approach (Manual)
```bash
# You decide which endpoint to call
curl -X POST 'http://localhost:8000/execute-workflow/send-emails?threadid=...'
```

### AI-Driven Approach (Automatic) ✨
```bash
# AI decides which workflow to execute
curl -X POST 'http://localhost:8000/execute-workflow/ai-driven?threadid=...' \
  -d '{"user_intent":"Send emails to everyone about the proposal"}'

# AI automatically:
# 1. Understands intent → "send emails"
# 2. Chooses tool → SendEmails
# 3. Executes workflow → Emails sent!
# 4. Returns result → "✓ Sent 3 emails successfully"
```

---

## Setup

### 1. Install Dependencies

```bash
pip install langchain langchain-anthropic
```

### 2. Add API Key to .env

```bash
# Add to backend/.env
ANTHROPIC_API_KEY=sk-ant-api03-...
```

### 3. Restart Backend

```bash
python main.py
```

---

## Supported User Intents

The AI recognizes these natural language intents:

### **Send Emails**
- "Send emails to all tribal leaders"
- "Email everyone about the proposal"
- "Reach out to all contacts via email"
- "Send outreach emails to stakeholders"

→ **AI executes:** `SendEmails` tool

### **Schedule Meetings**
- "Set up consultation meetings"
- "Create scheduling links for everyone"
- "Schedule meetings with tribal leaders"
- "Generate Calendly links"

→ **AI executes:** `ScheduleMeetings` tool

### **Full Outreach**
- "Launch full outreach campaign"
- "Start the consultation process"
- "Initiate outreach with emails and scheduling"
- "Send emails with meeting links"

→ **AI executes:** `FullOutreach` tool

### **Add Contacts**
- "Add Chief Sarah (Tribal Leader, chief@tribe.ca) to contacts"
- "Include Dr. James as an environmental officer"
- "Add a new stakeholder: Maria (maria@example.com)"

→ **AI executes:** `AddContact` tool

### **View Contacts**
- "Show me all contacts"
- "Who's on the outreach list?"
- "List all tribal leaders we're contacting"

→ **AI executes:** `GetContacts` tool

### **Check Status**
- "What's the workflow status?"
- "Show me what's been done"
- "How many emails have we sent?"
- "What actions have been taken?"

→ **AI executes:** `GetWorkflowStatus` tool

---

## Example Workflows

### Example 1: Complete Outreach Campaign

```bash
# Create proposal workflow thread
THREAD_ID=$(curl -s -X POST http://localhost:8000/create-chat \
  -H "Content-Type: application/json" \
  -d '{"agent":"proposal"}' | jq -r '.thread_id')

# Add contacts via AI
curl -X POST "http://localhost:8000/execute-workflow/ai-driven?threadid=$THREAD_ID" \
  -H "Content-Type: application/json" \
  -d '{"user_intent":"Add Chief Sarah as Tribal Leader with email chief@tribe.ca"}'

curl -X POST "http://localhost:8000/execute-workflow/ai-driven?threadid=$THREAD_ID" \
  -H "Content-Type: application/json" \
  -d '{"user_intent":"Add Dr. James Martinez as Environmental Officer, email james@env.gov.bc.ca"}'

# Launch full outreach (AI decides to use FullOutreach tool)
curl -X POST "http://localhost:8000/execute-workflow/ai-driven?threadid=$THREAD_ID" \
  -H "Content-Type: application/json" \
  -d '{"user_intent":"Launch full outreach campaign for Sustainable Urban Development proposal with consultation meetings"}'

# Check status
curl -X POST "http://localhost:8000/execute-workflow/ai-driven?threadid=$THREAD_ID" \
  -H "Content-Type: application/json" \
  -d '{"user_intent":"What have we done so far?"}'
```

**Response:**
```json
{
  "status": "success",
  "user_intent": "What have we done so far?",
  "ai_response": "Workflow Progress: Step 0/10\n\nRecent Actions:\n  - scheduling_link_created: Chief Sarah\n  - email_sent: Chief Sarah\n  - scheduling_link_created: Dr. James Martinez\n  - email_sent: Dr. James Martinez",
  "workflow_history": [...]
}
```

### Example 2: Progressive Workflow

```bash
# Step 1: Check contacts
curl -X POST "http://localhost:8000/execute-workflow/ai-driven?threadid=$THREAD_ID" \
  -d '{"user_intent":"Show me everyone on the contact list"}'

# Response: "Total contacts: 2\n1. Chief Sarah (Tribal Leader) - chief@tribe.ca\n2. Dr. James (Environmental Officer) - james@env.gov.bc.ca"

# Step 2: Just schedule meetings (no emails yet)
curl -X POST "http://localhost:8000/execute-workflow/ai-driven?threadid=$THREAD_ID" \
  -d '{"user_intent":"Create Calendly scheduling links for Indigenous Consultation meetings"}'

# Response: "✓ Created 2 scheduling links for Indigenous Consultation"

# Step 3: Send emails with those links
curl -X POST "http://localhost:8000/execute-workflow/ai-driven?threadid=$THREAD_ID" \
  -d '{"user_intent":"Send emails to everyone about the Sustainable Development proposal"}'

# Response: "✓ Sent 2 emails successfully. 0 errors."
```

---

## AI Decision Process

### How AI Chooses the Right Tool

**User says:** "I need to email all the tribal leaders about our sustainable development proposal"

**AI thinks:**
```
1. Parse intent: User wants to send emails
2. Check available tools:
   - SendEmails: ✓ (matches "email" keyword)
   - ScheduleMeetings: ✗ (not about scheduling)
   - FullOutreach: ✗ (user only mentioned email, not full campaign)
3. Choose: SendEmails tool
4. Extract parameters: proposal_title = "sustainable development proposal"
5. Execute: SendEmails(proposal_title="sustainable development proposal")
```

**AI responds:** "✓ Sent 2 emails successfully"

### Complex Intent Resolution

**User says:** "Set up consultations with indigenous leaders - send them emails with booking links"

**AI thinks:**
```
1. Parse intent: User wants both emails AND scheduling
2. Keywords detected: "emails", "booking links", "consultations"
3. Match: FullOutreach tool (combines both)
4. Execute: FullOutreach(proposal_title="...", event_type_name="...")
```

**AI responds:** "✓ Full outreach complete! Sent 2 emails with 2 scheduling links."

---

## Advanced: Chaining Multiple Actions

The AI can execute multiple actions in sequence:

```bash
curl -X POST "http://localhost:8000/execute-workflow/ai-driven?threadid=$THREAD_ID" \
  -d '{"user_intent":"Add Chief Sarah (chief@tribe.ca) and Dr. James (james@env.gov.bc.ca) to contacts, then send them both emails about the Sustainable Development proposal"}'
```

**AI executes:**
1. `AddContact(name="Chief Sarah", email="chief@tribe.ca", ...)`
2. `AddContact(name="Dr. James", email="james@env.gov.bc.ca", ...)`
3. `SendEmails(proposal_title="Sustainable Development proposal")`

**Response:** "✓ Added 2 contacts and sent 2 emails successfully"

---

## Error Handling

### Missing Contacts
```bash
curl -X POST "http://localhost:8000/execute-workflow/ai-driven?threadid=$THREAD_ID" \
  -d '{"user_intent":"Send emails to everyone"}'
```

**Response:**
```json
{
  "status": "error",
  "error": "No contacts available. Add contacts first via add_contact()."
}
```

### API Not Configured
```bash
# If Gmail not set up
curl -X POST "http://localhost:8000/execute-workflow/ai-driven?threadid=$THREAD_ID" \
  -d '{"user_intent":"Send emails about the proposal"}'
```

**Response:**
```json
{
  "status": "error",
  "error": "Gmail integration not available. Check credentials.json setup."
}
```

---

## Comparison: Manual vs AI-Driven

### Manual Workflow Execution
```bash
# You specify exact endpoint and parameters
curl -X POST 'http://localhost:8000/execute-workflow/send-emails?threadid=...' \
  -d '{"proposal_title":"Sustainable Development","event_type_name":"Consultation"}'
```

**Pros:**
- ✅ Precise control
- ✅ No AI API cost
- ✅ Predictable behavior

**Cons:**
- ❌ Need to know exact endpoint names
- ❌ Must structure JSON correctly
- ❌ Less flexible

### AI-Driven Workflow Execution
```bash
# You describe intent in natural language
curl -X POST 'http://localhost:8000/execute-workflow/ai-driven?threadid=...' \
  -d '{"user_intent":"Send consultation emails to tribal leaders"}'
```

**Pros:**
- ✅ Natural language interface
- ✅ AI chooses right tool automatically
- ✅ More flexible and intuitive
- ✅ Can handle complex multi-step intents

**Cons:**
- ❌ Requires ANTHROPIC_API_KEY
- ❌ Small API cost per request (~$0.001)
- ❌ Slightly less predictable (AI interpretation)

---

## Cool Workflow Ideas to Add

### 1. Document Generation
```python
Tool(
    name="GenerateProposalPDF",
    description="Generate PDF proposal document with indigenous perspectives"
)
```

**User intent:** "Create a PDF of the proposal"

### 2. Slack Notifications
```python
Tool(
    name="SendSlackNotification",
    description="Send notification to team Slack channel about workflow progress"
)
```

**User intent:** "Notify the team that consultations have been booked"

### 3. Follow-up Automation
```python
Tool(
    name="ScheduleFollowUp",
    description="Schedule automated follow-up email if no response after 7 days"
)
```

**User intent:** "Send reminders to anyone who hasn't responded in a week"

### 4. Meeting Transcription
```python
Tool(
    name="TranscribeMeeting",
    description="Transcribe Calendly meeting recording and summarize key points"
)
```

**User intent:** "Summarize the consultation meeting with Chief Sarah"

### 5. Territory Lookup
```python
Tool(
    name="LookupTerritory",
    description="Identify which indigenous territories a project is located on"
)
```

**User intent:** "Which indigenous territories is this project on?"

---

## Frontend Integration Example

```typescript
// In your Next.js frontend
async function executeWorkflow(threadId: string, userIntent: string) {
  const response = await fetch(
    `http://localhost:8000/execute-workflow/ai-driven?threadid=${threadId}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_intent: userIntent })
    }
  );
  
  const result = await response.json();
  return result.ai_response; // "✓ Sent 3 emails successfully"
}

// User interface
<button onClick={() => executeWorkflow(threadId, "Send emails to everyone")}>
  Launch Outreach
</button>

// Or chat interface
<input 
  placeholder="What workflow do you want to execute?" 
  onSubmit={(value) => executeWorkflow(threadId, value)}
/>
```

---

## Security & Best Practices

### Rate Limiting
- Implement rate limits on AI-driven endpoint (users could spam expensive LLM calls)
- Consider caching common intents

### User Permissions
- Verify user has permission to execute workflows
- Log all workflow executions for audit trail

### Intent Validation
- AI validates contacts exist before sending emails
- AI checks required integrations (Gmail, Calendly) are configured
- AI provides clear error messages if workflow can't be executed

### Cost Management
- Each AI-driven request costs ~$0.001-0.005 (Claude API)
- Consider showing cost estimate before execution
- Batch similar requests to reduce API calls

---

## Troubleshooting

### "AI workflow tools not available"
```bash
pip install langchain langchain-anthropic
```

### "ANTHROPIC_API_KEY not found"
Add to `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
```

### AI chooses wrong tool
Add more context to user intent:
```bash
# Ambiguous
{"user_intent": "Contact everyone"}

# Clear
{"user_intent": "Send emails with meeting scheduling links to all contacts"}
```

### Workflow fails mid-execution
Check workflow history to see what completed:
```bash
curl 'http://localhost:8000/workflow/history?threadid=THREAD_ID'
```

---

## Next Steps

1. **Test AI-driven workflows** with example intents
2. **Add custom tools** for your specific needs (document generation, Slack, etc.)
3. **Build frontend UI** with natural language workflow input
4. **Monitor costs** and optimize LLM calls
5. **Add webhook listeners** for real-time updates (Calendly bookings, email opens)

The AI will learn from usage patterns and get better at understanding your specific workflow intents!
