"""LangChain tools for AI-driven workflow execution using Backboard API."""

from typing import Optional, Dict, Any, List
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentType
from langchain_community.chat_models import ChatOpenAI
from .backboard_provider import BackboardProvider
import os


def create_workflow_tools(agent) -> List[Tool]:
    """
    Create LangChain tools from ProposalWorkflowAgent methods.
    
    The LLM will automatically choose which tool to use based on user intent.
    
    EXAMPLE USER INTENTS → TOOL MAPPING:
      "Send emails to everyone" → SendEmails tool
      "Set up meetings" → ScheduleMeetings tool
      "Launch full outreach" → FullOutreach tool
      "Add Chief Sarah to contacts" → AddContact tool
      "Show me who we've contacted" → GetContacts tool
    """
    
    def send_emails_wrapper(proposal_title: str) -> str:
        """Send outreach emails to all contacts."""
        try:
            result = agent.execute_send_emails(proposal_title=proposal_title)
            return f"✓ Sent {result['sent_count']} emails successfully. {len(result['errors'])} errors."
        except Exception as e:
            return f"Error sending emails: {str(e)}"
    
    def schedule_meetings_wrapper(event_type_name: str = "Consultation Meeting") -> str:
        """Generate Calendly scheduling links for all contacts."""
        try:
            result = agent.execute_schedule_meetings(event_type_name=event_type_name)
            return f"✓ Created {result['links_count']} scheduling links for {event_type_name}"
        except Exception as e:
            return f"Error creating scheduling links: {str(e)}"
    
    def full_outreach_wrapper(proposal_title: str, event_type_name: str = "Consultation Meeting") -> str:
        """Execute complete outreach workflow (emails with scheduling links)."""
        try:
            result = agent.execute_full_outreach_workflow(
                proposal_title=proposal_title,
                event_type_name=event_type_name
            )
            return f"✓ Full outreach complete! Sent {result['emails_sent']} emails with {result['meetings_scheduled']} scheduling links."
        except Exception as e:
            return f"Error executing full outreach: {str(e)}"
    
    def add_contact_wrapper(name: str, role: str, email: str, phone: str = "") -> str:
        """Add a new contact to the outreach list."""
        try:
            agent.add_contact(name=name, role=role, email=email, phone=phone)
            total = len(agent.get_contacts())
            return f"✓ Added {name} ({role}) to contacts. Total: {total}"
        except Exception as e:
            return f"Error adding contact: {str(e)}"
    
    def get_contacts_wrapper(dummy: str = "") -> str:
        """Get list of all contacts in the outreach list."""
        contacts = agent.get_contacts()
        if not contacts:
            return "No contacts added yet. Use add_contact to add tribal leaders and stakeholders."
        
        result = f"Total contacts: {len(contacts)}\n\n"
        for i, c in enumerate(contacts, 1):
            result += f"{i}. {c['name']} ({c['role']}) - {c['email']}\n"
        return result
    
    def get_workflow_status_wrapper(dummy: str = "") -> str:
        """Get current workflow submission progress."""
        status = agent.get_submission_status()
        history = agent.get_workflow_history()
        
        result = f"Workflow Progress: Step {status['step']}/{status['total_steps']}\n\n"
        
        if history:
            result += "Recent Actions:\n"
            for action in history[-5:]:  # Last 5 actions
                result += f"  - {action['action']}: {action.get('recipient', 'N/A')}\n"
        else:
            result += "No workflow actions executed yet.\n"
        
        return result
    
    # Define tools with descriptions for LLM
    tools = [
        Tool(
            name="SendEmails",
            func=send_emails_wrapper,
            description=(
                "Send personalized outreach emails to all contacts in the list. "
                "Use when user wants to email tribal leaders, stakeholders, or contacts. "
                "Input: proposal_title (string, e.g., 'Sustainable Land Development')"
            )
        ),
        Tool(
            name="ScheduleMeetings",
            func=schedule_meetings_wrapper,
            description=(
                "Generate Calendly scheduling links for consultation meetings with all contacts. "
                "Use when user wants to set up meetings, consultations, or schedule calls. "
                "Input: event_type_name (string, e.g., 'Indigenous Consultation', default: 'Consultation Meeting')"
            )
        ),
        Tool(
            name="FullOutreach",
            func=full_outreach_wrapper,
            description=(
                "Execute complete outreach workflow: generate emails with embedded scheduling links and send to all contacts. "
                "Use when user wants to launch full consultation process, initiate outreach campaign, or start engagement. "
                "Input: proposal_title (string), event_type_name (optional string)"
            )
        ),
        Tool(
            name="AddContact",
            func=add_contact_wrapper,
            description=(
                "Add a new contact (tribal leader, stakeholder, etc.) to the outreach list. "
                "Use when user mentions adding someone, needs to contact someone, or provides contact information. "
                "Input: name (string), role (string), email (string), phone (optional string)"
            )
        ),
        Tool(
            name="GetContacts",
            func=get_contacts_wrapper,
            description=(
                "View all contacts currently in the outreach list. "
                "Use when user asks who's on the list, wants to see contacts, or review stakeholders. "
                "Input: dummy (not used, just pass empty string)"
            )
        ),
        Tool(
            name="GetWorkflowStatus",
            func=get_workflow_status_wrapper,
            description=(
                "Check current workflow progress and recent actions (emails sent, meetings scheduled). "
                "Use when user asks about status, progress, what's been done, or workflow history. "
                "Input: dummy (not used, just pass empty string)"
            )
        ),
    ]
    
    return tools


