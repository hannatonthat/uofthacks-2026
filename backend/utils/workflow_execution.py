"""
Workflow execution engine that maps instructions to integration calls.
Deterministically executes workflow instructions via Gmail, Google Calendar, and Slack.
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum

from utils.gmail_utils import send_gmail
from utils.google_calendar_utils import create_calendar_meeting
from utils.slack_utils import send_slack_notification, log_workflow_event


class InstructionType(str, Enum):
    """Types of workflow instructions."""
    EMAIL = "email"
    MEETING = "meeting"
    SLACK = "slack"
    MILESTONE = "milestone"


class WorkflowInstruction:
    """Structured workflow instruction."""
    
    def __init__(self, 
                 instruction_id: str,
                 instruction_type: InstructionType,
                 target: str,
                 subject: str = "",
                 body: str = "",
                 duration_minutes: int = 30,
                 description: str = "",
                 status: str = "pending",
                 metadata: Optional[Dict] = None):
        """
        Args:
            instruction_id: Unique identifier (e.g., "email_001")
            instruction_type: Type of instruction (email, meeting, slack, milestone)
            target: Email, contact name, or channel name
            subject: For email/meeting title
            body: Email body or message content
            duration_minutes: Meeting duration
            description: Meeting description
            status: pending, executed, failed, skipped
            metadata: Additional context
        """
        self.instruction_id = instruction_id
        self.instruction_type = instruction_type
        self.target = target
        self.subject = subject
        self.body = body
        self.duration_minutes = duration_minutes
        self.description = description
        self.status = status
        self.metadata = metadata or {}
        self.created_at = datetime.now().isoformat()
        self.executed_at = None
        self.result = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            'id': self.instruction_id,
            'type': self.instruction_type.value,
            'target': self.target,
            'subject': self.subject,
            'body': self.body,
            'duration_minutes': self.duration_minutes,
            'description': self.description,
            'status': self.status,
            'created_at': self.created_at,
            'executed_at': self.executed_at,
            'result': self.result,
            'metadata': self.metadata
        }


class WorkflowExecutor:
    """Executes workflow instructions against integrations."""
    
    def __init__(self, email_from: str = "nuthanan06@gmail.com", calendar_email: str = "tharmarajahnuthanan@gmail.com"):
        self.executed_instructions: List[WorkflowInstruction] = []
        self.failed_instructions: List[Dict] = []
        self.email_from = email_from
        self.calendar_email = calendar_email
    
    def execute_instruction(self, instruction: WorkflowInstruction, email_from: str = None, calendar_email: str = None) -> Dict[str, Any]:
        """
        Execute a single workflow instruction.
        
        Args:
            instruction: The instruction to execute
            email_from: Override email sender (for emails)
            calendar_email: Override calendar email (for meetings)
        
        Returns:
            {
                'success': bool,
                'instruction_id': str,
                'message': str,
                'result': Any
            }
        """
        try:
            result = None
            message = ""
            
            # Use provided overrides or fall back to defaults
            email_from = email_from or self.email_from
            calendar_email = calendar_email or self.calendar_email
            
            if instruction.instruction_type == InstructionType.EMAIL:
                result = self._execute_email(instruction, email_from=email_from)
                message = f"Email sent to {instruction.target} from {email_from}"
            
            elif instruction.instruction_type == InstructionType.MEETING:
                result = self._execute_meeting(instruction, calendar_email=calendar_email)
                message = f"Meeting scheduled with {instruction.target} on {calendar_email}"
            
            elif instruction.instruction_type == InstructionType.SLACK:
                result = self._execute_slack(instruction)
                message = f"Slack notification sent"
            
            elif instruction.instruction_type == InstructionType.MILESTONE:
                result = {"milestone": instruction.subject}
                message = f"Milestone: {instruction.subject}"
            
            instruction.status = "executed"
            instruction.executed_at = datetime.now().isoformat()
            instruction.result = result
            self.executed_instructions.append(instruction)
            
            log_workflow_event(
                f"instruction_executed_{instruction.instruction_type.value}",
                {
                    'instruction_id': instruction.instruction_id,
                    'target': instruction.target,
                    'message': message
                }
            )
            
            return {
                'success': True,
                'instruction_id': instruction.instruction_id,
                'message': message,
                'result': result
            }
        
        except Exception as e:
            instruction.status = "failed"
            instruction.result = str(e)
            self.failed_instructions.append({
                'instruction': instruction.to_dict(),
                'error': str(e)
            })
            
            log_workflow_event(
                f"instruction_failed_{instruction.instruction_type.value}",
                {
                    'instruction_id': instruction.instruction_id,
                    'error': str(e)
                }
            )
            
            return {
                'success': False,
                'instruction_id': instruction.instruction_id,
                'message': f"Failed to execute instruction: {str(e)}",
                'error': str(e)
            }
    
    def execute_workflow(self, instructions: List[WorkflowInstruction]) -> Dict[str, Any]:
        """
        Execute a list of instructions in sequence.
        
        Returns summary with execution results.
        """
        results = []
        for instruction in instructions:
            result = self.execute_instruction(instruction)
            results.append(result)
        
        return {
            'total_instructions': len(instructions),
            'executed': len(self.executed_instructions),
            'failed': len(self.failed_instructions),
            'results': results,
            'execution_summary': {
                'success_count': len([r for r in results if r['success']]),
                'failure_count': len([r for r in results if not r['success']])
            }
        }
    
    def _execute_email(self, instruction: WorkflowInstruction, email_from: str = None) -> Dict:
        """Execute an email instruction via Gmail."""
        email_from = email_from or self.email_from
        send_gmail(
            to_email=instruction.target,
            subject=instruction.subject,
            body=instruction.body,
            from_email=email_from
        )
        return {
            'to': instruction.target,
            'from': email_from,
            'subject': instruction.subject,
            'sent_at': datetime.now().isoformat()
        }
    
    def _execute_meeting(self, instruction: WorkflowInstruction, calendar_email: str = None) -> Dict:
        """Execute a meeting instruction via Google Calendar."""
        calendar_email = calendar_email or self.calendar_email
        result = create_calendar_meeting(
            contact_name=instruction.metadata.get('contact_name', instruction.target),
            contact_email=instruction.target,
            event_title=instruction.subject,
            description=instruction.description,
            duration_minutes=instruction.duration_minutes,
            calendar_email=calendar_email
        )
        return result or {'error': 'Failed to create calendar event'}
    
    def _execute_slack(self, instruction: WorkflowInstruction) -> Dict:
        """Execute a Slack notification instruction."""
        message = f"{instruction.subject}\n{instruction.body}"
        success = send_slack_notification(message)
        return {
            'channel': instruction.target,
            'sent': success,
            'timestamp': datetime.now().isoformat()
        }


def parse_instruction_from_text(text: str, instruction_id: str = "") -> Optional[WorkflowInstruction]:
    """
    Parse user text into a structured instruction.
    Handles natural language like:
    - "email john@example.com about sustainability"
    - "schedule meeting with jane.doe@org.ca for 1 hour"
    - "send slack message to #general with update"
    
    Returns:
        WorkflowInstruction or None if parsing fails
    """
    text_lower = text.lower().strip()
    
    # Email instruction: "email [email] about [subject]" or "send email to [email]"
    if any(phrase in text_lower for phrase in ['email', 'send email to', 'mail']):
        # Extract email
        import re
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        if email_match:
            email = email_match.group()
            
            # Extract subject/body
            subject_start = text_lower.find('about') + 5
            if subject_start > 4:
                subject = text[subject_start:].strip()
            else:
                subject = "Follow-up on proposal"
            
            return WorkflowInstruction(
                instruction_id=instruction_id,
                instruction_type=InstructionType.EMAIL,
                target=email,
                subject=subject,
                body=f"Hi,\n\nI wanted to reach out regarding {subject}.\n\nLooking forward to hearing from you.\n\nBest regards"
            )
    
    # Meeting instruction: "schedule meeting" or "schedule call"
    if any(phrase in text_lower for phrase in ['schedule', 'meeting', 'call', 'book']):
        import re
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        if email_match:
            email = email_match.group()
            
            # Extract duration if mentioned
            duration = 30
            duration_match = re.search(r'(\d+)\s*hour', text_lower)
            if duration_match:
                duration = int(duration_match.group(1)) * 60
            else:
                duration_match = re.search(r'(\d+)\s*min', text_lower)
                if duration_match:
                    duration = int(duration_match.group(1))
            
            # Extract subject
            subject = "Project Discussion and Consultation"
            for_match = re.search(r'for\s+(.+?)(?:to|on|with|$)', text)
            if for_match:
                subject = for_match.group(1).strip()
            
            return WorkflowInstruction(
                instruction_id=instruction_id,
                instruction_type=InstructionType.MEETING,
                target=email,
                subject=subject,
                description=f"Discussion regarding {subject}",
                duration_minutes=duration,
                metadata={'contact_name': text.split('with')[-1].split('at')[0].strip() if 'with' in text else 'Contact'}
            )
    
    # Slack instruction: "send slack" or "post message"
    if any(phrase in text_lower for phrase in ['slack', 'message']):
        return WorkflowInstruction(
            instruction_id=instruction_id,
            instruction_type=InstructionType.SLACK,
            target="#general",
            subject="Workflow Update",
            body=text.replace('send slack', '').replace('post', '').strip()
        )
    
    return None
