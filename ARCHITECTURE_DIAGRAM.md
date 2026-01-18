# Email Personalization System - Visual Architecture

## System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        USER ENTERS CHAT MESSAGE                          │
│                                                                           │
│  "add CFO Jane at jane@bank.com for investment strategy and funding"    │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    COMMAND PARSER (parseAndApplyChatCommand)            │
│                                                                           │
│  Step 1: Match command pattern                                          │
│  - Detect: "add" + ("contact" | "stakeholder")                          │
│  - Result: ✅ Add contact command recognized                           │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     EMAIL & CONTACT EXTRACTION                           │
│                                                                           │
│  Extract from message:                                                   │
│  - Email: jane@bank.com ✅                                              │
│  - Name: Jane ✅                                                         │
│  - Role: CFO ✅                                                          │
│  - Full message: ENTIRE INPUT ✅                                        │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    CREATE CONTACT WITH CONTEXT                           │
│                                                                           │
│  const newContact: ProposalContact = {                                   │
│    role: "Jane",                                                         │
│    reason: "Added via chat",                                             │
│    email: "jane@bank.com",                                              │
│    context: "add CFO Jane at jane@bank.com for investment strategy..."  │
│    ────────────────────────────────────────────────────                 │
│    (NEW: Stores full message for context extraction)                    │
│  };                                                                       │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              generateRoleSpecificEmail(role, context, location)         │
│                                                                           │
│  Step 1: Extract meaningful details from context                        │
│  ────────────────────────────────────────────────                        │
│  const forMatch = /for\s+([^,]+?)(?:\s+at\s+|$)/i                      │
│  → Matches: "for investment strategy and funding"                       │
│  → Extracts: "investment strategy and funding"                          │
│                                                                           │
│  Step 2: Clean email addresses from context                             │
│  ──────────────────────────────────────────                              │
│  contextDetails = "investment strategy and funding"                     │
│     (emails removed)                                                     │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    ROLE-BASED TEMPLATE SELECTION                         │
│                                                                           │
│  roleLower.includes('financial') → TRUE                                 │
│                                                                           │
│  Subject Template:                                                       │
│  "Investment & Budget Planning - ${locationName} Development Initiative"│
│                                                                           │
│  Body Template:                                                          │
│  "We are developing a sustainable community project at ${locationName}  │
│   with a focus on ${contextDetails}..."                                 │
│                                                                           │
│  ${contextDetails} substituted with:                                    │
│  "investment strategy and funding"                                      │
│                                                                           │
│  Result:                                                                 │
│  "We are developing a sustainable community project at Toronto           │
│   with a focus on investment strategy and funding..."                   │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   EMAIL DRAFT CREATED & STORED                           │
│                                                                           │
│  {                                                                        │
│    to: "jane@bank.com",                                                 │
│    subject: "Investment & Budget Planning - Toronto Development...",    │
│    body: "Dear Jane,\n\n                                                │
│           We are developing a sustainable community project at Toronto  │
│           with a focus on investment strategy and funding and require   │
│           financial expertise for budgeting, funding strategies, and    │
│           investment opportunities.\n\n                                 │
│           **Project Financial Considerations:**                         │
│           • Budget allocation and cost-benefit analysis for investment  │
│             strategy and funding..."                                    │
│  }                                                                        │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STATE UPDATED SYNCHRONOUSLY                           │
│                                                                           │
│  setEditData(newEditData)                                                │
│                                                                           │
│  UI shows:                                                               │
│  📧 1 Email Draft (personalized with investment focus)                   │
│  👥 1 Contact (Jane, Financial)                                         │
│  📧 Subject preview shows "Investment & Budget Planning"                │
│  📧 Body preview shows investment/funding focus                         │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      WORKFLOW EXECUTION READY                            │
│                                                                           │
│  When user clicks "Execute Workflow":                                    │
│                                                                           │
│  Frontend sends to Backend:                                              │
│  - email_subjects: ["Investment & Budget Planning - Toronto..."]        │
│  - email_bodies: ["Dear Jane,\nWe are developing... investment..."]    │
│  - contacts: [{ role: "Jane", email: "jane@bank.com", ... }]           │
│                                                                           │
│  Backend:                                                                │
│  - Receives personalized emails (NOT generic)                           │
│  - Uses index-based matching                                             │
│  - Sends unique email to each contact                                    │
│  - Each email matches their specific purpose                            │
└─────────────────────────────────────────────────────────────────────────┘
```

## Before vs After Comparison

### BEFORE: Generic Email (❌)
```
Input Flow:
User: "add Jane at jane@bank.com for investment strategy"
  ↓
Hardcoded: 'Strategic consultation and partnership'
  ↓
Result: Generic email sent

Input Flow:
User: "add John at john@firm.com for legal review"
  ↓
Hardcoded: 'Strategic consultation and partnership'
  ↓
Result: SAME generic email sent

Problem: Jane and John get IDENTICAL emails ❌
```

### AFTER: Personalized Email (✅)
```
Input Flow:
User: "add Jane at jane@bank.com for investment strategy"
  ↓
Extracted: "investment strategy"
  ↓
Generated: "Investment & Budget Planning" email
  ↓
Result: Email about investment/funding

Input Flow:
User: "add John at john@firm.com for legal review"
  ↓
Extracted: "legal review"
  ↓
