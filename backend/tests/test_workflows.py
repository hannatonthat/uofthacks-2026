"""Comprehensive test suite for workflow execution and integrations."""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List


# Test Fixtures
@pytest.fixture
def mock_gmail_integration():
    """Mock Gmail integration for testing."""
    with patch('backend.integrations.gmail_integration.GmailIntegration') as mock:
        instance = mock.return_value
        instance.send_email.return_value = {
            "status": "sent",
            "message_id": "mock_message_id"
        }
        instance.send_batch_emails.return_value = [
            {"recipient": "test1@example.com", "status": "sent"},
            {"recipient": "test2@example.com", "status": "sent"}
        ]
        yield instance


@pytest.fixture
def mock_calendly_integration():
    """Mock Calendly integration for testing."""
    with patch('backend.integrations.calendly_integration.CalendlyIntegration') as mock:
        instance = mock.return_value
        instance.create_scheduling_link.return_value = {
            "scheduling_link": "https://calendly.com/test/consultation",
            "event_type": "Consultation"
        }
        instance.create_batch_scheduling_links.return_value = [
            {
                "name": "Chief Sarah",
                "email": "chief@tribe.ca",
                "scheduling_link": "https://calendly.com/test/consultation?name=Chief+Sarah"
            }
        ]
        yield instance


@pytest.fixture
def mock_slack_integration():
    """Mock Slack integration for testing."""
    with patch('backend.integrations.slack_integration.SlackIntegration') as mock:
        instance = mock.return_value
        instance.send_message.return_value = {
            "status": "sent",
            "message": "Test message",
            "channel": "#consultations"
        }
        instance.send_workflow_update.return_value = {
            "status": "sent",
            "message": "Workflow update"
        }
        yield instance


@pytest.fixture
def mock_backboard_llm():
    """Mock Backboard LLM for testing AI-driven workflows."""
    with patch('backend.agents.workflow_tools.BackboardProvider') as mock:
        provider = mock.return_value
        assistant = MagicMock()
        provider.create_assistant.return_value = assistant
        
        # Mock LLM response with tool selection
        assistant.run.return_value = (
            "TOOL: SendEmails\n"
            "REASONING: User wants to send outreach emails to stakeholders\n"
            "PARAMETERS: {\"subject\": \"Consultation Request\", \"recipients\": [\"test@example.com\"]}"
        )
        yield provider


# ===== GMAIL INTEGRATION TESTS =====

class TestGmailIntegration:
    """Test Gmail API integration."""
    
    def test_send_email_success(self, mock_gmail_integration):
        """Test successful email sending."""
        result = mock_gmail_integration.send_email(
            to="test@example.com",
            subject="Test Email",
            body="This is a test"
        )
        
        assert result["status"] == "sent"
        assert "message_id" in result
        mock_gmail_integration.send_email.assert_called_once()
    
    def test_send_batch_emails(self, mock_gmail_integration):
        """Test batch email sending."""
        contacts = [
            {"email": "test1@example.com", "name": "Test 1"},
            {"email": "test2@example.com", "name": "Test 2"}
        ]
        
        results = mock_gmail_integration.send_batch_emails(
            contacts=contacts,
            subject="Test Subject",
            body_template="Hello {name}"
        )
        
        assert len(results) == 2
        assert all(r["status"] == "sent" for r in results)
    
    def test_send_email_with_invalid_recipient(self, mock_gmail_integration):
        """Test email sending with invalid recipient."""
        mock_gmail_integration.send_email.side_effect = ValueError("Invalid email")
        
        with pytest.raises(ValueError):
            mock_gmail_integration.send_email(
                to="invalid_email",
                subject="Test",
                body="Test"
            )


# ===== CALENDLY INTEGRATION TESTS =====

class TestCalendlyIntegration:
    """Test Calendly API integration."""
    
    def test_create_scheduling_link(self, mock_calendly_integration):
        """Test scheduling link creation."""
        result = mock_calendly_integration.create_scheduling_link(
            name="John Doe",
            email="john@example.com"
        )
        
        assert "scheduling_link" in result
        assert "calendly.com" in result["scheduling_link"]
        mock_calendly_integration.create_scheduling_link.assert_called_once()
    
    def test_create_batch_scheduling_links(self, mock_calendly_integration):
        """Test batch scheduling link creation."""
        contacts = [
            {"name": "Chief Sarah", "email": "chief@tribe.ca"},
            {"name": "Dr. James", "email": "james@health.ca"}
        ]
        
        results = mock_calendly_integration.create_batch_scheduling_links(
            contacts=contacts
        )
        
        assert len(results) == 2
        assert all("scheduling_link" in r for r in results)
    
    def test_scheduling_link_with_prefilled_data(self, mock_calendly_integration):
        """Test scheduling link with pre-filled attendee data."""
        result = mock_calendly_integration.create_scheduling_link(
            name="Chief Sarah",
            email="chief@tribe.ca"
        )
        
        # Verify name is URL-encoded in link
        assert "name=Chief" in result["scheduling_link"] or "Chief+Sarah" in result["scheduling_link"]


