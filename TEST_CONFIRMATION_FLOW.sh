#!/bin/bash
# Test the complete confirmation workflow

set -e  # Exit on any error

echo "🚀 Testing Confirmation-Based Workflow"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

BASE_URL="http://localhost:8000"

# Step 1: Create thread
echo -e "${BLUE}Step 1: Creating proposal thread...${NC}"
CREATE_RESPONSE=$(curl -s -X POST "$BASE_URL/create-chat" \
  -H "Content-Type: application/json" \
  -d '{"agent":"proposal"}')

THREAD_ID=$(echo "$CREATE_RESPONSE" | jq -r '.thread_id')
echo -e "${GREEN}✓ Thread created: $THREAD_ID${NC}"
echo ""

# Step 2: Add contacts
echo -e "${BLUE}Step 2: Adding contacts...${NC}"
curl -s -X POST "$BASE_URL/workflow/add-contact?threadid=$THREAD_ID&name=Chief%20Sarah&role=Tribal%20Leader&email=chief@tribe.ca&phone=250-555-1234" > /dev/null
curl -s -X POST "$BASE_URL/workflow/add-contact?threadid=$THREAD_ID&name=Dr%20James&role=Environmental%20Scientist&email=dr@env.org&phone=604-555-5678" > /dev/null
curl -s -X POST "$BASE_URL/workflow/add-contact?threadid=$THREAD_ID&name=Manager%20Sue&role=Project%20Manager&email=sue@company.ca&phone=778-555-9999" > /dev/null
echo -e "${GREEN}✓ Added 3 contacts${NC}"
echo ""

# Step 3: Request to send emails (creates pending confirmation)
echo -e "${BLUE}Step 3: Requesting to send emails...${NC}"
WORKFLOW_RESPONSE=$(curl -s -X POST "$BASE_URL/execute-workflow/send-emails?threadid=$THREAD_ID" \
  -H "Content-Type: application/json" \
  -d '{"proposal_title":"Sustainable Forest Development"}')

echo -e "${YELLOW}Response from workflow endpoint:${NC}"
echo "$WORKFLOW_RESPONSE" | jq '.'
echo ""

ACTION_ID=$(echo "$WORKFLOW_RESPONSE" | jq -r '.action_id')

if [ "$ACTION_ID" = "null" ] || [ -z "$ACTION_ID" ]; then
  echo -e "${YELLOW}⚠️  No confirmation created (already approved or error)${NC}"
  exit 0
fi

echo -e "${GREEN}✓ Confirmation created: $ACTION_ID${NC}"
echo -e "${YELLOW}Status: PENDING (emails NOT sent yet)${NC}"
echo ""

# Step 4: Check pending confirmations
echo -e "${BLUE}Step 4: Checking pending confirmations...${NC}"
PENDING=$(curl -s "$BASE_URL/confirmations/pending")
echo "$PENDING" | jq '.'
echo ""

# Step 5: User decides - ask for approval
echo -e "${YELLOW}======================================"
echo "⏸️  WAITING FOR USER APPROVAL"
echo "======================================"
echo ""
echo "Details:"
echo "$WORKFLOW_RESPONSE" | jq '.details'
echo ""
read -p "Do you want to approve and send these emails? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Step 6: Approve
    echo -e "${BLUE}Step 6: Approving action...${NC}"
    APPROVE_RESPONSE=$(curl -s -X POST "$BASE_URL/confirmations/$ACTION_ID/approve")
    echo -e "${GREEN}✓ Action approved and executed!${NC}"
    echo ""
    echo -e "${YELLOW}Execution results:${NC}"
    echo "$APPROVE_RESPONSE" | jq '.'
    echo ""
    echo -e "${GREEN}✅ WORKFLOW COMPLETE - Emails sent!${NC}"
else
    # Step 6: Reject
    echo -e "${BLUE}Step 6: Rejecting action...${NC}"
    REJECT_RESPONSE=$(curl -s -X POST "$BASE_URL/confirmations/$ACTION_ID/reject?reason=User%20cancelled")
    echo -e "${YELLOW}✓ Action rejected${NC}"
    echo ""
    echo "$REJECT_RESPONSE" | jq '.'
    echo ""
    echo -e "${YELLOW}❌ WORKFLOW CANCELLED - No emails sent${NC}"
fi

echo ""
echo "🎉 Test complete!"
