# Workflow Testing Guide

## Overview
This guide covers testing for all workflow integrations: Gmail, Calendly, Slack, and AI-driven execution.

---

## Setup

### 1. Install Test Dependencies
```bash
cd backend
pip install -r requirements-test.txt
```

### 2. Set Environment Variables
Create `.env.test` file:
```bash
BACKBOARD_API_KEY=your_backboard_key
GOOGLE_API_MAP_KEY=your_google_key
CALENDLY_API_KEY=your_calendly_key
SLACK_WEBHOOK_URL=your_slack_webhook
```

---

## Running Tests

### Run All Tests
```bash
pytest backend/tests/test_workflows.py -v
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest backend/tests/test_workflows.py -m unit

# Integration tests only
pytest backend/tests/test_workflows.py -m integration

# AI-related tests
pytest backend/tests/test_workflows.py -m ai
```

### Run Specific Test Classes
```bash
# Gmail tests
pytest backend/tests/test_workflows.py::TestGmailIntegration -v

# Calendly tests
pytest backend/tests/test_workflows.py::TestCalendlyIntegration -v

# Slack tests
pytest backend/tests/test_workflows.py::TestSlackIntegration -v

# AI workflow tests
pytest backend/tests/test_workflows.py::TestAIDrivenWorkflows -v
```

### Run Specific Test Methods
```bash
# Test email sending
pytest backend/tests/test_workflows.py::TestGmailIntegration::test_send_email_success -v

# Test AI tool selection
pytest backend/tests/test_workflows.py::TestAIDrivenWorkflows::test_ai_tool_selection_send_emails -v
```

### Run with Coverage
```bash
pytest backend/tests/test_workflows.py --cov=backend --cov-report=html
# View coverage report: open htmlcov/index.html
```

---

## Test Structure

### 1. Gmail Integration Tests (`TestGmailIntegration`)
- ✓ `test_send_email_success`: Verify single email sending
- ✓ `test_send_batch_emails`: Verify batch email sending
- ✓ `test_send_email_with_invalid_recipient`: Error handling

**Example:**
```python
def test_send_email_success(mock_gmail_integration):
    result = mock_gmail_integration.send_email(
        to="test@example.com",
        subject="Test Email",
        body="Test body"
    )
    assert result["status"] == "sent"
```

### 2. Calendly Integration Tests (`TestCalendlyIntegration`)
- ✓ `test_create_scheduling_link`: Single link creation
- ✓ `test_create_batch_scheduling_links`: Multiple links
- ✓ `test_scheduling_link_with_prefilled_data`: URL encoding verification

**Example:**
```python
def test_create_scheduling_link(mock_calendly_integration):
    result = mock_calendly_integration.create_scheduling_link(
        name="John Doe",
        email="john@example.com"
    )
    assert "calendly.com" in result["scheduling_link"]
```

### 3. Slack Integration Tests (`TestSlackIntegration`)
- ✓ `test_send_message`: Basic message sending
- ✓ `test_send_workflow_update_emails`: Workflow notifications
- ✓ `test_send_consultation_booked`: Meeting booking alerts

**Example:**
```python
def test_send_workflow_update_emails(mock_slack_integration):
    result = mock_slack_integration.send_workflow_update(
        action="emails_sent",
        details={"count": 3, "recipients": ["test@example.com"]}
    )
    assert result["status"] == "sent"
```

### 4. ProposalWorkflowAgent Tests (`TestProposalWorkflowAgent`)
- ✓ `test_execute_send_emails`: Email workflow execution
- ✓ `test_execute_schedule_meetings`: Meeting scheduling workflow
- ✓ `test_execute_full_outreach_workflow`: Combined email + meetings

**Example:**
```python
@patch('backend.agents.specialized_agents.GmailIntegration')
def test_execute_send_emails(mock_gmail_class):
    agent = ProposalWorkflowAgent(api_key="test_key")
    agent.add_contact("Test", "test@example.com", "Role")
    
    result = agent.execute_send_emails(
        subject="Test Subject",
        context="Test context"
    )
    
    assert "emails_sent" in result
```

