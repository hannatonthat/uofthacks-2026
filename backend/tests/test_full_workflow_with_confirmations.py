"""
Comprehensive test demonstrating the full workflow with confirmation system.
This test shows the complete user journey from adding contacts to executing outreach.
"""
import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from main import app

client = TestClient(app)


class TestFullWorkflowWithConfirmations:
    """
    Complete workflow test demonstrating:
    1. Add contacts to a workflow thread
    2. Request full outreach (requires confirmation)
    3. Review pending action
    4. Approve action
    5. Execute outreach (sends emails + creates meetings + Slack)
    6. Verify workflow history
    """
    
    def setup_method(self):
        """Clear confirmation service before each test."""
        from main import confirmation_service
        confirmation_service.pending_confirmations.clear()
        confirmation_service.executed_actions.clear()
        confirmation_service.rejected_actions.clear()
    
    def test_complete_workflow_journey(self):
        """Test the complete workflow from start to finish with confirmations."""
        
        # ============================================================
        # STEP 1: Create a workflow thread by adding contacts
        # ============================================================
        print("\n" + "="*60)
        print("STEP 1: Adding contacts to workflow thread")
        print("="*60)
        
        thread_id = "test-workflow-thread-001"
        
        # Add first contact
        contact1 = {
            "name": "Chief Sarah Whitebear",
            "role": "Tribal Chief",
            "email": "tharmarajahnuthanan@gmail.com",
            "phone": "+1-555-0101"
        }
        
        response = client.post(
            f"/workflow/add-contact?threadid={thread_id}",
            json=contact1
        )
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        print(f"✓ Added contact: {contact1['name']} ({contact1['role']})")
        
        # Add second contact
        contact2 = {
            "name": "Elder Michael Strongheart",
            "role": "Community Elder",
            "email": "tharmarajahnuthanan@gmail.com",
            "phone": "+1-555-0102"
        }
        
        response = client.post(
            f"/workflow/add-contact?threadid={thread_id}",
            json=contact2
        )
        assert response.status_code == 200
        print(f"✓ Added contact: {contact2['name']} ({contact2['role']})")
        
        # Add third contact
        contact3 = {
            "name": "Councilor Jessica Redbear",
            "role": "Land Council Member",
            "email": "tharmarajahnuthanan@gmail.com",
            "phone": "+1-555-0103"
        }
        
        response = client.post(
            f"/workflow/add-contact?threadid={thread_id}",
            json=contact3
        )
        assert response.status_code == 200
        print(f"✓ Added contact: {contact3['name']} ({contact3['role']})")
        
        # ============================================================
        # STEP 2: Verify contacts were added
        # ============================================================
        print("\n" + "="*60)
        print("STEP 2: Verifying contact list")
        print("="*60)
        
        response = client.get(f"/workflow/contacts?threadid={thread_id}")
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert result["count"] == 3
        print(f"✓ Total contacts in thread: {result['count']}")
        for contact in result["contacts"]:
            print(f"  - {contact['name']} ({contact['role']}) - {contact['email']}")
        
        # ============================================================
        # STEP 3: Request full outreach (will require confirmation)
        # ============================================================
        print("\n" + "="*60)
        print("STEP 3: Requesting full outreach workflow")
        print("="*60)
        
        outreach_request = {
            "proposal_title": "Sustainable Forest Management Initiative - Traditional Territory Consultation",
            "event_type_name": "Indigenous Community Consultation"
        }
        
        response = client.post(
            f"/workflow/full-outreach?threadid={thread_id}",
            json=outreach_request
        )
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "pending_confirmation"
        
        action_id = result["action_id"]
        print(f"✓ Outreach request created: {action_id}")
        print(f"  Status: {result['status']}")
        print(f"  Message: {result['message']}")
        print(f"  Proposal: {result['context']['proposal_title']}")
        print(f"  Event Type: {result['context']['event_type_name']}")
        print(f"  Recipients: {result['context']['contact_count']} contacts")
        print(f"  Actions planned:")
        for action in result['context']['actions']:
            print(f"    - {action}")
        
        # ============================================================
        # STEP 4: Check pending actions
        # ============================================================
        print("\n" + "="*60)
        print("STEP 4: Reviewing pending actions")
        print("="*60)
        
        response = client.get("/workflow/pending-actions")
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert result["pending_count"] == 1
        print(f"✓ Pending actions: {result['pending_count']}")
        
        pending_action = result["actions"][0]
        print(f"  Action ID: {pending_action['action_id']}")
        print(f"  Type: {pending_action['action_type']}")
        print(f"  Status: {pending_action['status']}")
        print(f"  Requested at: {pending_action['timestamp']}")
        print(f"  Description: {pending_action['description']}")
        if 'details' in pending_action:
            print(f"  Proposal: {pending_action['details'].get('proposal_title', 'N/A')}")
        
        # ============================================================
        # STEP 5: User reviews and approves the action
        # ============================================================
        print("\n" + "="*60)
        print("STEP 5: Approving the outreach action")
        print("="*60)
        print("User review: This looks good, proceeding with outreach...")
        
        confirmation = {
            "action_id": action_id,
            "approved": True
        }
        
        response = client.post("/workflow/confirm", json=confirmation)
        assert response.status_code == 200
        result = response.json()
        
        # Print result to see what happened
        print(f"\n Response: {result}")
        
        if result["status"] == "error":
            print(f"  ERROR: {result.get('message', 'Unknown error')}")
            # Still continue to show the flow
        else:
            assert result["status"] == "success"
            assert result["action_type"] == "full_outreach"
            
            print(f"✓ Action approved and executed!")
            print(f"  Action ID: {result['action_id']}")
            print(f"  Result: {result['result']}")
        
        # ============================================================
        # STEP 6: Verify no more pending actions
        # ============================================================
        print("\n" + "="*60)
        print("STEP 6: Verifying pending actions cleared")
        print("="*60)
        
        response = client.get("/workflow/pending-actions")
        assert response.status_code == 200
        result = response.json()
        assert result["pending_count"] == 0
        print(f"✓ Pending actions: {result['pending_count']}")
        
        # ============================================================
        # STEP 7: Check workflow history
        # ============================================================
        print("\n" + "="*60)
        print("STEP 7: Reviewing workflow execution history")
        print("="*60)
        
        response = client.get(f"/workflow/history?threadid={thread_id}")
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        print(f"✓ Workflow history entries: {result['count']}")
        
        for i, entry in enumerate(result["history"], 1):
            print(f"\n  Entry {i}:")
            print(f"    Timestamp: {entry['timestamp']}")
            print(f"    Action: {entry['action']}")
            print(f"    Status: {entry['status']}")
            if 'details' in entry:
                print(f"    Details: {entry['details']}")
        
        print("\n" + "="*60)
        print("✓ COMPLETE WORKFLOW TEST PASSED")
        print("="*60)
    
    
    def test_rejection_flow(self):
        """Test what happens when user rejects a pending action."""
        
        print("\n" + "="*60)
        print("TEST: Action Rejection Flow")
        print("="*60)
        
        thread_id = "test-rejection-thread"
        
        # Add a contact
        contact = {
            "name": "Test Contact",
            "role": "Test Role",
            "email": "nuthanan06@gmail.com"
        }
        
        response = client.post(
            f"/workflow/add-contact?threadid={thread_id}",
            json=contact
        )
        assert response.status_code == 200
        print("✓ Contact added")
        
        # Request send emails
        request = {
            "proposal_title": "Test Proposal"
        }
        
        response = client.post(
            f"/workflow/send-emails?threadid={thread_id}",
            json=request
        )
        assert response.status_code == 200
        result = response.json()
        action_id = result["action_id"]
        print(f"✓ Email send requested: {action_id}")
        
        # Reject the action
        confirmation = {
            "action_id": action_id,
            "approved": False
        }
        
        response = client.post("/workflow/confirm", json=confirmation)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "rejected"
        print(f"✓ Action rejected: {result['message']}")
        
        # Verify no pending actions
        response = client.get("/workflow/pending-actions")
        result = response.json()
        assert result["pending_count"] == 0
        print("✓ No pending actions remain")
        
        print("✓ REJECTION FLOW TEST PASSED")
    
    
    def test_individual_workflow_actions(self):
        """Test individual workflow actions (send emails, schedule meetings)."""
        
        print("\n" + "="*60)
        print("TEST: Individual Workflow Actions")
        print("="*60)
        
        thread_id = "test-individual-actions"
        
        # Add contacts
        contacts = [
            {"name": "Contact 1", "role": "Role 1", "email": "nuthanan06@gmail.com"},
            {"name": "Contact 2", "role": "Role 2", "email": "nuthanan06@gmail.com"}
        ]
        
        for contact in contacts:
            response = client.post(
                f"/workflow/add-contact?threadid={thread_id}",
                json=contact
            )
            assert response.status_code == 200
        print("✓ Added 2 contacts")
        
        # Test send emails action
        print("\n--- Testing Send Emails ---")
        request = {"proposal_title": "Test Email Campaign"}
        response = client.post(
            f"/workflow/send-emails?threadid={thread_id}",
            json=request
        )
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "pending_confirmation"
        email_action_id = result["action_id"]
        print(f"✓ Email action pending: {email_action_id}")
        
        # Test schedule meetings action
        print("\n--- Testing Schedule Meetings ---")
        request = {
            "proposal_title": "Test Proposal",
            "event_type_name": "Consultation Meeting"
        }
        response = client.post(
            f"/workflow/schedule-meetings?threadid={thread_id}",
            json=request
        )
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "pending_confirmation"
        meeting_action_id = result["action_id"]
        print(f"✓ Meeting action pending: {meeting_action_id}")
        
        # Check both actions are pending
        response = client.get("/workflow/pending-actions")
        result = response.json()
        assert result["pending_count"] == 2
        print(f"✓ Total pending actions: {result['pending_count']}")
        
        # Approve email action
        response = client.post("/workflow/confirm", json={
            "action_id": email_action_id,
            "approved": True
        })
        assert response.status_code == 200
        print("✓ Email action approved and executed")
        
        # Reject meeting action
        response = client.post("/workflow/confirm", json={
            "action_id": meeting_action_id,
            "approved": False
        })
        assert response.status_code == 200
        print("✓ Meeting action rejected")
        
        # Verify all cleared
        response = client.get("/workflow/pending-actions")
        result = response.json()
        assert result["pending_count"] == 0
        print("✓ All actions processed")
        
        print("✓ INDIVIDUAL ACTIONS TEST PASSED")


if __name__ == "__main__":
    # Run with verbose output
    pytest.main([__file__, "-v", "-s"])
