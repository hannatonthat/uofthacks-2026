"""
Workflow instruction management endpoints.
Handles generation, modification, and execution of workflow instructions.
"""

from typing import List, Dict, Optional, Any
import uuid
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query, Body

from utils.workflow_execution import (
    WorkflowInstruction,
    WorkflowExecutor,
    InstructionType,
    parse_instruction_from_text
)
from agents.specialized_agents import ProposalWorkflowAgent

router = APIRouter(prefix="/workflow", tags=["workflow"])


# ============================================================================
# Pydantic Models
# ============================================================================

class GenerateInstructionsRequest(BaseModel):
    """Request to generate workflow instructions from agent context."""
    sustainability_context: str
    indigenous_context: str
    proposal_title: str
    location: str
    suggested_stakeholders: Optional[List[Dict[str, str]]] = None


class InstructionModificationRequest(BaseModel):
    """Request to add or modify a workflow instruction via chat."""
    thread_id: str
    user_message: str  # Natural language like "email john@example.com about sustainability"
    instruction_index: Optional[int] = None  # For editing existing instruction


class WorkflowExecutionRequest(BaseModel):
    """Request to execute workflow instructions."""
    thread_id: str
    instructions: List[Dict[str, Any]]
    user_confirmation: bool = True


class InstructionResponse(BaseModel):
    """Response containing structured instruction."""
    id: str
    type: str
    target: str
    subject: str
    body: str
    status: str
    metadata: Dict = {}


# ============================================================================
# Instruction Generation
# ============================================================================