### 5. AI-Driven Workflow Tests (`TestAIDrivenWorkflows`)
- ✓ `test_ai_tool_selection_send_emails`: AI chooses SendEmails tool
- ✓ `test_ai_tool_selection_schedule_meetings`: AI chooses ScheduleMeetings
- ✓ `test_ai_tool_selection_full_outreach`: AI chooses FullOutreach

**Example:**
```python
@patch('backend.agents.workflow_tools.BackboardProvider')
def test_ai_tool_selection_send_emails(mock_backboard):
    mock_assistant = MagicMock()
    mock_assistant.run.return_value = (
        "TOOL: SendEmails\n"
        "REASONING: User wants to send emails\n"
        'PARAMETERS: {"subject": "Test"}'
    )
    
    ai_executor = create_workflow_agent(agent)
    result = ai_executor("Send emails to all stakeholders")
    
    assert "SendEmails" in str(result)
```

### 6. Contact Management Tests (`TestContactManagement`)
- ✓ `test_add_contact`: Add stakeholder contact
- ✓ `test_get_contacts`: Retrieve all contacts
- ✓ `test_workflow_history_tracking`: Audit trail verification

### 7. End-to-End Tests (`TestEndToEndWorkflows`)
- ✓ `test_full_outreach_with_slack_notification`: Complete workflow with notifications

---

## Mocking Strategy

### Mock Fixtures
All external API calls are mocked using pytest fixtures:

```python
@pytest.fixture
def mock_gmail_integration():
    """Mock Gmail API calls."""
    with patch('backend.integrations.gmail_integration.GmailIntegration') as mock:
        instance = mock.return_value
        instance.send_email.return_value = {"status": "sent"}
        yield instance
```

### Backboard LLM Mock
AI responses are mocked to test tool selection:

```python
@pytest.fixture
def mock_backboard_llm():
    """Mock Backboard LLM responses."""
    with patch('backend.agents.workflow_tools.BackboardProvider') as mock:
        assistant = MagicMock()
        assistant.run.return_value = (
            "TOOL: SendEmails\n"
            "REASONING: ...\n"
            "PARAMETERS: {...}"
        )
        yield assistant
```

---

## Test Markers

### Mark Tests for Selective Running
```python
@pytest.mark.unit
def test_add_contact():
    """Unit test for contact addition."""
    pass

@pytest.mark.integration
def test_full_outreach_workflow():
    """Integration test for complete workflow."""
    pass

@pytest.mark.ai
def test_ai_tool_selection():
    """AI-driven workflow test."""
    pass

@pytest.mark.slow
def test_long_running_workflow():
    """Slow test that takes >5 seconds."""
    pass
```

### Run Tests by Marker
```bash
pytest -m unit        # Only unit tests
pytest -m integration # Only integration tests
pytest -m "not slow"  # Skip slow tests
```

---

## Common Test Scenarios

### 1. Test Email Sending Workflow
```bash
# Test single email
pytest backend/tests/test_workflows.py::TestGmailIntegration::test_send_email_success -v

# Test batch emails
pytest backend/tests/test_workflows.py::TestGmailIntegration::test_send_batch_emails -v
```

### 2. Test Meeting Scheduling
```bash
pytest backend/tests/test_workflows.py::TestCalendlyIntegration -v
```

### 3. Test AI Workflow Selection
```bash
pytest backend/tests/test_workflows.py::TestAIDrivenWorkflows -v
```

### 4. Test End-to-End Workflows
```bash
pytest backend/tests/test_workflows.py::TestEndToEndWorkflows -v
```

---

## Debugging Failed Tests

### Verbose Output
```bash
pytest backend/tests/test_workflows.py -vv
```

### Show Print Statements
```bash
pytest backend/tests/test_workflows.py -s
```

