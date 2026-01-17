# Confirmation Flow - Like GitHub Copilot

## 🎯 The New Flow (Exactly Like Copilot)

```
User's Action                          What Happens
═══════════════                        ═════════════════════════════════════════

1. HTTP Request                        Backend creates PENDING confirmation
   POST /execute-workflow/send-emails  
                                       ✓ Analyzes: 3 emails to send
                                       ✓ Creates action_id: "send_email_abc123"
                                       ✗ Does NOT send emails yet
   
   ↓ Returns immediately
   
   {
     "status": "pending_approval",
     "action_id": "send_email_abc123",
     "details": {
       "recipients": ["Chief Sarah", "Dr James", "Sue"],
       "count": 3
     }
   }

───────────────────────────────────────────────────────────────────

2. User Reviews                        Frontend shows confirmation UI
   "I'm about to send 3 emails to:     
    • Chief Sarah (chief@tribe.ca)     [Approve ✓]  [Reject ✗]
    • Dr James (dr@env.org)
    • Manager Sue (sue@company.ca)"

───────────────────────────────────────────────────────────────────

3a. User Clicks [Approve ✓]           Backend executes workflow
    POST /confirmations/abc123/approve
                                       ✓ Generates emails with AI
                                       ✓ Sends via Gmail API
                                       ✓ Notifies Slack
                                       ✓ Returns results
   
   {
     "status": "approved",
     "result": {
       "emails_sent": 3,
       "results": [...]
     }
   }

───────────────────────────────────────────────────────────────────

3b. OR User Clicks [Reject ✗]         Backend cancels workflow
    POST /confirmations/abc123/reject
                                       ✓ Marks as rejected
                                       ✗ Emails never sent
   
   {
     "status": "rejected",
     "message": "Action cancelled"
   }
```

---

## 🔄 Before vs After

### ❌ BEFORE (Immediate Execution - Dangerous!)

```bash
# User sends request
curl -X POST /execute-workflow/send-emails

# ⚠️ EMAILS SENT IMMEDIATELY - NO CONFIRMATION!
# Result: {"emails_sent": 3}
```

**Problem:** No chance to review or cancel!

---

### ✅ AFTER (Confirmation Required - Safe!)

```bash
# User sends request
curl -X POST /execute-workflow/send-emails
# Returns: {"status": "pending_approval", "action_id": "abc123"}

# ⏸️ NOTHING HAPPENS YET - WAITING FOR APPROVAL

# User reviews and approves
curl -X POST /confirmations/abc123/approve
# NOW emails actually get sent
# Result: {"status": "approved", "result": {"emails_sent": 3}}
```

**Benefit:** User has full control before any action executes!

---

## 💻 Complete Example

```bash
# Terminal 1: Start backend
cd backend
python3 main.py

# Terminal 2: Run workflow with confirmation
cd uofthacks-2026
./TEST_CONFIRMATION_FLOW.sh
```

**What you'll see:**

```
🚀 Testing Confirmation-Based Workflow
======================================

Step 1: Creating proposal thread...
✓ Thread created: abc-123-xyz

Step 2: Adding contacts...
✓ Added 3 contacts

Step 3: Requesting to send emails...
Response from workflow endpoint:
{
  "status": "pending_approval",
  "action_id": "send_email_abc123",
  "message": "Confirmation required before sending 3 emails",
  "details": {
    "count": 3,
    "recipients": ["Chief Sarah", "Dr. James", "Manager Sue"],
    "description": "Send outreach emails about Sustainable Forest Development"
  }
}

✓ Confirmation created: send_email_abc123
Status: PENDING (emails NOT sent yet)

======================================
⏸️  WAITING FOR USER APPROVAL
======================================

Details:
{
  "count": 3,
  "recipients": ["Chief Sarah", "Dr. James", "Manager Sue"],
  "description": "Send outreach emails about Sustainable Forest Development"
}

Do you want to approve and send these emails? (y/n): _
```

**If you press `y`:**
```
Step 6: Approving action...
✓ Action approved and executed!

Execution results:
{
  "status": "approved",
  "result": {
    "emails_sent": 3,
    "results": [...]
  }
}

✅ WORKFLOW COMPLETE - Emails sent!
```

**If you press `n`:**
```
Step 6: Rejecting action...
✓ Action rejected

{
  "status": "rejected",
  "reason": "User cancelled"
}

❌ WORKFLOW CANCELLED - No emails sent
```

---

## 🎨 Frontend Integration (Next Step)

```typescript
// Example React component
function ConfirmationPanel() {
  const [pending, setPending] = useState([]);
  
  useEffect(() => {
    // Poll for pending confirmations
    fetch('/confirmations/pending')
      .then(r => r.json())
      .then(data => setPending(data.pending));
  }, []);
  
  const handleApprove = async (actionId) => {
    const result = await fetch(`/confirmations/${actionId}/approve`, {
      method: 'POST'
    });
    const data = await result.json();
    alert(`✓ ${data.result.emails_sent} emails sent!`);
  };
  
  const handleReject = async (actionId) => {
    await fetch(`/confirmations/${actionId}/reject`, {
      method: 'POST'
    });
    alert('✗ Action cancelled');
  };
  
  return (
    <div>
      {pending.map(action => (
        <div key={action.action_id} className="confirmation-card">
          <h3>{action.description}</h3>
          <p>Recipients: {action.details.recipients.join(', ')}</p>
          <button onClick={() => handleApprove(action.action_id)}>
            ✓ Approve
          </button>
          <button onClick={() => handleReject(action.action_id)}>
            ✗ Reject
          </button>
        </div>
      ))}
    </div>
  );
}
```

---

## 📊 Key Points

✅ **All workflows now require confirmation** (send-emails, schedule-meetings, full-outreach)
✅ **Nothing executes until user approves** (safe by default)
✅ **User can review details** before committing
✅ **User can reject** to cancel action
✅ **Exactly like GitHub Copilot approval system**
✅ **Works via HTTP requests** (can be triggered by frontend, API, or CLI)

---

## 🧪 Test It Now

```bash
# Make sure backend is running
cd backend
python3 main.py

# In another terminal
cd uofthacks-2026
./TEST_CONFIRMATION_FLOW.sh
```

**It will:**
1. Create a thread
2. Add 3 contacts
3. Request to send emails → Creates pending confirmation
4. Ask YOU to approve or reject
5. Execute only if you approve

Try it! 🎉
