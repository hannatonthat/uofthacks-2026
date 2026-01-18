"""
Workflow thread state management - maintains thread context and regenerates instructions dynamically.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
import json
import os
import requests

class WorkflowThreadState:
    """Maintains state for a single workflow thread."""
    
    def __init__(self, thread_id: str, proposal_title: str, location: str, 
                 sustainability_context: str, indigenous_context: str):
        self.thread_id = thread_id
        self.proposal_title = proposal_title
        self.location = location
        self.sustainability_context = sustainability_context
        self.indigenous_context = indigenous_context
        
        # Email configuration
        self.email_sender = "nuthanan06@gmail.com"
        self.meeting_recipient = "tharmarajahnuthanan@gmail.com"
        
        # Workflow state
        self.instructions: List[Dict[str, Any]] = []
        self.message_history: List[Dict[str, str]] = []
        self.stakeholders: Dict[str, Dict[str, Any]] = {}  # email -> {role, context, added_at, type}
        self.created_at = datetime.now().isoformat()
        self.last_updated = datetime.now().isoformat()
    
    def add_message(self, role: str, content: str):
        """Add message to thread history."""
        self.message_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.last_updated = datetime.now().isoformat()
    
    def add_stakeholder(self, email: str, role: str, context: str = "", stakeholder_type: str = "both"):
        """
        Add or update a stakeholder.
        
        Args:
            email: Stakeholder email
            role: Their role/title
            context: What they're being consulted for
            stakeholder_type: 'both' (email+meeting), 'email' (email only), or 'meeting' (meeting only)
        """
        self.stakeholders[email] = {
            "role": role,
            "context": context,
            "added_at": datetime.now().isoformat(),
            "type": stakeholder_type  # NEW: track what to generate
        }
        self.last_updated = datetime.now().isoformat()
    
    def remove_stakeholder(self, email: str):
        """Remove a stakeholder."""
        if email in self.stakeholders:
            del self.stakeholders[email]
            self.last_updated = datetime.now().isoformat()
    
    def regenerate_instructions(self) -> List[Dict[str, Any]]:
        """
        Regenerate all workflow instructions based on current state.
        
        Instructions structure:
        1. Milestone: Workflow plan summary
        2. For each stakeholder: Email + Meeting pair
        3. Slack notification
        
        This is called after every message to show live updates.
        """
        new_instructions = []
        instruction_counter = 1
        
        # 1. Milestone: Workflow planning summary
        synthesis_body = f"""
PROPOSAL SYNTHESIS FOR: {self.proposal_title}
Location: {self.location}

=== SUSTAINABILITY INSIGHTS ===
{self.sustainability_context}

=== INDIGENOUS PERSPECTIVES ===
{self.indigenous_context}

=== STAKEHOLDERS ({len(self.stakeholders)}) ===
"""
        for email, info in self.stakeholders.items():
            synthesis_body += f"\n• {info['role']} ({email})"
        
        synthesis_body += f"""

=== ACTION PLAN ===
Each stakeholder will receive a personalized email and calendar invite.
All emails sent from: {self.email_sender}
All meetings scheduled for: {self.meeting_recipient}
"""
        
        new_instructions.append({
            "id": f"milestone_{instruction_counter:03d}",
            "type": "milestone",
            "target": "planning",
            "subject": f"Workflow Plan: {self.proposal_title}",
            "body": synthesis_body.strip(),
            "status": "pending",
            "metadata": {}
        })
        instruction_counter += 1
        
        # 2. Generate email + meeting for each stakeholder - USE AI TO GENERATE EMAILS
        for email, info in self.stakeholders.items():
            role = info['role']
            context = info['context']
            stakeholder_type = info.get('type', 'both')  # Default to both if not specified
            
            # Generate EMAIL if type is 'both' or 'email'
            if stakeholder_type in ['both', 'email']:
                # Generate personalized email using AI
                email_subject, email_body = self._generate_personalized_email(email, role, context)
                
                new_instructions.append({
                    "id": f"email_{instruction_counter:03d}",
                    "type": "email",
                    "target": email,
                    "subject": email_subject,
                    "body": email_body.strip(),
                    "status": "pending",
                    "metadata": {"role": role, "context": context}
                })
                instruction_counter += 1
            
            # Generate MEETING if type is 'both' or 'meeting'
            if stakeholder_type in ['both', 'meeting']:
                # Meeting instruction - personalized based on context
                if context:
                    meeting_subject = f"{self.proposal_title} - {context.split()[0].title()} Discussion with {role}"
                    meeting_body = f"""30-minute consultation with {role} ({email})

