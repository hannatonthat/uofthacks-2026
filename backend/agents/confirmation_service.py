"""User confirmation system for workflow actions."""

from typing import Dict, List, Any
from enum import Enum


class ActionType(Enum):
    """Types of actions requiring confirmation."""
    SEND_EMAIL = "send_email"
    SCHEDULE_MEETING = "schedule_meeting"
    FULL_OUTREACH = "full_outreach"
    DELETE_CONTACT = "delete_contact"


class ConfirmationRequest:
    """Represents a pending action awaiting user confirmation."""
    
    def __init__(
        self,
        action_type: ActionType,
        action_id: str,
        description: str,
        details: Dict[str, Any],
        requires_confirmation: bool = True
    ):
        self.action_type = action_type
        self.action_id = action_id
        self.description = description
        self.details = details
        self.requires_confirmation = requires_confirmation
        self.confirmed = False
        self.rejected = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "description": self.description,
            "details": self.details,
            "confirmed": self.confirmed,
            "rejected": self.rejected,
            "requires_confirmation": self.requires_confirmation
        }


class ConfirmationService:
    """Manages pending confirmations and action execution."""
    
    def __init__(self):
        """Initialize confirmation service."""
        self.pending_confirmations: Dict[str, ConfirmationRequest] = {}
        self.executed_actions: List[str] = []
        self.rejected_actions: List[str] = []
    
    def create_confirmation(
        self,
        action_type: ActionType,
        description: str,
        details: Dict[str, Any],
        action_id: str = None,
        requires_confirmation: bool = True
    ) -> ConfirmationRequest:
        """
        Create a pending confirmation request.
        
        PARAMETERS:
          action_type: Type of action (send_email, schedule_meeting, etc)
          description: Human-readable description of action
          details: Action details (recipients, meeting info, etc)
          action_id: Optional custom ID (auto-generated if not provided)
          requires_confirmation: Whether confirmation is required
        
        RETURNS:
          ConfirmationRequest object
        
        EXAMPLE:
          req = service.create_confirmation(
              action_type=ActionType.SEND_EMAIL,
              description="Send 3 consultation emails to tribal leaders",
              details={
                  "recipients": ["chief@tribe.ca", "james@env.ca"],
                  "subject": "Consultation Request",
                  "count": 3
              }
          )
        """
        import uuid
        
        if action_id is None:
            action_id = f"{action_type.value}_{uuid.uuid4().hex[:8]}"
        
        req = ConfirmationRequest(
            action_type=action_type,
            action_id=action_id,
            description=description,
            details=details,
            requires_confirmation=requires_confirmation
        )
        
        self.pending_confirmations[action_id] = req
        return req
    
    def approve_action(self, action_id: str) -> bool:
        """
        User approves an action.
        
        PARAMETERS:
          action_id: ID of the confirmation request
        
        RETURNS:
          True if approved, False if not found
        
        EXAMPLE:
          if service.approve_action(action_id):
              # Execute the action
              pass
        """
        if action_id not in self.pending_confirmations:
            return False
        
        self.pending_confirmations[action_id].confirmed = True
        self.executed_actions.append(action_id)
        return True
    
    def reject_action(self, action_id: str) -> bool:
        """
        User rejects an action.
        
        PARAMETERS:
          action_id: ID of the confirmation request
        
        RETURNS:
          True if rejected, False if not found
        """
        if action_id not in self.pending_confirmations:
            return False
        
        self.pending_confirmations[action_id].rejected = True
        self.rejected_actions.append(action_id)
        return True
    
    def get_pending(self) -> List[Dict[str, Any]]:
        """
        Get all pending confirmations.
        
        RETURNS:
          List of pending confirmation requests as dicts
        
        EXAMPLE:
          pending = service.get_pending()
          for req in pending:
              print(f"{req['action_id']}: {req['description']}")
        """
        return [
            req.to_dict()
            for req in self.pending_confirmations.values()
            if not req.confirmed and not req.rejected
        ]
    
    def is_confirmed(self, action_id: str) -> bool:
        """Check if action has been confirmed."""
        if action_id not in self.pending_confirmations:
            return False
        return self.pending_confirmations[action_id].confirmed
    
    def is_rejected(self, action_id: str) -> bool:
        """Check if action has been rejected."""
        if action_id not in self.pending_confirmations:
            return False
        return self.pending_confirmations[action_id].rejected
    
    def get_confirmation(self, action_id: str) -> ConfirmationRequest:
        """Get confirmation request by ID."""
        return self.pending_confirmations.get(action_id)
    
    def clear_old_actions(self):
        """Clear executed and rejected actions from memory."""
        self.pending_confirmations = {
            k: v for k, v in self.pending_confirmations.items()
            if not v.confirmed and not v.rejected
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of confirmations."""
        return {
            "pending_count": len(self.get_pending()),
            "executed_count": len(self.executed_actions),
            "rejected_count": len(self.rejected_actions),
            "pending": self.get_pending()
        }