### Show Full Traceback
```bash
pytest backend/tests/test_workflows.py --tb=long
```

### Drop into Debugger on Failure
```bash
pytest backend/tests/test_workflows.py --pdb
```

### Run Last Failed Tests
```bash
pytest backend/tests/test_workflows.py --lf
```

---

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Test Workflows
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r backend/requirements-test.txt
      
      - name: Run tests
        env:
          BACKBOARD_API_KEY: ${{ secrets.BACKBOARD_API_KEY }}
        run: |
          pytest backend/tests/test_workflows.py -v --cov=backend
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Test Coverage Goals

### Current Coverage
Run coverage report:
```bash
pytest backend/tests/test_workflows.py --cov=backend --cov-report=term-missing
```

### Target Coverage
- **Gmail Integration**: 100% (all methods tested)
- **Calendly Integration**: 100% (all methods tested)
- **Slack Integration**: 100% (all methods tested)
- **ProposalWorkflowAgent**: 90%+ (core workflows tested)
- **AI Workflow Tools**: 85%+ (tool selection tested)

---

## Manual Testing API Endpoints

### Test Send Emails Workflow
```bash
curl -X POST http://localhost:8000/execute-workflow/send-emails \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Test Email",
    "context": "Testing email workflow"
  }'
```

### Test Schedule Meetings Workflow
```bash
curl -X POST http://localhost:8000/execute-workflow/schedule-meetings
```

### Test AI-Driven Workflow
```bash
curl -X POST http://localhost:8000/execute-workflow/ai-driven \
  -H "Content-Type: application/json" \
  -d '{
    "user_intent": "Send consultation emails to all stakeholders"
  }'
```

### Test Add Contact
```bash
curl -X POST http://localhost:8000/workflow/add-contact \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Chief Sarah",
    "email": "chief@tribe.ca",
    "role": "Tribal Leader"
  }'
```

### Test Get Contacts
```bash
curl http://localhost:8000/workflow/contacts
```

### Test Workflow History
```bash
curl http://localhost:8000/workflow/history
```

---

## Troubleshooting

### Issue: Import Errors
**Solution**: Ensure `backend/` is in PYTHONPATH:
```bash
export PYTHONPATH="${PYTHONPATH}:/Users/nuthanantharmarajah/uofthacks-2026"
```

### Issue: Mock Not Working
**Solution**: Verify patch path matches actual import:
```python
# If agent imports: from integrations.gmail_integration import GmailIntegration
# Then patch: 'backend.agents.specialized_agents.GmailIntegration'
```

### Issue: Environment Variables Not Set
**Solution**: Load from `.env.test`:
```bash
export $(cat .env.test | xargs)
pytest backend/tests/test_workflows.py
```

### Issue: Backboard API Errors
**Solution**: Mock the BackboardProvider:
```python
@patch('backend.agents.workflow_tools.BackboardProvider')
def test_workflow(mock_backboard):
    # Test implementation
    pass
```

---

## Best Practices

1. **Isolate Tests**: Each test should be independent
2. **Mock External APIs**: Never call real APIs in tests
3. **Test Edge Cases**: Invalid inputs, empty lists, null values
4. **Use Fixtures**: Reuse mock setup across tests
5. **Mark Tests**: Use markers for test categorization
6. **Coverage Goals**: Aim for 90%+ coverage on critical paths
7. **Fast Tests**: Keep test suite under 30 seconds
8. **Clear Assertions**: Use descriptive assertion messages

---

## Next Steps

1. ✅ Install test dependencies: `pip install -r requirements-test.txt`
2. ✅ Run all tests: `pytest backend/tests/test_workflows.py -v`
3. ✅ Check coverage: `pytest --cov=backend --cov-report=html`
4. ✅ Review failing tests and fix issues
5. ✅ Add more test cases for edge cases
6. ✅ Set up CI/CD pipeline for automated testing
