#!/bin/bash
# Test Runner Script - Quick Reference for Workflow Testing

set -e

PROJECT_ROOT=$(cd "$(dirname "$0")" && pwd)
BACKEND_DIR="$PROJECT_ROOT/backend"

echo "🧪 Workflow Test Runner"
echo "======================="
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found. Installing test dependencies..."
    pip install -r "$BACKEND_DIR/requirements-test.txt"
fi

cd "$BACKEND_DIR"

# Parse command-line arguments
TEST_TYPE="${1:-all}"

case $TEST_TYPE in
    "all")
        echo "▶️  Running all tests..."
        pytest tests/test_workflows.py -v
        ;;
    
    "gmail")
        echo "▶️  Running Gmail integration tests..."
        pytest tests/test_workflows.py::TestGmailIntegration -v
        ;;
    
    "calendly")
        echo "▶️  Running Calendly integration tests..."
        pytest tests/test_workflows.py::TestCalendlyIntegration -v
        ;;
    
    "slack")
        echo "▶️  Running Slack integration tests..."
        pytest tests/test_workflows.py::TestSlackIntegration -v
        ;;
    
    "agent")
        echo "▶️  Running ProposalWorkflowAgent tests..."
        pytest tests/test_workflows.py::TestProposalWorkflowAgent -v
        ;;
    
    "ai")
        echo "▶️  Running AI-driven workflow tests..."
        pytest tests/test_workflows.py::TestAIDrivenWorkflows -v
        ;;
    
    "unit")
        echo "▶️  Running unit tests (non-integration)..."
        pytest tests/test_workflows.py -m unit -v
        ;;
    
    "integration")
        echo "▶️  Running integration tests..."
        pytest tests/test_workflows.py -m integration -v
        ;;
    
    "coverage")
        echo "▶️  Running tests with coverage report..."
        pytest tests/test_workflows.py --cov=. --cov-report=html
        echo "📊 Coverage report generated: htmlcov/index.html"
        ;;
    
    "fast")
        echo "▶️  Running fast tests (skip slow tests)..."
        pytest tests/test_workflows.py -m "not slow" -v
        ;;
    
    "help")
        cat << EOF

Usage: ./run_tests.sh [TYPE]

Available Test Types:
  all          - Run all tests (19 total)
  gmail        - Gmail integration tests only (3 tests)
  calendly     - Calendly integration tests only (3 tests)
  slack        - Slack integration tests only (3 tests)
  agent        - ProposalWorkflowAgent tests only (3 tests)
  ai           - AI-driven workflow tests only (3 tests)
  unit         - All unit tests
  integration  - End-to-end integration tests
  coverage     - Run tests with coverage report
  fast         - Skip slow tests (faster execution)
  help         - Show this help message

Examples:
  ./run_tests.sh              # Run all tests (default)
  ./run_tests.sh gmail        # Test Gmail integration
  ./run_tests.sh coverage     # Generate coverage report
  ./run_tests.sh fast         # Quick test run (no slow tests)

EOF
        ;;
    
    *)
        echo "❌ Unknown test type: $TEST_TYPE"
        echo "Run './run_tests.sh help' for usage information"
        exit 1
        ;;
esac

echo ""
echo "✅ Test run complete!"