Topic: {context}

Agenda:
- Review project scope and timeline
- Discuss {context} requirements and recommendations
- Identify potential challenges and solutions
- Next steps and deliverables

Location: Video call or in-person (TBD)"""
                else:
                    meeting_subject = f"{self.proposal_title} - {role} Consultation"
                    meeting_body = f"""30-minute consultation with {role} ({email})

Agenda:
- Project overview and objectives
- Stakeholder input and expertise
- Collaboration opportunities
- Next steps

Location: Video call or in-person (TBD)"""
                
                new_instructions.append({
                    "id": f"meeting_{instruction_counter:03d}",
                    "type": "meeting",
                    "target": self.meeting_recipient,  # Meeting on calendar for this email
                    "subject": meeting_subject,
                    "body": meeting_body.strip(),
                    "status": "pending",
                    "metadata": {
                        "attendee_email": email,
                        "attendee_role": role,
                        "duration_minutes": 30,
                        "context": context
                    }
                })
                instruction_counter += 1
        
        # 3. Slack notification (if stakeholders exist)
        if self.stakeholders:
            stakeholder_list = ", ".join([f"{info['role']}" for info in self.stakeholders.values()])
            new_instructions.append({
                "id": f"slack_{instruction_counter:03d}",
                "type": "slack",
                "target": "#general",
                "subject": f"Workflow Initiated: {self.proposal_title}",
                "body": f"🚀 Outreach workflow launched for {self.proposal_title}\n"
                       f"📍 Location: {self.location}\n"
                       f"👥 Stakeholders: {stakeholder_list}\n"
                       f"📧 Emails to send: {len([i for i in new_instructions if i['type'] == 'email'])}\n"
                       f"📅 Meetings to schedule: {len([i for i in new_instructions if i['type'] == 'meeting'])}",
                "status": "pending",
                "metadata": {}
            })
        
        self.instructions = new_instructions
        self.last_updated = datetime.now().isoformat()
        return new_instructions
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of current workflow state."""
        emails = [i for i in self.instructions if i['type'] == 'email']
        meetings = [i for i in self.instructions if i['type'] == 'meeting']
        
        return {
            "thread_id": self.thread_id,
            "proposal_title": self.proposal_title,
            "location": self.location,
            "email_sender": self.email_sender,
            "meeting_recipient": self.meeting_recipient,
            "stakeholder_count": len(self.stakeholders),
            "email_count": len(emails),
            "meeting_count": len(meetings),
            "total_instructions": len(self.instructions),
            "last_updated": self.last_updated,
            "created_at": self.created_at
        }
    
    def _generate_personalized_email(self, recipient_email: str, role: str, context: str) -> tuple[str, str]:
        """
        Generate a personalized email using AI based on the full proposal context.
        Returns (subject, body)
        """
        api_key = os.getenv("BACKBOARD_API_KEY")
        
        if not api_key:
            # Fallback to template if no API key
            if context:
                subject = f"{self.proposal_title} - Collaboration Request"
                body = f"""Hi {role},

I'm reaching out regarding {self.proposal_title} at {self.location}.

Your expertise in {context} would be invaluable. The project integrates sustainable development with Indigenous land stewardship practices.

I'd like to discuss how we can collaborate. Are you available for a consultation?

Best regards"""
            else:
                subject = f"Consultation: {self.proposal_title}"
                body = f"""Hi {role},

I'm reaching out regarding {self.proposal_title} at {self.location}.

Your perspective would be invaluable for this initiative. I'd like to schedule a consultation to discuss collaboration.

Best regards"""
            return subject, body
        
        # Use AI to generate personalized email
        try:
            # Create a simple one-shot prompt using BackboardProvider
            from agents.backboard_provider import BackboardProvider
            
            provider = BackboardProvider()
            
            prompt = f"""You are writing a professional consultation request email for a development project.

PROJECT DETAILS:
Title: {self.proposal_title}
Location: {self.location}

SUSTAINABILITY ANALYSIS:
{self.sustainability_context}

INDIGENOUS PERSPECTIVES:
{self.indigenous_context}

RECIPIENT INFORMATION:
- Role/Title: {role}
- Area of Expertise: {context if context else role}
- Email: {recipient_email}

INSTRUCTIONS:
Write a highly personalized, professional email that:

1. SUBJECT LINE: Create a specific subject mentioning both the project location AND their expertise area (e.g., "Financial Strategy for [Location] Development" or "Indigenous Consultation - [Project Name]")

2. EMAIL BODY must include:
   - Warm, professional greeting addressing them by role
   - Brief introduction of the project with specific details from the sustainability and Indigenous context above
   - Explain EXACTLY why their specific expertise in "{context if context else role}" is critical for this project
   - Reference specific aspects from the context that relate to their role (e.g., for financial advisor: budget planning, funding strategies, ROI; for environmental consultant: ecosystem impact, green certifications)
   - Describe 2-3 specific questions or areas you need their input on
   - Propose a 30-minute consultation meeting
   - Professional closing

3. Make it conversational but professional, showing you've done research on what they can contribute

Format your response exactly as:
SUBJECT: [specific subject line]
BODY: [complete email body]"""

            # Create temporary assistant for email generation
            assistant_id = provider.create_assistant(
                name="Email Generator",
                system_prompt="You are a professional email writer for development proposal consultations. Generate clear, personalized emails.",
                model="gpt-4o-mini"
            )
            
            # Send message and get response
            response_content, _ = provider.chat(assistant_id, prompt)
            
            print(f"[DEBUG] AI Response: {response_content[:200]}...")  # Debug log
            
            # Parse the response - try multiple formats
            if "SUBJECT:" in response_content and "BODY:" in response_content:
                # Split by SUBJECT: and BODY:
                subject_part = response_content.split("SUBJECT:")[1].split("BODY:")[0].strip()
                body_part = response_content.split("BODY:")[1].strip()
                
                # Clean up subject (take first line only)
                subject = subject_part.split("\n")[0].strip()
                
                return subject, body_part
            else:
                # Try to parse as structured response
                lines = response_content.strip().split("\n")
                if len(lines) >= 2:
                    # First line as subject, rest as body
                    subject = lines[0].strip()
                    body = "\n".join(lines[1:]).strip()
                    return subject, body
            
            # Fallback if parsing fails
            raise Exception(f"Failed to parse AI response")
            
        except Exception as e:
            print(f"AI email generation failed: {e}. Using template.")
            # Fallback to template
            if context:
                subject = f"{self.proposal_title} - {context.split()[0].title()} Consultation"
                body = f"""Hi {role},

I'm reaching out regarding {self.proposal_title} at {self.location}.

Your expertise in {context} would be invaluable. The project integrates sustainable development with Indigenous land stewardship.

I'd like to discuss your insights. Are you available for a 30-minute consultation?

Best regards"""
            else:
                subject = f"Consultation: {self.proposal_title}"
                body = f"""Hi {role},

I'm reaching out regarding {self.proposal_title} at {self.location}.

Your perspective would be valuable. I'd like to schedule a consultation.

Best regards"""
            return subject, body
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize thread state to dict."""
        return {
            "thread_id": self.thread_id,
            "proposal_title": self.proposal_title,
            "location": self.location,
            "sustainability_context": self.sustainability_context,
            "indigenous_context": self.indigenous_context,
            "email_sender": self.email_sender,
            "meeting_recipient": self.meeting_recipient,
            "stakeholders": self.stakeholders,
            "instructions": self.instructions,
            "message_history": self.message_history,
            "summary": self.get_summary()
        }


# Global thread storage (in production, use database)
workflow_threads: Dict[str, WorkflowThreadState] = {}


def create_thread(thread_id: str, proposal_title: str, location: str,
                 sustainability_context: str, indigenous_context: str) -> WorkflowThreadState:
    """Create a new workflow thread."""
    thread = WorkflowThreadState(
        thread_id=thread_id,
        proposal_title=proposal_title,
        location=location,
        sustainability_context=sustainability_context,
        indigenous_context=indigenous_context
    )
    workflow_threads[thread_id] = thread
    return thread


def get_thread(thread_id: str) -> Optional[WorkflowThreadState]:
    """Get existing thread."""
    return workflow_threads.get(thread_id)


def delete_thread(thread_id: str) -> bool:
    """Delete a thread."""
    if thread_id in workflow_threads:
        del workflow_threads[thread_id]
        return True
    return False


def list_threads() -> List[Dict[str, Any]]:
    """List all active threads."""
    return [thread.get_summary() for thread in workflow_threads.values()]