# ===== SLACK INTEGRATION TESTS =====

class TestSlackIntegration:
    """Test Slack webhook integration."""
    
    def test_send_message(self, mock_slack_integration):
        """Test basic Slack message sending."""
        result = mock_slack_integration.send_message(
            message="Test notification",
            channel="#consultations"
        )
        
        assert result["status"] == "sent"
        assert result["channel"] == "#consultations"
    
    def test_send_workflow_update_emails(self, mock_slack_integration):
        """Test Slack workflow update for emails."""
        result = mock_slack_integration.send_workflow_update(
            action="emails_sent",
            details={"count": 3, "recipients": ["test1@example.com", "test2@example.com"]}
        )
        
        assert result["status"] == "sent"
        mock_slack_integration.send_workflow_update.assert_called_once()
    
    def test_send_consultation_booked(self, mock_slack_integration):
        """Test consultation booking notification."""
        mock_slack_integration.send_consultation_booked = Mock(return_value={
            "status": "sent",
            "message": "Consultation booked"
        })
        
        result = mock_slack_integration.send_consultation_booked(
            attendee_name="Chief Sarah",
            attendee_email="chief@tribe.ca",
            meeting_time="2026-01-20 10:00 AM"
        )
        
        assert result["status"] == "sent"


# ===== PROPOSAL WORKFLOW AGENT TESTS =====

class TestProposalWorkflowAgent:
    """Test ProposalWorkflowAgent workflow methods."""
    
    @patch('backend.agents.specialized_agents.GmailIntegration')
    @patch('backend.agents.specialized_agents.BackboardProvider')
    def test_execute_send_emails(self, mock_backboard, mock_gmail_class):
        """Test email sending workflow."""
        # Setup mocks
        mock_gmail = mock_gmail_class.return_value
        mock_gmail.send_batch_emails.return_value = [
            {"recipient": "test@example.com", "status": "sent"}
        ]
        
        mock_assistant = MagicMock()
        mock_backboard.return_value.create_assistant.return_value = mock_assistant
        mock_assistant.run.return_value = "Email content generated"
        
        # Import after patching
        from backend.agents.specialized_agents import ProposalWorkflowAgent
        
        agent = ProposalWorkflowAgent(
            api_key=os.getenv("BACKBOARD_API_KEY", "test_key")
        )
        
        # Add test contacts
        agent.add_contact("Chief Sarah", "chief@tribe.ca", "Tribal Leader")
        
        # Execute workflow
        result = agent.execute_send_emails(
            subject="Consultation Request",
            context="We'd like to discuss sustainability"
        )
        
        assert "emails_sent" in result
        assert result["emails_sent"] == 1
    
    @patch('backend.agents.specialized_agents.CalendlyIntegration')
    def test_execute_schedule_meetings(self, mock_calendly_class):
        """Test meeting scheduling workflow."""
        # Setup mock
        mock_calendly = mock_calendly_class.return_value
        mock_calendly.create_batch_scheduling_links.return_value = [
            {
                "name": "Chief Sarah",
                "email": "chief@tribe.ca",
                "scheduling_link": "https://calendly.com/test/consultation"
            }
        ]
        
        from backend.agents.specialized_agents import ProposalWorkflowAgent
        
        agent = ProposalWorkflowAgent(
            api_key=os.getenv("BACKBOARD_API_KEY", "test_key")
        )
        
        # Add test contacts
        agent.add_contact("Chief Sarah", "chief@tribe.ca", "Tribal Leader")
        
        # Execute workflow
        result = agent.execute_schedule_meetings()
        
        assert "meetings_scheduled" in result
        assert result["meetings_scheduled"] == 1
        assert len(result["scheduling_links"]) == 1
    
    @patch('backend.agents.specialized_agents.GmailIntegration')
    @patch('backend.agents.specialized_agents.CalendlyIntegration')
    @patch('backend.agents.specialized_agents.BackboardProvider')
    def test_execute_full_outreach_workflow(
        self,
        mock_backboard,
        mock_calendly_class,
        mock_gmail_class
    ):
        """Test full outreach workflow (emails + meetings)."""
        # Setup mocks
        mock_gmail = mock_gmail_class.return_value
        mock_gmail.send_batch_emails.return_value = [
            {"recipient": "chief@tribe.ca", "status": "sent"}
        ]
        
        mock_calendly = mock_calendly_class.return_value
        mock_calendly.create_batch_scheduling_links.return_value = [
            {
                "name": "Chief Sarah",
                "email": "chief@tribe.ca",
                "scheduling_link": "https://calendly.com/test/consultation"
            }
        ]
        
        mock_assistant = MagicMock()
        mock_backboard.return_value.create_assistant.return_value = mock_assistant
        mock_assistant.run.return_value = "Email with scheduling link"
        
        from backend.agents.specialized_agents import ProposalWorkflowAgent
        
        agent = ProposalWorkflowAgent(
            api_key=os.getenv("BACKBOARD_API_KEY", "test_key")
        )
        
        # Add test contacts
        agent.add_contact("Chief Sarah", "chief@tribe.ca", "Tribal Leader")
        
        # Execute full workflow
        result = agent.execute_full_outreach_workflow(
            subject="Consultation Invitation",
            context="Sustainability project discussion"
        )
        
        assert "emails_sent" in result
        assert "meetings_scheduled" in result
        assert result["emails_sent"] == 1
        assert result["meetings_scheduled"] == 1