Generated: "Legal Review & Compliance" email
  ↓
Result: Email about contracts/compliance

Result: Jane and John get DIFFERENT emails ✅
```

## Data Transformation at Each Step

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                           │
│  Raw Input (String):                                                     │
│  "add CFO Michael at michael@bank.com for investment strategy"          │
│                                                                           │
│                              ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Parsed Data (Object)                                             │  │
│  │ {                                                                │  │
│  │   name: "Michael",                                              │  │
│  │   email: "michael@bank.com",                                    │  │
│  │   context: "add CFO Michael at michael@bank.com for investment  │  │
│  │            strategy" ← FULL MESSAGE STORED                      │  │
│  │ }                                                                │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Contact Created (TypeScript)                                     │  │
│  │ {                                                                │  │
│  │   role: "Michael",                                              │  │
│  │   reason: "Added via chat",                                     │  │
│  │   email: "michael@bank.com",                                    │  │
│  │   context: "add CFO Michael at michael@bank.com for investment  │  │
│  │            strategy" ← STORED IN CONTACT                       │  │
│  │ }                                                                │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Context Extracted (Regex)                                        │  │
│  │ {                                                                │  │
│  │   contextDetails: "investment strategy" ← EXTRACTED            │  │
│  │ }                                                                │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Email Generated (Template)                                       │  │
│  │ Subject: "Investment & Budget Planning - Toronto Development..." │  │
│  │ Body: "...with a focus on investment strategy..."              │  │
│  │   (Where ${contextDetails} = "investment strategy")            │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Backend Sends (Email)                                            │  │
│  │ To: michael@bank.com                                             │  │
│  │ Subject: Investment & Budget Planning - Toronto Development...  │  │
│  │ Body: "Dear Michael,\nWe are developing a sustainable community │  │
│  │        project at Toronto with a focus on investment strategy.. │  │
│  │                                                                  │  │
│  │        **Project Financial Considerations:**                    │  │
│  │        • Budget allocation and cost-benefit analysis for        │  │
│  │          investment strategy..."                                │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Michael Receives (Email)                                         │  │
│  │                                                                  │  │
│  │ From: proposal@[company]                                        │  │
│  │ To: michael@bank.com                                             │  │
│  │                                                                  │  │
│  │ Subject: Investment & Budget Planning - Toronto Development    │  │
│  │          Initiative                                              │  │
│  │                                                                  │  │
│  │ Body: Email specifically about investment and budgeting, NOT    │  │
│  │       generic consultation message ✅                           │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

## Pattern Extraction Examples

```
User Input                                     Context Extracted
───────────────────────────────────────────────────────────────────────
"for investment strategy"                  →  "investment strategy"
"for budget planning"                      →  "budget planning"
"for contract review"                      →  "contract review"
"about carbon reduction"                   →  "carbon reduction"
"regarding legal compliance"               →  "legal compliance"
"for environmental assessment"             →  "environmental assessment"
"about wetland protection and habitat"    →  "wetland protection and habitat"
"regarding indigenous partnership"         →  "indigenous partnership"
(no pattern match)                         →  "project objectives and goals"
```

## Role Detection Logic

```
Role             Keywords Detected    Email Type               Context Use
─────────────────────────────────────────────────────────────────────────
Financial        financial, budget,   Investment & Budget      "with a focus on
                 finance, cfo,        Planning                 ${contextDetails}"
                 accountant

Legal            legal, lawyer,       Legal Review &           "specifically
                 counsel, attorney    Compliance               regarding ${context}"

Indigenous       elder, indigenous,   Indigenous Partnership   "focused on
                 cultural, nation,    & Sacred Consultation    ${contextDetails}"
                 band

Environmental    environmental,       Environmental            "with emphasis on
                 sustainability,      Sustainability &         ${contextDetails}"
                 ecology,             Ecological Impact
                 conservation

Community        community,           Community Partnership    "focused on
                 resident,            & Engagement             ${contextDetails}"
                 neighborhood,
                 council

Generic          (no match)           Strategic Partnership    "Strategic
                                                               Partnership -
                                                               ${contextDetails}"
```

## Message Flow to Backend

```
Frontend State (React)
│
├─ Contacts:
│  └─ [{ role: "Jane", email: "jane@...", context: "..." }]
│
├─ Email Drafts:
│  └─ [
│      {
│        to: "jane@bank.com",
│        subject: "Investment & Budget Planning...",
│        body: "...investment strategy..."
│      }
│    ]
│
└─ Execute Workflow
   │
   ▼
Backend Request (API Call)
{
  "contacts": [...],
  "email_subjects": [
    "Investment & Budget Planning - Toronto Development Initiative"
  ],
  "email_bodies": [
    "Dear Jane,\n\nWe are developing a sustainable community project..."
  ],
  ...
}
   │
   ▼
Backend Processing (execute_send_emails)
│
├─ Loop through contacts with index
├─ For each contact[i]:
│  ├─ to = contact[i].email
│  ├─ subject = email_subjects[i]  ← PERSONALIZED
│  ├─ body = email_bodies[i]       ← PERSONALIZED
│  └─ send(to, subject, body)
│
└─ Result: Each contact receives their unique email ✅
```

---

This visual architecture shows how the system has been enhanced to extract context from user messages and use it to generate truly personalized emails for each contact!
