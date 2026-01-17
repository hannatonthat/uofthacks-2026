# API Keys & Confirmation System Summary

## 🔑 5 API Keys You Need

### 1. Backboard API Key (LLM)
```
BACKBOARD_API_KEY=your_key_here
```
- **Where**: https://backboard.io
- **What it does**: Powers AI (Claude/Gemini) for email generation, sustainability analysis
- **Required**: YES

### 2. Google API Key (Street View + Images)
```
GOOGLE_API_MAP_KEY=your_key_here
```
- **Where**: https://console.cloud.google.com/
- **What it does**: Street View panorama generation, image generation with Gemini
- **Setup**: Enable "Street View Static API" and "Gemini API"
- **Required**: YES

### 3. Calendly API Key (Scheduling)
```
CALENDLY_API_KEY=your_key_here
```
- **Where**: https://calendly.com/app/settings → Integrations → API & Webhooks
- **What it does**: Create meeting scheduling links
- **Required**: YES (for scheduling feature)

### 4. Gmail Credentials (OAuth2 for Email)
```
# Download JSON from Google Cloud Console
# Save as: backend/credentials.json
```
- **Where**: https://console.cloud.google.com/ → APIs & Services → Credentials
- **What it does**: Send outreach emails
- **Setup**: Create "Desktop App" OAuth2 credentials, download JSON
- **First run**: Opens browser for permission, auto-creates token.pickle
- **Required**: YES (for email feature)

### 5. Slack Webhook (Optional - Notifications)
```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```
- **Where**: https://api.slack.com/apps → Create App → Incoming Webhooks
- **What it does**: Send workflow completion notifications to Slack
- **Required**: NO (optional)

---

## ✅ Setup Checklist

```bash
# 1. Create .env file in backend/
cd backend
cat > .env << 'EOF'
BACKBOARD_API_KEY=your_backboard_key
GOOGLE_API_MAP_KEY=your_google_key
CALENDLY_API_KEY=your_calendly_key
SLACK_WEBHOOK_URL=your_slack_webhook  # Optional
EOF

# 2. Download Gmail credentials
# Go to Google Cloud Console → OAuth2 → Download JSON
# Save as: backend/credentials.json

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run server
python3 main.py
```

---

## 🔐 Confirmation System Overview

**Problem**: Actions (sending emails, scheduling meetings) happen instantly without user review.

**Solution**: Confirmation system that requires user approval before execution.

### How It Works

#### 1. User initiates action
```bash
POST /execute-workflow/send-emails
{
  "proposal_title": "Sustainable Development"
}

Response:
{
  "status": "pending_approval",
  "action_id": "send_email_abc123",
  "details": {
    "count": 3,
    "recipients": ["Chief Sarah", "Dr. James", "Manager Sue"],
    "description": "Send 3 consultation emails"
  }
}
```

#### 2. User reviews the details
- See who will receive emails
- Review email count/recipients
- Check meeting scheduling details

#### 3a. User approves
```bash
POST /confirmations/send_email_abc123/approve

Response:
{
  "status": "approved",
  "action_id": "send_email_abc123",
  "emails_sent": 3,
  "results": [...]
}
```

#### 3b. User rejects
```bash
POST /confirmations/send_email_abc123/reject
?reason=Need%20to%20edit%20emails

Response:
{
  "status": "rejected",
  "reason": "Need to edit emails",
  "action_id": "send_email_abc123"
}
```

#### 4. Check pending confirmations anytime
```bash
GET /confirmations/pending

Response:
{
  "pending_count": 2,
  "executed_count": 5,
  "rejected_count": 1,
  "pending": [
    {
      "action_id": "send_email_xyz",
      "action_type": "send_email",
      "description": "Send 3 emails",
      "details": {...}
    }
  ]
}
```

---

## 🛠️ Endpoints for Confirmation System

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/confirmations/pending` | View pending confirmations |
| POST | `/confirmations/{action_id}/approve` | Approve an action |
| POST | `/confirmations/{action_id}/reject` | Reject an action |

---

## 💡 Implementation Tips

### Tip 1: Return Early (Don't Execute Yet)
```python
# ❌ Old way (executes immediately):
result = agent.execute_send_emails(...)
return result

# ✅ New way (requests confirmation first):
confirmation = confirmation_service.create_confirmation(
    action_type=ActionType.SEND_EMAIL,
    description="Send 3 emails",
    details={...}
)
return {
    "status": "pending_approval",
    "action_id": confirmation.action_id,
    "details": confirmation.to_dict()
}
```

### Tip 2: Check Status Before Executing
```python
# When user approves, check if really approved:
if confirmation_service.is_confirmed(action_id):
    # NOW execute
    result = agent.execute_send_emails(...)
else:
    raise HTTPException(400, "Not approved")
```

### Tip 3: Multiple Actions at Once
```python
# Create multiple confirmations for complex workflows
email_req = confirmation_service.create_confirmation(...)
meeting_req = confirmation_service.create_confirmation(...)

return {
    "pending": [email_req.to_dict(), meeting_req.to_dict()]
}
```

### Tip 4: Clean Up Old Actions
```python
# Periodically clear old confirmations to save memory
confirmation_service.clear_old_actions()
```

---

## 🚀 Quick Examples

### Frontend: Show Pending Confirmation
```javascript
// Fetch pending confirmations
const response = await fetch('http://localhost:8000/confirmations/pending');
const data = await response.json();

// Show to user
data.pending.forEach(action => {
  console.log(`${action.description} (${action.action_id})`);
  console.log(`Recipients: ${action.details.recipients.join(', ')}`);
});
```

### Frontend: User Approves
```javascript
// User clicks approve button
const response = await fetch(
  `http://localhost:8000/confirmations/${actionId}/approve`,
  { method: 'POST' }
);

const result = await response.json();
console.log(`✓ ${result.emails_sent} emails sent!`);
```

### Backend: Add Confirmation to Any Endpoint
```python
@app.post("/execute-workflow/send-emails")
async def send_emails(proposal_title: str):
    # Create confirmation instead of executing
    req = confirmation_service.create_confirmation(
        action_type=ActionType.SEND_EMAIL,
        description=f"Send emails about {proposal_title}",
        details={"count": len(agent.get_contacts())}
    )
    
    return {
        "status": "pending_approval",
        "action_id": req.action_id,
        "details": req.to_dict()
    }
```

---

## ✨ What You Get

✅ **API Keys organized** in one place  
✅ **Confirmation system** to prevent accidental actions  
✅ **User review** before emails/meetings are sent  
✅ **Approval/rejection** endpoints  
✅ **Status checking** for pending actions  
✅ **Clean implementation** ready to integrate  

---

## 📋 Files Created

- `backend/agents/confirmation_service.py` - Confirmation system
- `backend/CONFIRMATION_EXAMPLES.md` - Usage examples
- Updated `backend/main.py` with endpoints

---

**Ready to go!** See [SETUP.md](SETUP.md) for complete installation.