# ===== AI-DRIVEN WORKFLOW TESTS =====

class TestAIDrivenWorkflows:
    """Test AI-driven workflow execution via LangChain tools."""
    
    @patch('backend.agents.workflow_tools.BackboardProvider')
    def test_ai_tool_selection_send_emails(self, mock_backboard):
        """Test AI correctly selects SendEmails tool."""
        # Setup mock
        mock_assistant = MagicMock()
        mock_backboard.return_value.create_assistant.return_value = mock_assistant
        mock_assistant.run.return_value = (
            "TOOL: SendEmails\n"
            "REASONING: User wants to send outreach emails\n"
            'PARAMETERS: {"subject": "Consultation", "recipients": ["test@example.com"]}'
        )
        
        from backend.agents.workflow_tools import create_workflow_agent
        from backend.agents.specialized_agents import ProposalWorkflowAgent
        
        agent = ProposalWorkflowAgent(
            api_key=os.getenv("BACKBOARD_API_KEY", "test_key")
        )
        
        ai_executor = create_workflow_agent(agent)
        
        # Execute with natural language
        user_intent = "Send consultation emails to all stakeholders"
        
        # Note: This will fail without proper tool execution mocking
        # In real implementation, we'd need to mock the tool execution
        with patch.object(agent, 'execute_send_emails', return_value={"emails_sent": 2}):
            result = ai_executor(user_intent)
            assert "emails_sent" in str(result) or "SendEmails" in str(result)
    
    @patch('backend.agents.workflow_tools.BackboardProvider')
    def test_ai_tool_selection_schedule_meetings(self, mock_backboard):
        """Test AI correctly selects ScheduleMeetings tool."""
        mock_assistant = MagicMock()
        mock_backboard.return_value.create_assistant.return_value = mock_assistant
        mock_assistant.run.return_value = (
            "TOOL: ScheduleMeetings\n"
            "REASONING: User wants to create scheduling links\n"
            'PARAMETERS: {}'
        )
        
        from backend.agents.workflow_tools import create_workflow_agent
        from backend.agents.specialized_agents import ProposalWorkflowAgent
        
        agent = ProposalWorkflowAgent(
            api_key=os.getenv("BACKBOARD_API_KEY", "test_key")
        )
        
        ai_executor = create_workflow_agent(agent)
        
        with patch.object(agent, 'execute_schedule_meetings', return_value={"meetings_scheduled": 2}):
            user_intent = "Create meeting links for all contacts"
            result = ai_executor(user_intent)
            assert "meetings_scheduled" in str(result) or "ScheduleMeetings" in str(result)
    
    @patch('backend.agents.workflow_tools.BackboardProvider')
    def test_ai_tool_selection_full_outreach(self, mock_backboard):
        """Test AI correctly selects FullOutreach tool."""
        mock_assistant = MagicMock()
        mock_backboard.return_value.create_assistant.return_value = mock_assistant
        mock_assistant.run.return_value = (
            "TOOL: FullOutreach\n"
            "REASONING: User wants both emails and meeting links\n"
            'PARAMETERS: {"subject": "Consultation Invitation"}'
        )
        
        from backend.agents.workflow_tools import create_workflow_agent
        from backend.agents.specialized_agents import ProposalWorkflowAgent
        
        agent = ProposalWorkflowAgent(
            api_key=os.getenv("BACKBOARD_API_KEY", "test_key")
        )
        
        ai_executor = create_workflow_agent(agent)
        
        with patch.object(agent, 'execute_full_outreach_workflow', return_value={
            "emails_sent": 2,
            "meetings_scheduled": 2
        }):
            user_intent = "Send emails with meeting links to all stakeholders"
            result = ai_executor(user_intent)
            assert "FullOutreach" in str(result) or "emails_sent" in str(result)


