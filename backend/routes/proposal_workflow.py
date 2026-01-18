"""
Proposal workflow API endpoints - handles instruction generation, refinement, and execution.
These endpoints work specifically with the Proposal agent and regenerate on each message.
"""

from typing import List, Dict, Optional, Any
import uuid
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from datetime import datetime

from utils.workflow_state import (
    create_thread, get_thread, delete_thread, list_threads,
    WorkflowThreadState
)
from utils.workflow_execution import (
    WorkflowInstruction,
    WorkflowExecutor,
    InstructionType,
    parse_instruction_from_text
)

router = APIRouter(prefix="/proposal-workflow", tags=["proposal_workflow"])


# ============================================================================
# Pydantic Models
# ============================================================================

class ProposalWorkflowInitRequest(BaseModel):
    """Initialize a proposal workflow."""
    proposal_title: str
    location: str
    sustainability_context: str
    indigenous_context: str


class ProposalWorkflowMessageRequest(BaseModel):
    """Add a message and regenerate workflow instructions."""
    thread_id: str
    user_message: str


class WorkflowConfigUpdateRequest(BaseModel):
    """Update workflow configuration (sender/recipient emails)."""
    thread_id: str
    email_sender: Optional[str] = None
    meeting_recipient: Optional[str] = None


class WorkflowExecuteRequest(BaseModel):
    """Execute workflow instructions."""
    thread_id: str
    user_confirmation: bool = True


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/init")
def initialize_proposal_workflow(request: ProposalWorkflowInitRequest) -> Dict[str, Any]:
    """
    Initialize a new proposal workflow thread with starter stakeholders.
    
    Auto-generates 2-3 suggested stakeholders based on context.
    """
    try:
        thread_id = f"proposal-{uuid.uuid4().hex[:12]}"
        
        thread = create_thread(
            thread_id=thread_id,
            proposal_title=request.proposal_title,
            location=request.location,
            sustainability_context=request.sustainability_context,
            indigenous_context=request.indigenous_context
        )
        
        # Add initial message to history
        thread.add_message("system", f"Workflow initialized for: {request.proposal_title}")
        
        # Auto-generate starter stakeholders to give users examples
        location_name = request.location.split(',')[0] if ',' in request.location else request.location
        
        # Add 3 example stakeholders
        thread.add_stakeholder(
            "sustainability.lead@example.ca",
            "Sustainability Lead",
            "Oversee environmental compliance and green initiatives"
        )
        
        thread.add_stakeholder(
            "indigenous.relations@example.ca",
            "Indigenous Relations Officer",
            "Ensure consultation and respect for traditional land stewardship"
        )
        
        thread.add_stakeholder(
            "community.liaison@example.ca",
            "Community Liaison",
            f"Coordinate with {location_name} residents and local stakeholders"
        )
        
        # Generate initial instructions
        instructions = thread.regenerate_instructions()
        
        return {
            "thread_id": thread_id,
            "proposal_title": request.proposal_title,
            "location": request.location,
            "email_sender": thread.email_sender,
            "meeting_recipient": thread.meeting_recipient,
            "instructions": instructions,
            "stakeholder_count": len(thread.stakeholders),
            "status": "initialized"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize workflow: {str(e)}")


@router.post("/message")
def add_message_to_workflow(request: ProposalWorkflowMessageRequest) -> Dict[str, Any]:
    """
    Add a message to workflow thread and regenerate instructions.
    
    The message is parsed to identify stakeholder additions, removals, or modifications.
    All instructions are regenerated based on current state.
    
    Natural language patterns:
    - "add [Role] at [email@example.com] for [context]"
    - "remove [Role]" or "remove [email@example.com]"
    - "change [Role] to [new@email.com]"
    - "update proposal to [new title]"
    """
    try:
        thread = get_thread(request.thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Workflow thread not found")
        
        user_message = request.user_message
        thread.add_message("user", user_message)
        
        # Parse the message for stakeholder modifications
        response_text = ""
        import re
        
        # Pattern 0: Book/Schedule Meeting - NEW PATTERN
        # Matches: "book meeting with X", "schedule meeting with X for Y", "meeting with X about Y"
        meeting_keywords = ["book meeting", "schedule meeting", "meeting with", "schedule call", "book call"]
        if any(keyword in user_message.lower() for keyword in meeting_keywords):
            email_pattern = r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
            email_match = re.search(email_pattern, user_message)
            
            if email_match:
                email = email_match.group(1)
                
                # Extract role if provided
                role = ""
                role_pattern = r"(?:with|for)\s+([^@]+?)\s+(?:at|@)?\s*" + re.escape(email)
                role_match = re.search(role_pattern, user_message, re.IGNORECASE)
                if role_match:
                    role = role_match.group(1).strip()
                if not role or len(role) < 2:
                    role = "Stakeholder"
                
                # Extract context - what the meeting is about
                context = ""
                context_pattern = r"(?:for|about|regarding|on)\s+(.+)$"
                context_match = re.search(context_pattern, user_message, re.IGNORECASE)
                if context_match:
                    context = context_match.group(1).strip()
                
                # Add stakeholder with type='meeting' (meeting only, no email)
                thread.add_stakeholder(email, role, context, stakeholder_type='meeting')
                response_text = f"✓ Scheduled meeting with {role} ({email})"
                if context:
                    response_text += f" regarding {context}"
            else:
                response_text = "Please include an email address for the meeting (e.g., person@example.com)"
        
        # Pattern 1: Add stakeholder - more flexible patterns
        # Matches: "add X", "add X at email", "add X as Y", "contact X", "include X", etc.
        elif any(keyword in user_message.lower() for keyword in ["add", "include", "contact", "reach out", "send to", "email", "invite"]):
            # Try to extract email
            email_pattern = r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
            email_match = re.search(email_pattern, user_message)
            
            if email_match:
                email = email_match.group(1)
                
                # Try to extract role - look for words before/after email or keywords
                role = ""
                context = ""
                
                # Pattern: "add [role] at [email]"
                role_pattern1 = r"(?:add|include|contact|invite)\s+([^@]+?)\s+(?:at|:|as)?\s*" + re.escape(email)
                role_match1 = re.search(role_pattern1, user_message, re.IGNORECASE)
                if role_match1:
                    role = role_match1.group(1).strip()
                
                # Pattern: "[email] as [role]"
                if not role:
                    role_pattern2 = re.escape(email) + r"\s+as\s+([^,\.]+)"
                    role_match2 = re.search(role_pattern2, user_message, re.IGNORECASE)
                    if role_match2:
                        role = role_match2.group(1).strip()
                
                # Default role if none found
                if not role or len(role) < 2:
                    role = "Stakeholder"
                
                # Try to extract context - look for "for", "regarding", "about"
                context_pattern = r"(?:for|regarding|about|on)\s+(.+)$"
                context_match = re.search(context_pattern, user_message, re.IGNORECASE)
                if context_match:
                    context = context_match.group(1).strip()
                
                thread.add_stakeholder(email, role, context)
                response_text = f"✓ Added {role} ({email})"
                if context:
                    response_text += f" - {context}"
            else:
                response_text = "Please include an email address (e.g., person@example.com)"
        
        # Pattern 2: Remove stakeholder
        elif "remove " in user_message.lower():
            import re
            # Try to match email or role
            email_pattern = r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
            email_match = re.search(email_pattern, user_message)
            
            if email_match:
                email = email_match.group(1)
                if email in thread.stakeholders:
                    role = thread.stakeholders[email]['role']
                    thread.remove_stakeholder(email)
                    response_text = f"✓ Removed {role} ({email})"
                else:
                    response_text = f"Email {email} not found in stakeholders"
            else:
                # Try to match by role name
                response_text = "Could not parse email to remove. Try: 'remove [email@example.com]'"
        
        # Pattern 3: Update sender or recipient
        elif "email from " in user_message.lower() or "sender " in user_message.lower():
            import re
            email_pattern = r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
            email_match = re.search(email_pattern, user_message)
            if email_match:
                new_sender = email_match.group(1)
                thread.email_sender = new_sender
                response_text = f"✓ Updated email sender to {new_sender}"
        
        elif "meeting recipient " in user_message.lower() or "calendar " in user_message.lower():
            import re
            email_pattern = r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
            email_match = re.search(email_pattern, user_message)
            if email_match:
                new_recipient = email_match.group(1)
                thread.meeting_recipient = new_recipient
                response_text = f"✓ Updated meeting recipient to {new_recipient}"
        
        else:
            response_text = "Message noted. Commands: 'add [Role] at [email]', 'remove [email]', 'update sender', 'update recipient'"
        
        # Regenerate instructions
        instructions = thread.regenerate_instructions()
        
        return {
            "thread_id": thread.thread_id,
            "user_message": user_message,
            "response": response_text,
            "instructions": instructions,
            "stakeholder_count": len(thread.stakeholders),
            "email_count": len([i for i in instructions if i['type'] == 'email']),
            "meeting_count": len([i for i in instructions if i['type'] == 'meeting']),
            "summary": thread.get_summary()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process message: {str(e)}")


@router.get("/status/{thread_id}")
def get_workflow_status(thread_id: str) -> Dict[str, Any]:
    """Get current workflow status and all instructions."""
    try:
        thread = get_thread(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Workflow thread not found")
        
        return thread.to_dict()
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.post("/config")
def update_workflow_config(request: WorkflowConfigUpdateRequest) -> Dict[str, Any]:
    """Update workflow configuration (email sender, meeting recipient)."""
    try:
        thread = get_thread(request.thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Workflow thread not found")
        
        if request.email_sender:
            thread.email_sender = request.email_sender
        if request.meeting_recipient:
            thread.meeting_recipient = request.meeting_recipient
        
        # Regenerate instructions with new config
        instructions = thread.regenerate_instructions()
        
        return {
            "thread_id": thread.thread_id,
            "email_sender": thread.email_sender,
            "meeting_recipient": thread.meeting_recipient,
            "instructions": instructions,
            "summary": thread.get_summary()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}")


@router.post("/execute")
def execute_workflow(request: WorkflowExecuteRequest) -> Dict[str, Any]:
    """
    Execute all instructions in the workflow.
    
    Executes against Gmail (emails), Google Calendar (meetings), and Slack (notifications).
    """
    try:
        thread = get_thread(request.thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Workflow thread not found")
        
        if not request.user_confirmation:
            raise HTTPException(status_code=400, detail="User confirmation required")
        
        # Convert thread instructions to WorkflowInstruction objects
        workflow_instructions = []
        for inst in thread.instructions:
            workflow_instructions.append(WorkflowInstruction(
                instruction_id=inst['id'],
                instruction_type=InstructionType(inst['type']),
                target=inst['target'],
                subject=inst['subject'],
                body=inst['body'],
                status='pending',
                metadata=inst.get('metadata', {})
            ))
        
        # Execute all instructions
        executor = WorkflowExecutor()
        results = []
        executed_count = 0
        failed_count = 0
        
        for instruction in workflow_instructions:
            try:
                # For email instructions, set the from_email to the configured sender
                if instruction.instruction_type == InstructionType.EMAIL:
                    result = executor.execute_instruction(instruction, email_from=thread.email_sender)
                # For meeting instructions, set the attendee to the configured recipient
                elif instruction.instruction_type == InstructionType.MEETING:
                    result = executor.execute_instruction(instruction, calendar_email=thread.meeting_recipient)
                else:
                    result = executor.execute_instruction(instruction)
                
                results.append({
                    "instruction_id": instruction.instruction_id,
                    "type": instruction.instruction_type.value,
                    "target": instruction.target,
                    "success": True,
                    "message": result.get('message', 'Executed'),
                    "timestamp": datetime.now().isoformat()
                })
                executed_count += 1
                instruction.status = 'completed'
            except Exception as e:
                failed_count += 1
                results.append({
                    "instruction_id": instruction.instruction_id,
                    "type": instruction.instruction_type.value,
                    "target": instruction.target,
                    "success": False,
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                instruction.status = 'failed'
        
        # Add execution message to thread
        thread.add_message("system", f"Workflow executed: {executed_count} successful, {failed_count} failed")
        
        return {
            "thread_id": thread.thread_id,
            "executed": executed_count,
            "failed": failed_count,
            "total": len(workflow_instructions),
            "results": results,
            "execution_summary": {
                "success_rate": f"{(executed_count / len(workflow_instructions) * 100):.1f}%" if workflow_instructions else "0%",
                "timestamp": datetime.now().isoformat(),
                "status": "completed" if executed_count > 0 else "failed"
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute workflow: {str(e)}")


@router.get("/threads")
def list_all_threads() -> Dict[str, Any]:
    """List all active workflow threads."""
    try:
        threads = list_threads()
        return {
            "count": len(threads),
            "threads": threads
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list threads: {str(e)}")


@router.delete("/delete/{thread_id}")
def delete_workflow_thread(thread_id: str) -> Dict[str, Any]:
    """Delete a workflow thread."""
    try:
        success = delete_thread(thread_id)
        if not success:
            raise HTTPException(status_code=404, detail="Workflow thread not found")
        
        return {
            "thread_id": thread_id,
            "status": "deleted",
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete thread: {str(e)}")