@router.post("/generate-instructions")
def generate_workflow_instructions(request: GenerateInstructionsRequest) -> Dict[str, Any]:
    """
    Generate initial workflow instructions from sustainability + indigenous context.
    
    Process:
    1. Synthesize sustainability and indigenous insights
    2. Create instruction sequence (email → meeting → slack → milestone)
    3. For each stakeholder: email → propose meeting → schedule follow-up
    4. Return structured instructions list
    
    Returns:
        {
            'thread_id': str,
            'proposal_title': str,
            'instructions': [
                {
                    'id': 'email_001',
                    'type': 'email',
                    'target': 'john@example.com',
                    'subject': '...',
                    'body': '...',
                    'status': 'pending'
                },
                ...
            ],
            'summary': str
        }
    """
    try:
        thread_id = f"workflow-{uuid.uuid4()}"
        instructions: List[WorkflowInstruction] = []
        instruction_counter = 1
        
        # Step 1: Generate synthesis email to self as planning summary
        synthesis_body = f"""
PROPOSAL SYNTHESIS FOR: {request.proposal_title}
Location: {request.location}

=== SUSTAINABILITY INSIGHTS ===
{request.sustainability_context}

=== INDIGENOUS PERSPECTIVES ===
{request.indigenous_context}

=== ACTION PLAN ===
This workflow will coordinate stakeholder outreach and schedule consultations.
Each contact will receive a personalized email and be invited to a meeting.
"""
        
        instructions.append(WorkflowInstruction(
            instruction_id=f"milestone_{instruction_counter:03d}",
            instruction_type=InstructionType.MILESTONE,
            target="planning",
            subject=f"Workflow Plan: {request.proposal_title}",
            body=synthesis_body,
            status="pending"
        ))
        instruction_counter += 1
        
        # Step 2: Generate instructions for each stakeholder
        stakeholders = request.suggested_stakeholders or []
        
        for idx, stakeholder in enumerate(stakeholders, 1):
            name = stakeholder.get('name') or stakeholder.get('role', 'Stakeholder')
            email = stakeholder.get('email', 'contact@example.com')
            role = stakeholder.get('role', 'Contact')
            reason = stakeholder.get('reason', 'Project consultation')
            
            # Email instruction
            email_body = f"""
Hi {name},

I hope this email finds you well. I'm reaching out regarding {request.proposal_title} at {request.location}.

Your perspective as a {role} would be invaluable for this initiative. The project integrates:
- Sustainable development principles
- Indigenous land stewardship practices
- Community-led decision making

I'd like to schedule a time to discuss how we can work together on this. Are you available for a 30-minute consultation in the coming weeks?

Thank you for your consideration.

Best regards
"""
            
            instructions.append(WorkflowInstruction(
                instruction_id=f"email_{instruction_counter:03d}",
                instruction_type=InstructionType.EMAIL,
                target=email,
                subject=f"Consultation: {request.proposal_title}",
                body=email_body.strip(),
                status="pending"
            ))
            instruction_counter += 1
            
            # Meeting instruction (proposed, will be scheduled after email response)
            instructions.append(WorkflowInstruction(
                instruction_id=f"meeting_{instruction_counter:03d}",
                instruction_type=InstructionType.MEETING,
                target=email,
                subject=f"{request.proposal_title} - Stakeholder Consultation",
                description=f"Consultation with {name} ({role}) regarding {reason}",
                duration_minutes=30,
                status="pending",
                metadata={'contact_name': name}
            ))
            instruction_counter += 1
        
        # Step 3: Slack notification for team coordination
        stakeholder_list = ", ".join([s.get('name') or s.get('role', 'Contact') for s in stakeholders])
        
        instructions.append(WorkflowInstruction(
            instruction_id=f"slack_{instruction_counter:03d}",
            instruction_type=InstructionType.SLACK,
            target="#general",
            subject=f"Workflow Initiated: {request.proposal_title}",
            body=f"🚀 Outreach workflow launched for {request.proposal_title}\n"
                 f"📍 Location: {request.location}\n"
                 f"👥 Key contacts: {stakeholder_list}\n"
                 f"📅 Consultations being scheduled",
            status="pending"
        ))
        
        return {
            'thread_id': thread_id,
            'proposal_title': request.proposal_title,
            'location': request.location,
            'instructions': [inst.to_dict() for inst in instructions],
            'summary': f"Generated {len(instructions)} workflow instructions for {len(stakeholders)} stakeholders"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate instructions: {str(e)}")


# ============================================================================
# Instruction Refinement via Chat
# ============================================================================

@router.post("/refine-instructions")
def refine_workflow_instructions(request: InstructionModificationRequest) -> Dict[str, Any]:
    """
    Refine workflow by adding/modifying instructions via conversational interface.
    
    Natural language examples:
    - "add email to jane@example.com about sustainability"
    - "schedule meeting with john for 1 hour discussion"
    - "send slack message to #general about update"
    - "edit email_001 to add more detail"
    
    Returns:
        {
            'thread_id': str,
            'user_message': str,
            'action': 'created' | 'modified' | 'deleted',
            'instruction': {...},
            'response': str
        }
    """
    try:
        # Parse user message into instruction
        instruction = parse_instruction_from_text(
            request.user_message,
            instruction_id=f"user_{request.thread_id}_{uuid.uuid4().hex[:8]}"
        )
        
        if not instruction:
            return {
                'thread_id': request.thread_id,
                'user_message': request.user_message,
                'action': 'none',
                'response': "I couldn't parse that instruction. Try formats like:\n"
                           "- 'email john@example.com about sustainability'\n"
                           "- 'schedule meeting with jane.doe@org.ca for 1 hour'\n"
                           "- 'send slack message about update'"
            }
        
        return {
            'thread_id': request.thread_id,
            'user_message': request.user_message,
            'action': 'created',
            'instruction': instruction.to_dict(),
            'response': f"✓ Created {instruction.instruction_type.value} instruction: {instruction.target}"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refine instructions: {str(e)}")


# ============================================================================
# Workflow Execution
# ============================================================================

@router.post("/execute")
def execute_workflow_instructions(request: WorkflowExecutionRequest) -> Dict[str, Any]:
    """
    Execute workflow instructions against Gmail, Google Calendar, and Slack.
    
    Process:
    1. User confirms workflow (user_confirmation=True)
    2. Convert instruction dicts to WorkflowInstruction objects
    3. Create WorkflowExecutor and run each instruction
    4. Collect results and return summary
    
    Returns:
        {
            'thread_id': str,
            'total_instructions': int,
            'executed': int,
            'failed': int,
            'results': [
                {
                    'instruction_id': str,
                    'success': bool,
                    'message': str,
                    'result': {...}
                },
                ...
            ],
            'execution_summary': {
                'success_count': int,
                'failure_count': int
            }
        }
    """
    try:
        if not request.user_confirmation:
            return {
                'thread_id': request.thread_id,
                'status': 'pending_confirmation',
                'message': 'Workflow is ready to execute. Please confirm to proceed.'
            }
        
        # Convert instruction dicts to WorkflowInstruction objects
        workflow_instructions: List[WorkflowInstruction] = []
        
        for inst_dict in request.instructions:
            instruction = WorkflowInstruction(
                instruction_id=inst_dict.get('id', f"inst_{uuid.uuid4().hex[:8]}"),
                instruction_type=InstructionType(inst_dict.get('type', 'email')),
                target=inst_dict.get('target', ''),
                subject=inst_dict.get('subject', ''),
                body=inst_dict.get('body', ''),
                duration_minutes=inst_dict.get('duration_minutes', 30),
                description=inst_dict.get('description', ''),
                status=inst_dict.get('status', 'pending'),
                metadata=inst_dict.get('metadata', {})
            )
            workflow_instructions.append(instruction)
        
        # Execute workflow
        executor = WorkflowExecutor()
        result = executor.execute_workflow(workflow_instructions)
        
        return {
            'thread_id': request.thread_id,
            'total_instructions': result['total_instructions'],
            'executed': result['executed'],
            'failed': result['failed'],
            'results': result['results'],
            'execution_summary': result['execution_summary'],
            'status': 'completed'
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute workflow: {str(e)}")


# ============================================================================
# Helper: Get Instruction Status
# ============================================================================

@router.get("/status/{thread_id}")
def get_workflow_status(thread_id: str) -> Dict[str, Any]:
    """Get status of workflow instructions for a thread."""
    # TODO: Implement thread-based instruction storage and retrieval
    # For now, return placeholder
    return {
        'thread_id': thread_id,
        'status': 'active',
        'message': 'Workflow status tracking coming soon'
    }
