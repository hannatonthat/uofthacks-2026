"""Example: Using the Confirmation System"""

# Example 1: Before sending emails, request confirmation
# ========================================================

# In your endpoint, instead of immediately sending:

async def send_emails_with_confirmation(proposal_title: str):
    """Send emails but request user confirmation first."""
    
    # Step 1: Prepare the action (don't execute yet)
    contacts = agent.get_contacts()
    
    # Step 2: Create a confirmation request
    confirmation_req = confirmation_service.create_confirmation(
        action_type=ActionType.SEND_EMAIL,
        description=f"Send {len(contacts)} consultation emails about '{proposal_title}'",
        details={
            "count": len(contacts),
            "recipients": [c["name"] for c in contacts],
            "emails": [c["email"] for c in contacts],
            "proposal_title": proposal_title
        }
    )
    
    # Step 3: Return action_id to user (don't execute yet!)
    return {
        "status": "pending_approval",
        "action_id": confirmation_req.action_id,
        "message": f"Ready to send {len(contacts)} emails",
        "details": confirmation_req.to_dict()
    }


# User sees this:
# {
#   "status": "pending_approval",
#   "action_id": "send_email_abc123",
#   "message": "Ready to send 3 emails",
#   "details": {
#     "count": 3,
#     "recipients": ["Chief Sarah", "Dr. James", "Manager Sue"],
#     "emails": ["chief@tribe.ca", "james@env.ca", "sue@gov.ca"],
#     "proposal_title": "Sustainable Land Development"
#   }
# }
#
# User reviews and either approves or rejects


# Example 2: User approves the action
# ====================================

async def handle_approval(action_id: str):
    """Execute the action after user approves."""
    
    # Step 1: Check if user approved
    if not confirmation_service.is_confirmed(action_id):
        raise HTTPException(status_code=400, detail="Action not approved")
    
    # Step 2: NOW execute the email sending
    confirmation_req = confirmation_service.get_confirmation(action_id)
    result = agent.execute_send_emails(
        proposal_title=confirmation_req.details["proposal_title"]
    )
    
    # Step 3: Return execution results
    return {
        "status": "executed",
        "action_id": action_id,
        "emails_sent": result["sent_count"],
        "results": result["results"],
        "errors": result["errors"]
    }


# User sees:
# {
#   "status": "executed",
#   "action_id": "send_email_abc123",
#   "emails_sent": 3,
#   "results": [
#     {"recipient": "Chief Sarah", "status": "sent"},
#     {"recipient": "Dr. James", "status": "sent"},
#     {"recipient": "Manager Sue", "status": "sent"}
#   ]
# }


# Example 3: API Flow in Practice
# ================================

"""
Step 1: User initiates action
  POST /execute-workflow/send-emails
  {
    "proposal_title": "Sustainable Land Development"
  }
  
  Response:
  {
    "status": "pending_approval",
    "action_id": "send_email_abc123",
    "details": {...}
  }

Step 2: User reviews and chooses
  
  Option A - User approves:
    POST /confirmations/send_email_abc123/approve
    
    Response: {"status": "approved", "action_id": "send_email_abc123"}
  
  Option B - User rejects:
    POST /confirmations/send_email_abc123/reject?reason=Need to edit emails first
    
    Response: {"status": "rejected", "reason": "Need to edit emails first"}

Step 3: Check pending confirmations anytime
  GET /confirmations/pending
  
  Response:
  {
    "pending_count": 1,
    "executed_count": 5,
    "rejected_count": 2,
    "pending": [...]
  }
"""


# Example 4: Multiple Confirmations at Once
# ==========================================

async def full_outreach_with_confirmation():
    """Show user both email sending and meeting scheduling."""
    
    confirmations = []
    
    # Create confirmation for emails
    email_req = confirmation_service.create_confirmation(
        action_type=ActionType.SEND_EMAIL,
        description="Send 3 consultation emails",
        details={"count": 3, "recipients": [...]}
    )
    confirmations.append(email_req.to_dict())
    
    # Create confirmation for meetings
    meeting_req = confirmation_service.create_confirmation(
        action_type=ActionType.SCHEDULE_MEETING,
        description="Create 3 Calendly scheduling links",
        details={"count": 3, "event_type": "Consultation Meeting"}
    )
    confirmations.append(meeting_req.to_dict())
    
    return {
        "status": "pending_approval",
        "confirmations": confirmations,
        "message": "Review and approve both actions"
    }


# User sees both pending actions and approves them separately or together


# Example 5: Quick Implementation Checklist
# ==========================================

"""
To add confirmation to your endpoints:

1. Import at top:
   from agents.confirmation_service import ConfirmationService, ActionType
   confirmation_service = ConfirmationService()

2. In your endpoint, create confirmation instead of executing:
   confirmation_req = confirmation_service.create_confirmation(
       action_type=ActionType.SEND_EMAIL,
       description="Send X emails to Y recipients",
       details={...}
   )
   return {"status": "pending_approval", "action_id": confirmation_req.action_id}

3. In approval handler, check confirmation then execute:
   if confirmation_service.is_confirmed(action_id):
       result = agent.execute_send_emails(...)
       return result
   else:
       raise HTTPException(400, "Not approved")

4. Frontend shows:
   - Pending actions
   - Approve/Reject buttons
   - Execution results after approval
"""