def create_workflow_agent(proposal_workflow_agent):
    """
    Create AI agent that automatically executes workflows based on user intent.
    Uses Backboard API to access Claude models.
    
    USER SAYS:
      "Can you email all the tribal leaders about the proposal?"
    
    AI THINKS:
      "User wants to send emails → I should use SendEmails tool"
    
    AI EXECUTES:
      SendEmails(proposal_title="...") → Emails sent!
    
    RETURNS:
      "✓ Sent 3 emails successfully to Chief Sarah, Elder John, and Dr. Martinez"
    """
    
    # Get Backboard API key from environment
    api_key = os.getenv("BACKBOARD_API_KEY")
    if not api_key:
        raise ValueError("BACKBOARD_API_KEY not found. Add to .env for AI-driven workflow execution.")
    
    # Create Backboard provider
    backboard = BackboardProvider()
    
    # Create assistant with Claude via Backboard
    assistant_id = backboard.create_assistant(
        name="Workflow Execution Agent",
        system_prompt=(
            "You are a workflow automation assistant. When users describe what they want to do, "
            "you choose the appropriate tool and execute it. Be concise and action-oriented. "
            "Always confirm what action was taken and provide clear results."
        ),
        model="claude-3-5-sonnet"
    )
    
    # Create custom LLM wrapper for LangChain that uses Backboard
    class BackboardLLM:
        """Wrapper to use Backboard API with LangChain."""
        def __init__(self, backboard_provider, assistant_id):
            self.backboard = backboard_provider
            self.assistant_id = assistant_id
            self.thread_id = None
        
        def __call__(self, prompt: str) -> str:
            """Call Backboard API."""
            response, self.thread_id = self.backboard.chat(
                self.assistant_id,
                prompt,
                self.thread_id
            )
            return response
        
        def invoke(self, prompt: str) -> str:
            """LangChain invoke interface."""
            return self(prompt)
    
    # Create tools
    tools = create_workflow_tools(proposal_workflow_agent)
    
    # Use simple tool execution loop instead of full LangChain agent
    # This avoids complex LangChain dependencies while keeping AI decision-making
    def execute_with_ai(user_intent: str) -> str:
        """Execute user intent with AI tool selection."""
        # Build prompt with available tools
        tools_desc = "\n".join([
            f"- {tool.name}: {tool.description}"
            for tool in tools
        ])
        
        prompt = f"""You are a workflow automation assistant. Based on the user's intent, choose ONE tool to execute.

Available tools:
{tools_desc}

User intent: {user_intent}

Respond in this exact format:
TOOL: <tool_name>
REASONING: <brief explanation>
PARAMETERS: <parameters as key=value, comma separated>

Example:
TOOL: SendEmails
REASONING: User wants to send outreach emails
PARAMETERS: proposal_title=Sustainable Development"""

        # Get AI response via Backboard
        llm = BackboardLLM(backboard, assistant_id)
        response = llm(prompt)
        
        # Parse response
        lines = response.strip().split('\n')
        tool_name = None
        params = {}
        
        for line in lines:
            if line.startswith('TOOL:'):
                tool_name = line.replace('TOOL:', '').strip()
            elif line.startswith('PARAMETERS:'):
                param_str = line.replace('PARAMETERS:', '').strip()
                if param_str and param_str.lower() != 'none':
                    for param in param_str.split(','):
                        if '=' in param:
                            key, value = param.strip().split('=', 1)
                            params[key.strip()] = value.strip()
        
        # Execute chosen tool
        if tool_name:
            for tool in tools:
                if tool.name == tool_name:
                    # Call tool with extracted parameters
                    if params:
                        # Pass first parameter as string argument
                        param_value = list(params.values())[0] if params else ""
                        return tool.func(param_value)
                    else:
                        return tool.func("")
        
        return "❌ Could not determine which workflow to execute. Please be more specific."
    
    return execute_with_ai


# Example usage:
"""
# In your API endpoint:
proposal_agent = ProposalWorkflowAgent()

# Add contacts first
proposal_agent.add_contact("Chief Sarah", "Tribal Leader", "chief@tribe.ca")
proposal_agent.add_contact("Dr. James", "Environmental Officer", "james@env.gov.bc.ca")

# Create AI agent (uses Backboard API with Claude)
ai_executor = create_workflow_agent(proposal_agent)

# User just describes what they want
user_intent = "I want to reach out to all the tribal leaders about the sustainable development proposal"

# AI automatically:
# 1. Understands intent (send emails)
# 2. Chooses FullOutreach tool
# 3. Executes workflow
# 4. Returns human-friendly response
response = ai_executor(user_intent)
print(response)
# Output: "✓ Full outreach complete! Sent 2 emails with 2 scheduling links."
"""