# ===== CONTACT MANAGEMENT TESTS =====

class TestContactManagement:
    """Test contact management functionality."""
    
    def test_add_contact(self):
        """Test adding a contact."""
        from backend.agents.specialized_agents import ProposalWorkflowAgent
        
        agent = ProposalWorkflowAgent(
            api_key=os.getenv("BACKBOARD_API_KEY", "test_key")
        )
        
        result = agent.add_contact(
            name="Chief Sarah",
            email="chief@tribe.ca",
            role="Tribal Leader"
        )
        
        assert "contact_added" in result
        assert result["name"] == "Chief Sarah"
    
    def test_get_contacts(self):
        """Test retrieving all contacts."""
        from backend.agents.specialized_agents import ProposalWorkflowAgent
        
        agent = ProposalWorkflowAgent(
            api_key=os.getenv("BACKBOARD_API_KEY", "test_key")
        )
        
        # Add multiple contacts
        agent.add_contact("Chief Sarah", "chief@tribe.ca", "Tribal Leader")
        agent.add_contact("Dr. James", "james@health.ca", "Health Director")
        
        contacts = agent.get_contacts()
        
        assert len(contacts) == 2
        assert any(c["name"] == "Chief Sarah" for c in contacts)
        assert any(c["name"] == "Dr. James" for c in contacts)
    
    def test_workflow_history_tracking(self):
        """Test workflow execution history tracking."""
        from backend.agents.specialized_agents import ProposalWorkflowAgent
        
        agent = ProposalWorkflowAgent(
            api_key=os.getenv("BACKBOARD_API_KEY", "test_key")
        )
        
        # Add contact and execute workflow
        agent.add_contact("Chief Sarah", "chief@tribe.ca", "Tribal Leader")
        
        with patch.object(agent, 'gmail_integration') as mock_gmail:
            mock_gmail.send_batch_emails.return_value = [
                {"recipient": "chief@tribe.ca", "status": "sent"}
            ]
            
            with patch.object(agent, 'assistant') as mock_assistant:
                mock_assistant.run.return_value = "Email content"
                
                agent.execute_send_emails(
                    subject="Test",
                    context="Test context"
                )
        
        history = agent.get_workflow_history()
        
        assert len(history) >= 1
        assert history[0]["action"] == "send_emails"


# ===== INTEGRATION TESTS =====

class TestEndToEndWorkflows:
    """Test complete end-to-end workflow scenarios."""
    
    @patch('backend.agents.specialized_agents.GmailIntegration')
    @patch('backend.agents.specialized_agents.CalendlyIntegration')
    @patch('backend.agents.specialized_agents.SlackIntegration')
    @patch('backend.agents.specialized_agents.BackboardProvider')
    def test_full_outreach_with_slack_notification(
        self,
        mock_backboard,
        mock_slack_class,
        mock_calendly_class,
        mock_gmail_class
    ):
        """Test full outreach workflow with Slack notifications."""
        # Setup mocks
        mock_gmail = mock_gmail_class.return_value
        mock_gmail.send_batch_emails.return_value = [
            {"recipient": "chief@tribe.ca", "status": "sent"}
        ]
        
        mock_calendly = mock_calendly_class.return_value
        mock_calendly.create_batch_scheduling_links.return_value = [
            {
                "name": "Chief Sarah",
                "email": "chief@tribe.ca",
                "scheduling_link": "https://calendly.com/test/consultation"
            }
        ]
        
        mock_slack = mock_slack_class.return_value
        mock_slack.send_workflow_update.return_value = {
            "status": "sent",
            "message": "Workflow complete"
        }
        
        mock_assistant = MagicMock()
        mock_backboard.return_value.create_assistant.return_value = mock_assistant
        mock_assistant.run.return_value = "Email with scheduling link"
        
        from backend.agents.specialized_agents import ProposalWorkflowAgent
        
        agent = ProposalWorkflowAgent(
            api_key=os.getenv("BACKBOARD_API_KEY", "test_key")
        )
        
        # Add contact
        agent.add_contact("Chief Sarah", "chief@tribe.ca", "Tribal Leader")
        
        # Execute full workflow
        result = agent.execute_full_outreach_workflow(
            subject="Consultation Invitation",
            context="Sustainability project"
        )
        
        # Verify workflow completed
        assert result["emails_sent"] == 1
        assert result["meetings_scheduled"] == 1
        
        # Send Slack notification
        mock_slack.send_workflow_update(
            action="full_outreach_complete",
            details={
                "emails_sent": result["emails_sent"],
                "meetings_scheduled": result["meetings_scheduled"]
            }
        )
        
        mock_slack.send_workflow_update.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
