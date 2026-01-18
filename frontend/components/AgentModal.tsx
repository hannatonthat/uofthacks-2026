'use client';

import { useState, useEffect, useRef } from 'react';
import { createAgentChat, sendAgentMessage, ChatMessage, ChatResponse } from '@/lib/api';
import { 
  trackAgentChatStarted, 
  trackAgentMessageSent, 
  trackAgentResponseReceived,
  trackAgentResponseRated,
  getDeviceId,
  LocationData
} from '@/lib/amplitude';
import { Trash2 } from 'lucide-react';

interface AgentModalProps {
  isOpen: boolean;
  onClose: () => void;
  panoramaPath: string | null;
  locationData: {
    lat: number;
    lon: number;
    address: string;
    territory?: string;
  } | null;
}

type AgentType = 'sustainability' | 'indigenous' | 'proposal';

interface AgentThread {
  threadId: string;
  messages: ChatMessage[];
  loading: boolean;
}

interface MessageRating {
  messageIndex: number;
  rating: 1 | -1;
}

interface ProposalContact {
  role: string;
  reason: string;
  email: string;
  context?: string; // Store the chat context for this contact
}

interface WorkflowPlan {
  proposal: {
    title: string;
    content: string;
  };
  contacts: {
    count: number;
    suggested_stakeholders: ProposalContact[];
  };
  emails: {
    count: number;
    drafts: Array<{
      to: string;
      subject: string;
      body: string;
    }>;
  };
  meetings: {
    count: number;
    suggested_meetings: Array<{
      title: string;
      attendees: string[];
      duration_minutes: number;
      purpose: string;
    }>;
  };
}

export default function AgentModal({ isOpen, onClose, panoramaPath, locationData }: AgentModalProps) {
  const [activeAgent, setActiveAgent] = useState<AgentType>('sustainability');
  const [threads, setThreads] = useState<Record<AgentType, AgentThread>>({
    sustainability: { threadId: '', messages: [], loading: false },
    indigenous: { threadId: '', messages: [], loading: false },
    proposal: { threadId: '', messages: [], loading: false },
  });
  const [inputMessage, setInputMessage] = useState('');
  const [isMinimized, setIsMinimized] = useState(false);
  const [ratings, setRatings] = useState<Record<AgentType, MessageRating[]>>({
    sustainability: [],
    indigenous: [],
    proposal: [],
  });
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Proposal workflow state
  const [workflowPlan, setWorkflowPlan] = useState<WorkflowPlan | null>(null);
  const [editData, setEditData] = useState<Partial<WorkflowPlan>>({});
  const [executing, setExecuting] = useState(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [threads, activeAgent]);

  useEffect(() => {
    const initializeAgentLocal = async (agent: AgentType) => {
      const currentThread = threads[agent];
      if (currentThread.threadId || currentThread.loading) return;

      setThreads(prev => ({
        ...prev,
        [agent]: { ...prev[agent], loading: true }
      }));

      try {
        let initialMessage = '';
        let imagePath: string | undefined;

        if (agent === 'sustainability') {
          initialMessage = panoramaPath 
            ? `Analyze this location and provide sustainable redesign suggestions. Location: ${locationData?.address || 'Unknown'}`
            : 'Generate initial redesign ideas for sustainable urban development.';
          imagePath = panoramaPath || undefined;
        } else if (agent === 'indigenous') {
          initialMessage = locationData?.territory
            ? `This location is in ${locationData.territory}. What are the key indigenous perspectives to consider for development here?`
            : 'What are the key indigenous perspectives to consider for land development?';
        }

        const response = await createAgentChat(agent, initialMessage, imagePath);

        setThreads(prev => ({
          ...prev,
          [agent]: {
            threadId: response.thread_id,
            messages: [
              { role: 'user', content: response.user_message },
              { role: 'assistant', content: response.assistant_response }
            ],
            loading: false
          }
        }));
      } catch (error) {
        console.error(`Failed to initialize ${agent} agent:`, error);
        setThreads(prev => ({
          ...prev,
          [agent]: {
            ...prev[agent],
            loading: false,
            messages: [
              { role: 'assistant', content: `Failed to initialize agent. Error: ${error instanceof Error ? error.message : 'Unknown error'}` }
            ]
          }
        }));
      }
    };

    const generateWorkflowAutoLocal = async () => {
      try {
        // Get context from sustainability and indigenous agents if available
        const sustainabilityContext = threads.sustainability.messages.length > 0
          ? threads.sustainability.messages[threads.sustainability.messages.length - 1].content.substring(0, 200)
          : '';
        const indigenousContext = threads.indigenous.messages.length > 0
          ? threads.indigenous.messages[threads.indigenous.messages.length - 1].content.substring(0, 200)
          : '';

        // Generate dynamic land use based on location and context
        const locationName = locationData?.address?.split(',')[0] || 'this location';
        const dynamicLandUse = sustainabilityContext.toLowerCase().includes('park') || sustainabilityContext.toLowerCase().includes('green')
          ? 'Green Space Development & Community Park Initiative'
          : sustainabilityContext.toLowerCase().includes('housing') || sustainabilityContext.toLowerCase().includes('residential')
          ? 'Sustainable Housing & Community Development'
          : indigenousContext.toLowerCase().includes('cultural') || indigenousContext.toLowerCase().includes('sacred')
          ? 'Cultural Heritage Preservation & Land Stewardship'
          : `Sustainable Community Development at ${locationName}`;

        const dynamicObjectives = `Integrating indigenous perspectives and sustainability practices for ${locationName}, with focus on community-led decision-making, ecological stewardship, and cultural respect`;

        const proposalRequest = {
          location: locationData?.address || 'Location',
          land_use: dynamicLandUse,
          objectives: dynamicObjectives,
          timeframe: '2-3 years',
        };

        const response = await fetch('http://localhost:8000/workflow/generate-action-plan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(proposalRequest),
        });

        if (!response.ok) throw new Error('Failed to generate workflow');

        const plan = await response.json();
        const editablePlan = JSON.parse(JSON.stringify(plan));
        if (!editablePlan.contacts?.suggested_stakeholders || editablePlan.contacts.suggested_stakeholders.length === 0) {
          editablePlan.contacts = {
            count: 1,
            suggested_stakeholders: [{
              role: 'Community Representative',
              reason: 'Initial consultation and feedback gathering',
              email: 'contact@example.com'
            }]
          };
        }

        setWorkflowPlan(plan);
        setEditData(editablePlan);

        setThreads(prev => ({
          ...prev,
          proposal: {
            ...prev.proposal,
            threadId: `proposal-${Date.now()}`,
            messages: [
              {
                role: 'assistant',
                content: `I've generated a comprehensive workflow proposal for ${proposalRequest.location}. 

Here's what's ready:
📋 **Proposal** - Framework with sustainability & indigenous context
👥 **${editablePlan.contacts?.count || 0} Stakeholders** - Ready to contact
📧 **${editablePlan.emails?.count || 0} Emails** - Draft outreach messages
📅 **${editablePlan.meetings?.count || 0} Meetings** - Scheduled consultations

You can use natural language commands:
• "add [name] at [email@example.com]" - Add new contact
• "schedule meeting with [name] at [email] for [purpose]" - Book consultation
• "send email to [name] at [email] about [subject]" - Custom outreach
• "show me the workflow" - Review all details
• Edit contacts/emails directly below

All commands require valid email addresses. What would you like to do?`
              }
            ],
            loading: false
          }
        }));
      } catch (error) {
        console.error('Error generating workflow:', error);
        setThreads(prev => ({
          ...prev,
          proposal: {
            ...prev.proposal,
            messages: [
              {
                role: 'assistant',
                content: `Failed to generate workflow: ${error instanceof Error ? error.message : 'Unknown error'}`
              }
            ],
            loading: false
          }
        }));
      }
    };

    if (isOpen && !threads[activeAgent].threadId && !threads[activeAgent].loading) {
      if (activeAgent === 'proposal') {
        generateWorkflowAutoLocal();
      } else {
        initializeAgentLocal(activeAgent);
      }
    }
  }, [isOpen, activeAgent, threads, locationData?.address, locationData?.territory, panoramaPath]);

  const initializeAgent = async (agent: AgentType) => {
    const currentThread = threads[agent];
    if (currentThread.threadId || currentThread.loading) return;

    setThreads(prev => ({
      ...prev,
      [agent]: { ...prev[agent], loading: true }
    }));

    try {
      let initialMessage = '';
      let imagePath: string | undefined;

      if (agent === 'sustainability') {
        initialMessage = panoramaPath 
          ? `Analyze this location and provide sustainable redesign suggestions. Location: ${locationData?.address || 'Unknown'}`
          : 'Generate initial redesign ideas for sustainable urban development.';
        imagePath = panoramaPath || undefined;
      } else if (agent === 'indigenous') {
        initialMessage = locationData?.territory
          ? `This location is in ${locationData.territory}. What are the key indigenous perspectives to consider for development here?`
          : 'What are the key indigenous perspectives to consider for land development?';
      }

      const startTime = Date.now();
      const response = await createAgentChat(agent, initialMessage, imagePath);
      const responseTime = Date.now() - startTime;

      // Track agent chat started
      const location: LocationData | undefined = locationData ? {
        lat: locationData.lat,
        lon: locationData.lon,
        territory: locationData.territory,
        address: locationData.address,
      } : undefined;
      
      trackAgentChatStarted(agent, response.thread_id, location);
      
      // Track initial message and response
      trackAgentMessageSent(agent, response.thread_id, initialMessage, 0);
      trackAgentResponseReceived(agent, response.thread_id, response.assistant_response.length, 0, responseTime);

      setThreads(prev => ({
        ...prev,
        [agent]: {
          threadId: response.thread_id,
          messages: [
            { role: 'user', content: response.user_message },
            { role: 'assistant', content: response.assistant_response }
          ],
          loading: false
        }
      }));
    } catch (error) {
      console.error(`Failed to initialize ${agent} agent:`, error);
      setThreads(prev => ({
        ...prev,
        [agent]: {
          ...prev[agent],
          loading: false,
          messages: [
            { role: 'assistant', content: `Failed to initialize agent. Error: ${error instanceof Error ? error.message : 'Unknown error'}` }
          ]
        }
      }));
    }
  };

  const executeWorkflow = async () => {
    if (!editData.contacts?.suggested_stakeholders.length) {
      alert('No contacts to process');
      return;
    }

    setExecuting(true);
    try {
      const threadId = `workflow-${Date.now()}`;
      
      console.log('🚀 Starting workflow execution...');
      console.log('📋 Contacts:', editData.contacts.suggested_stakeholders);
      
      // Add contacts
      for (const contact of editData.contacts.suggested_stakeholders) {
        console.log(`➕ Adding contact: ${contact.role} (${contact.email})`);
        await fetch(`http://localhost:8000/workflow/add-contact?threadid=${threadId}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: contact.role,
            role: contact.role,
            email: contact.email,
            phone: '+1-555-0000',
          }),
        });
      }

      console.log('📧 Requesting full outreach (emails + meetings + Slack)...');
      
      // Build dynamic event type from proposal or first email subject
      let eventTypeName = 'Community Development Consultation';
      if (editData.emails?.drafts?.[0]?.subject) {
        eventTypeName = editData.emails.drafts[0].subject.split(' - ')[0]; // Get subject part before dash
      } else if (editData.proposal?.title) {
        eventTypeName = editData.proposal.title.split('at')[0].trim();
      }
      
      // Request full outreach with email subjects and meetings
      const outreachResponse = await fetch(`http://localhost:8000/workflow/full-outreach?threadid=${threadId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          proposal_title: editData.proposal?.title || 'Workflow Proposal',
          event_type_name: eventTypeName,
          email_subjects: editData.emails?.drafts?.map(e => e.subject) || [], // Pass actual email subjects
          email_bodies: editData.emails?.drafts?.map(e => e.body) || [], // Pass actual email bodies
        }),
      });

      if (!outreachResponse.ok) throw new Error('Failed to request outreach');
      const outreachResult = await outreachResponse.json();
      console.log('📬 Outreach response:', outreachResult);

      console.log('✅ Confirming action...');
      // Confirm action
      const confirmResponse = await fetch('http://localhost:8000/workflow/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action_id: outreachResult.action_id,
          approved: true,
        }),
      });

      if (!confirmResponse.ok) throw new Error('Failed to approve action');
      const confirmResult = await confirmResponse.json();
      console.log('🎉 Confirmation result:', confirmResult);

      alert(`✅ Workflow executed!\n\n📧 ${confirmResult.result?.emails_sent || 0} Emails sent\n📅 ${confirmResult.result?.meetings_scheduled || 0} Meetings booked\n📢 Slack notification: ${confirmResult.result?.slack_notified ? 'Yes' : 'No'}`);
      setWorkflowPlan(null);
      setEditData({});
    } catch (error) {
      console.error('❌ Error executing workflow:', error);
      alert(`Failed to execute workflow: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setExecuting(false);
    }
  };

  const removeContact = (index: number) => {
    if (!editData.contacts) return;
    const updated = editData.contacts.suggested_stakeholders.filter((_: ProposalContact, i: number) => i !== index);
    setEditData({
      ...editData,
      contacts: {
        ...editData.contacts,
        count: updated.length,
        suggested_stakeholders: updated,
      },
    });
  };

  const updateContact = (index: number, field: keyof ProposalContact, value: string) => {
    if (!editData.contacts) return;
    const updated = [...editData.contacts.suggested_stakeholders];
    updated[index] = { ...updated[index], [field]: value };
    setEditData({
      ...editData,
      contacts: {
        ...editData.contacts,
        suggested_stakeholders: updated,
      },
    });
  };

  // Build a concise workflow summary for chat responses
  const buildWorkflowSummary = () => {
    const proposalTitle = editData.proposal?.title || 'Untitled';
    const proposalPreview = editData.proposal?.content ? `${editData.proposal.content.substring(0, 200)}...` : '';
    const contacts = editData.contacts?.suggested_stakeholders || [];
    const contactLines = contacts.length
      ? contacts.map(c => `  • ${c.role} - ${c.reason}`).join('\n')
      : '  No contacts yet';

    const emailDrafts = editData.emails?.drafts || [];
    const emailLines = emailDrafts.length
      ? emailDrafts.slice(0, 3).map((e, idx) => `  • Email ${idx + 1}: ${e.to} — ${e.subject || 'No subject'}`).join('\n')
      : '  No email drafts yet';

    const meetings = editData.meetings?.suggested_meetings || [];
    const meetingLines = meetings.length
      ? meetings.slice(0, 3).map((m, idx) => `  • ${idx + 1}. ${m.title}${m.attendees?.length ? ` (with ${m.attendees.join(', ')})` : ''}`).join('\n')
      : '  No meetings yet';

    return `📋 Proposal: ${proposalTitle}
${proposalPreview}

👥 ${editData.contacts?.count || 0} Stakeholder Contacts:
${contactLines}

📧 ${editData.emails?.count || 0} Email Drafts (personalized with sustainability + indigenous context)
${emailLines}

📅 ${editData.meetings?.count || 0} Meeting Invitations
${meetingLines}

💬 Slack Notification ready`;
  };

  // Helper: Generate role-specific email content and subjects
  const generateRoleSpecificEmail = (role: string, purpose: string, locationName: string) => {
    const roleLower = role.toLowerCase();
    const sustainabilityText = threads.sustainability.messages.length > 0
      ? threads.sustainability.messages[threads.sustainability.messages.length - 1].content.substring(0, 250)
      : 'sustainable development practices';
    const indigenousText = threads.indigenous.messages.length > 0
      ? threads.indigenous.messages[threads.indigenous.messages.length - 1].content.substring(0, 250)
      : 'indigenous perspectives and community leadership';

    // Extract meaningful context from the purpose/chat message
    // Look for specific requirements or contexts mentioned in the message
    let contextDetails = 'project objectives and goals';
    
    // Extract patterns like "for [context]", "regarding [context]", "about [context]"
    const forMatch = purpose.match(/for\s+([^,]+?)(?:\s+at\s+|$)/i);
    const aboutMatch = purpose.match(/(?:about|regarding)\s+([^,]+?)(?:\s+at\s+|$)/i);
    const contextMatch = forMatch || aboutMatch;
    
    if (contextMatch?.[1]) {
      contextDetails = contextMatch[1].trim();
      // Clean up email patterns from context
      contextDetails = contextDetails.replace(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/g, '').trim();
    }

    let subject = '';
    let body = '';

    if (roleLower.includes('financial') || roleLower.includes('budget') || roleLower.includes('finance') || roleLower.includes('cfo') || roleLower.includes('accountant')) {
      subject = `Investment & Budget Planning - ${locationName} Development Initiative`;
      body = `Dear ${role},

We are developing a sustainable community project at ${locationName} with a focus on ${contextDetails} and require financial expertise for budgeting, funding strategies, and investment opportunities.

**Project Financial Considerations:**
• Budget allocation and cost-benefit analysis for ${contextDetails}
• Funding opportunities and grant programs
• ROI projections and financial sustainability
• Investment from community stakeholders

**Sustainability Context:**
${sustainabilityText}

**Indigenous Partnership & Governance:**
${indigenousText}

Your financial planning expertise would be critical to ensuring this project is fiscally responsible while honoring community values. We would value a meeting to discuss funding mechanisms and financial sustainability.

Please let us know your availability for an initial consultation.

Best regards,
The Development Team`;
    } else if (roleLower.includes('legal') || roleLower.includes('lawyer') || roleLower.includes('counsel') || roleLower.includes('attorney')) {
      subject = `Legal Review & Compliance - ${locationName} Community Development`;
      body = `Dear ${role},

We are seeking legal guidance on a community development project at ${locationName} that integrates sustainable practices with indigenous governance principles, specifically regarding ${contextDetails}.

**Key Legal Areas:**
• Land use regulations and zoning compliance for ${contextDetails}
• Environmental assessments and permits
• Indigenous rights and consultation requirements
• Contract structures with community stakeholders
• Liability and insurance considerations

**Sustainability Framework:**
${sustainabilityText}

**Indigenous Leadership & Protocols:**
${indigenousText}

We need your expertise to ensure all legal requirements are met while respecting indigenous sovereignty and community-led decision-making. Please review the attached proposal and let us know if you're available for a consultation.

Thank you,
The Development Team`;
    } else if (roleLower.includes('elder') || roleLower.includes('indigenous') || roleLower.includes('cultural') || roleLower.includes('nation') || roleLower.includes('band')) {
      subject = `Indigenous Partnership & Sacred Consultation - ${locationName} Stewardship`;
      body = `Dear ${role},

We greet you respectfully. We are working on a development initiative at ${locationName} focused on ${contextDetails}, and recognize that this land's stewardship and cultural significance must guide our efforts.

**Our Commitment to Indigenous Leadership:**
• Centering indigenous knowledge and governance in ${contextDetails}
• Respecting sacred sites and cultural protocols
• Ensuring community-led decision-making
• Supporting indigenous economic participation
• Honoring the nation's sovereignty and rights

**Sustainability Alignment:**
${sustainabilityText}

**Our Understanding of Indigenous Context:**
${indigenousText}

We seek your guidance and partnership to ensure this project reflects your community's values, priorities, and long-term wellbeing. Your leadership is essential to the project's success and integrity.

We welcome the opportunity to meet and discuss how we can work together respectfully.

With deep respect,
The Development Team`;
    } else if (roleLower.includes('environmental') || roleLower.includes('sustainability') || roleLower.includes('ecolog') || roleLower.includes('conservation')) {
      subject = `Environmental Sustainability & Ecological Impact - ${locationName} Review`;
      body = `Dear ${role},

We are planning a sustainable development project at ${locationName} with emphasis on ${contextDetails} and need environmental expertise to maximize positive ecological outcomes.

**Environmental Focus Areas:**
• Ecological impact assessment and mitigation for ${contextDetails}
• Green infrastructure and nature-based solutions
• Carbon reduction and climate resilience
• Biodiversity enhancement and habitat restoration
• Water and waste management systems

**Proposed Sustainability Measures:**
${sustainabilityText}

**Community & Indigenous Environmental Stewardship:**
${indigenousText}

Your environmental expertise will ensure we create a project that strengthens ecosystems while honoring indigenous land stewardship practices. We'd like to schedule a consultation to discuss your recommendations.

Please let us know your availability.

Regards,
The Development Team`;
    } else if (roleLower.includes('community') || roleLower.includes('resident') || roleLower.includes('neighborhood') || roleLower.includes('council')) {
      subject = `Community Partnership & Engagement - ${locationName} Development`;
      body = `Dear ${role},

We are developing a community-centered initiative at ${locationName} focused on ${contextDetails} and your participation as a community representative is essential.

**Community Engagement Goals:**
• Gathering local feedback and priorities on ${contextDetails}
• Building collaborative decision-making processes
• Creating local economic opportunities
• Supporting community health and wellbeing
• Strengthening neighborhood connections

**Sustainability Vision:**
${sustainabilityText}

**Honoring Indigenous Principles:**
${indigenousText}

This project is designed with community leadership at its core. We value your insights and want to work together to create something that truly serves the neighborhood's long-term interests.

We'd love to meet and hear your thoughts. Let us know when you're available.

Thank you,
The Development Team`;
    } else {
      subject = `Strategic Partnership - ${contextDetails} at ${locationName}`;
      body = `Dear ${role},

We are developing a sustainable community project at ${locationName} focused on ${contextDetails} and believe your expertise and perspective would be valuable to our initiative.

Project Focus: ${contextDetails}

**Sustainability Approach:**
${sustainabilityText}

**Indigenous Partnership Framework:**
${indigenousText}

Your involvement would help ensure we create a project that is both sustainable and respectful of indigenous principles and community values. We would appreciate the opportunity to discuss this with you further.

Please let us know if you're interested in learning more and your availability for a meeting.

Best regards,
The Development Team`;
    }

    return { subject, body };
  };

  // Helper: Generate unique meeting subjects based on role and purpose
  const generateMeetingSubject = (role: string, purpose: string) => {
    const roleLower = role.toLowerCase();
    let meetingSubject = '';

    if (roleLower.includes('financial') || roleLower.includes('budget') || roleLower.includes('finance')) {
      meetingSubject = `Financial Planning Consultation: ${purpose} Strategy`;
    } else if (roleLower.includes('legal') || roleLower.includes('lawyer') || roleLower.includes('counsel')) {
      meetingSubject = `Legal Consultation: ${purpose} Compliance & Governance`;
    } else if (roleLower.includes('elder') || roleLower.includes('indigenous') || roleLower.includes('cultural')) {
      meetingSubject = `Indigenous Stewardship Meeting: ${purpose} & Community Protocols`;
    } else if (roleLower.includes('environmental') || roleLower.includes('sustainability') || roleLower.includes('ecolog')) {
      meetingSubject = `Environmental Review Meeting: ${purpose} & Ecological Impact`;
    } else if (roleLower.includes('community') || roleLower.includes('resident')) {
      meetingSubject = `Community Engagement Session: ${purpose} & Local Partnership`;
    } else {
      meetingSubject = `Strategic Meeting: ${purpose} Discussion`;
    }

    return meetingSubject;
  };

  const parseAndApplyChatCommand = (userMessage: string) => {
    const lowerMsg = userMessage.toLowerCase();
    
    // Command: Add a contact
    if (lowerMsg.includes('add') && (lowerMsg.includes('contact') || lowerMsg.includes('stakeholder'))) {
      // Extract email - REQUIRED
      const emailMatch = userMessage.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/);
      if (!emailMatch) {
        return { success: false, response: `Please provide an email address for the contact. Try: "add [name] with email [email@example.com]"` };
      }
      
      // Extract name if provided
      const nameMatch = userMessage.match(/(?:add|contact|stakeholder).*?(?:named|called|is)\s+([A-Za-z\s]+?)(?:\s+(?:with|at|email)|$)/i);
      const name = nameMatch?.[1]?.trim() || 'New Stakeholder';
      const extractedEmail = emailMatch[1];
      
      // Store the entire user message as context for this contact
      const contactContext = userMessage;
      
      const newContact: ProposalContact = {
        role: name,
        reason: 'Added via chat',
        email: extractedEmail,
        context: contactContext, // Store full chat context
      };
      
      let newEditData: Partial<WorkflowPlan> = JSON.parse(JSON.stringify(editData));
      const prevContacts = newEditData.contacts || { count: 0, suggested_stakeholders: [] };
      const prevEmails = newEditData.emails || { count: 0, drafts: [] };

      const updatedContacts = {
        count: (prevContacts.count || 0) + 1,
        suggested_stakeholders: [
          ...(prevContacts.suggested_stakeholders || []),
          newContact
        ]
      };

      const proposalTitle = newEditData.proposal?.title || 'Community Development Proposal';
      const locationName = proposalTitle.split('at')[1]?.trim() || 'this location';
      
      // Generate role-specific email using the actual chat context as purpose
      const { subject: roleSpecificSubject, body: roleSpecificBody } = generateRoleSpecificEmail(
        newContact.role,
        contactContext, // Use the actual chat message as context
        locationName
      );
      
      const newEmailDraft = {
        to: extractedEmail,
        subject: roleSpecificSubject,
        body: roleSpecificBody
      };

      const updatedEmails = {
        count: (prevEmails.count || 0) + 1,
        drafts: [...(prevEmails.drafts || []), newEmailDraft]
      };

      newEditData = {
        ...newEditData,
        contacts: updatedContacts,
        emails: updatedEmails
      };
      
      // Update state
      setEditData(newEditData);
      
      return { success: true, response: `Added "${name}" (${extractedEmail}) to contacts. Email draft created based on: "${contactContext.substring(0, 60)}..." and ready to send.` };
    }
    
    // Command: Modify contact email
    if (lowerMsg.includes('email') && (lowerMsg.includes('change') || lowerMsg.includes('update') || lowerMsg.includes('to'))) {
      const emailMatch = userMessage.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/);
      if (emailMatch && editData.contacts?.suggested_stakeholders.length) {
        const newEmail = emailMatch[1];
        const lastContact = editData.contacts.suggested_stakeholders.length - 1;
        
        let newEditData: Partial<WorkflowPlan> = JSON.parse(JSON.stringify(editData));
        const updated = [...(newEditData.contacts?.suggested_stakeholders || [])];
        updated[lastContact] = { ...updated[lastContact], email: newEmail };
        
        newEditData = {
          ...newEditData,
          contacts: {
            ...newEditData.contacts!,
            suggested_stakeholders: updated
          }
        };
        
        setEditData(newEditData);
        
        return { success: true, response: `Updated contact email to ${newEmail}.` };
      }
    }
    
    // Command: Modify proposal/add meeting request
    if (lowerMsg.includes('meeting') || lowerMsg.includes('schedule') || lowerMsg.includes('consultation')) {
      // Extract email - REQUIRED
      const emailMatch = userMessage.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/);
      if (!emailMatch) {
        return { success: false, response: `Please provide an email address for the meeting invitation. Try: "schedule meeting with [name] at [email@example.com] for [purpose]"` };
      }
      
      // Detect contact and purpose
      const contactMatch = userMessage.match(/with\s+([A-Za-z\s]+?)(?:\s+at|\s+for|\s+email|$)/i);
      const purposeMatch = userMessage.match(/for\s+(.+?)(?:\s+at\s+[a-zA-Z0-9._%+-]+@)?/i);
      const contactName = contactMatch?.[1]?.trim() || 'Stakeholder';
      const purpose = purposeMatch?.[1]?.trim() || 'Consultation request';
      const extractedEmail = emailMatch[1];
      
      // Store the entire user message as context for this contact
      const contactContext = userMessage;

      // Create updated state synchronously
      let newEditData: Partial<WorkflowPlan> = JSON.parse(JSON.stringify(editData));
      const prevContacts = newEditData.contacts || { count: 0, suggested_stakeholders: [] };
      const prevEmails = newEditData.emails || { count: 0, drafts: [] };
      const prevMeetings = newEditData.meetings || { count: 0, suggested_meetings: [] };

      const alreadyExists = (prevContacts.suggested_stakeholders || []).some(c => c.email.toLowerCase() === extractedEmail.toLowerCase());
      const newContactsList = alreadyExists
        ? prevContacts.suggested_stakeholders
        : [...(prevContacts.suggested_stakeholders || []), { role: contactName, reason: purpose, email: extractedEmail, context: contactContext }];

      const proposalTitle = newEditData.proposal?.title || 'Community Development Proposal';
      const locationName = proposalTitle.split('at')[1]?.trim() || 'our location';
      
      // Generate role-specific email using the full context
      const { subject: roleSpecificEmailSubject, body: roleSpecificEmailBody } = generateRoleSpecificEmail(
        contactName,
        contactContext, // Use the actual chat message as context
        locationName
      );
      
      const newEmailsList = [...(prevEmails.drafts || []), {
        to: extractedEmail,
        subject: roleSpecificEmailSubject,
        body: roleSpecificEmailBody
      }];

      const meetingTitle = generateMeetingSubject(contactName, purpose);
      const newMeeting = {
        title: meetingTitle,
        attendees: [contactName],
        duration_minutes: 60,
        purpose,
      };

      newEditData = {
        ...newEditData,
        contacts: {
          count: alreadyExists ? (prevContacts.count || newContactsList.length) : (prevContacts.count || 0) + 1,
          suggested_stakeholders: newContactsList
        },
        emails: {
          count: (prevEmails.count || 0) + 1,
          drafts: newEmailsList
        },
        meetings: {
          count: (prevMeetings.count || 0) + 1,
          suggested_meetings: [...(prevMeetings.suggested_meetings || []), newMeeting]
        }
      };

      // Update state
      setEditData(newEditData);
      
      return { success: true, response: `Great! I'll note that you want to schedule a meeting with ${contactName} (${extractedEmail}) for "${purpose}". When you execute the workflow, I'll automatically book the meeting and send calendar invites to all stakeholders.` };
    }
    
    // Command: Add custom email
    if (lowerMsg.includes('send') && lowerMsg.includes('email')) {
      // Extract email - REQUIRED
      const emailMatch = userMessage.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/);
      if (!emailMatch) {
        return { success: false, response: `Please provide an email address. Try: "send email to [name] at [email@example.com] about [subject]"` };
      }
      
      // Extract recipient and subject if provided
      const recipientMatch = userMessage.match(/to\s+([A-Za-z\s]+?)(?:\s+at|\s+about|\s+regarding|$)/i);
      const subjectMatch = userMessage.match(/(?:about|regarding)\s+(.+?)(?:\s+at\s+[a-zA-Z0-9._%+-]+@)?/i);
      const recipient = recipientMatch?.[1]?.trim() || 'Stakeholder';
      const subject = subjectMatch?.[1]?.trim() || 'Project Consultation';
      const extractedEmail = emailMatch[1];
      
      // Store the entire user message as context for this email
      const emailContext = userMessage;

      // Create updated state synchronously
      let newEditData: Partial<WorkflowPlan> = JSON.parse(JSON.stringify(editData));
      const prevEmails = newEditData.emails || { count: 0, drafts: [] };
      const proposalTitle = newEditData.proposal?.title || 'Community Development Proposal';
      const locationName = proposalTitle.split('at')[1]?.trim() || 'our location';
      
      // Use role-specific email generation for more targeted content with full context
      const { subject: roleBasedSubject, body: roleBasedBody } = generateRoleSpecificEmail(
        recipient,
        emailContext, // Use the actual chat message as context
        locationName
      );
      
      const newEmail = {
        to: extractedEmail,
        subject: roleBasedSubject,
        body: roleBasedBody
      };

      newEditData = {
        ...newEditData,
        emails: {
          count: (prevEmails.count || 0) + 1,
          drafts: [...(prevEmails.drafts || []), newEmail]
        }
      };

      // Update state
      setEditData(newEditData);

      return { success: true, response: `Added email to ${recipient} (${extractedEmail}) about "${subject}". Email draft created with role-specific content and ready to send.` };
    }

    // Command: Modify email/proposal content
    if (lowerMsg.includes('email') && (lowerMsg.includes('add') || lowerMsg.includes('mention') || lowerMsg.includes('include'))) {
      return { success: false, response: `You can edit the email drafts below to include any additional information or context you'd like to add.` };
    }
    
    return null;
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    const currentThread = threads[activeAgent];
    if (!currentThread.threadId) {
      if (activeAgent === 'proposal') {
        // Auto-generate for proposal tab
        return;
      } else {
        await initializeAgent(activeAgent);
        return;
      }
    }

    const userMessage = inputMessage.trim();
    setInputMessage('');

    // For proposal agent, parse commands and provide smart responses
    if (activeAgent === 'proposal') {
      setThreads(prev => ({
        ...prev,
        proposal: {
          ...prev.proposal,
          messages: [
            ...prev.proposal.messages,
            { role: 'user', content: userMessage }
          ],
          loading: true
        }
      }));

      // Check if user is asking for workflow details/data
      const isAskingForData = /\b(show|list|display|what|tell|give|see|view|explain|what's|whats)\b.*\b(workflow|steps|process|plan|contacts|emails|meetings|stakeholders|data|details)\b/i.test(userMessage);
      
      if (isAskingForData && editData) {
        setTimeout(() => {
          const workflowSummary = `Here's the complete workflow breakdown:\n\n${buildWorkflowSummary()}\n\nYou can modify contacts, emails, or ask me to add/change anything!`;

          setThreads(prev => ({
            ...prev,
            proposal: {
              ...prev.proposal,
              messages: [
                ...prev.proposal.messages,
                { role: 'assistant', content: workflowSummary }
              ],
              loading: false
            }
          }));
        }, 500);
        return;
      }

      // Parse chat commands
      const commandResult = parseAndApplyChatCommand(userMessage);
      
      // Simulate assistant response - use updated editData immediately
      setTimeout(() => {
        setThreads(prev => ({
          ...prev,
          proposal: {
            ...prev.proposal,
            messages: [
              ...prev.proposal.messages,
              {
                role: 'assistant',
                content: commandResult
                  ? `${commandResult.response}\n\nUpdated workflow:\n\n${buildWorkflowSummary()}`
                  : `I've noted: "${userMessage}"\n\nYou can edit any details in the workflow sections below. I'll automatically:\n• Book calendar meetings with all stakeholders\n• Send personalized emails from sustainability + indigenous context\n• Post team coordination messages to Slack\n\nFeel free to adjust the contacts and emails, then click "Execute" when ready!`
              }
            ],
            loading: false
          }
        }));
      }, 500);
      return;
    }

    setThreads(prev => ({
      ...prev,
      [activeAgent]: {
        ...prev[activeAgent],
        messages: [...prev[activeAgent].messages, { role: 'user', content: userMessage }],
        loading: true
      }
    }));

    try {
      // Track message sent
      const messageIndex = currentThread.messages.length;
      trackAgentMessageSent(activeAgent, currentThread.threadId, userMessage, messageIndex);
      
      const startTime = Date.now();
      const response = await sendAgentMessage(currentThread.threadId, userMessage);
      const responseTime = Date.now() - startTime;
      
      // Track response received
      trackAgentResponseReceived(activeAgent, currentThread.threadId, response.assistant_response.length, messageIndex, responseTime);

      setThreads(prev => ({
        ...prev,
        [activeAgent]: {
          ...prev[activeAgent],
          messages: [
            ...prev[activeAgent].messages,
            { role: 'assistant', content: response.assistant_response }
          ],
          loading: false
        }
      }));
    } catch (error) {
      console.error('Failed to send message:', error);
      setThreads(prev => ({
        ...prev,
        [activeAgent]: {
          ...prev[activeAgent],
          messages: [
            ...prev[activeAgent].messages,
            { role: 'assistant', content: `Error: ${error instanceof Error ? error.message : 'Failed to send message'}` }
          ],
          loading: false
        }
      }));
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleRating = async (messageIndex: number, rating: 1 | -1) => {
    const currentThread = threads[activeAgent];
    if (!currentThread.threadId) return;

    // Find the user message and agent response
    const userMessage = currentThread.messages[messageIndex - 1]?.content || '';
    const agentResponse = currentThread.messages[messageIndex]?.content || '';

    // Update local state
    setRatings(prev => ({
      ...prev,
      [activeAgent]: [
        ...prev[activeAgent].filter(r => r.messageIndex !== messageIndex),
        { messageIndex, rating }
      ]
    }));

    // Track with Amplitude
    const location: LocationData | undefined = locationData ? {
      lat: locationData.lat,
      lon: locationData.lon,
      territory: locationData.territory,
      address: locationData.address,
    } : undefined;

    trackAgentResponseRated(
      activeAgent,
      currentThread.threadId,
      messageIndex,
      rating,
      userMessage,
      agentResponse,
      location
    );

    // Send to backend for storage and AI analysis
    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      await fetch(`${API_BASE_URL}/api/ratings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: getDeviceId(),
          thread_id: currentThread.threadId,
          agent_type: activeAgent,
          message_index: messageIndex,
          rating,
          context: {
            user_message: userMessage,
            agent_response: agentResponse,
            location: locationData ? {
              lat: locationData.lat,
              lon: locationData.lon,
            } : undefined,
          }
        }),
      });
    } catch (error) {
      console.error('Failed to save rating:', error);
    }
  };

  const getRatingForMessage = (messageIndex: number): 1 | -1 | null => {
    const rating = ratings[activeAgent].find(r => r.messageIndex === messageIndex);
    return rating ? rating.rating : null;
  };

  if (!isOpen) return null;

  const agentNames = {
    sustainability: 'Sustainability',
    indigenous: 'Indigenous Context',
    proposal: 'Proposal Workflow'
  };

  const currentThread = threads[activeAgent];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div 
        className={`bg-gray-900 border border-gray-700 rounded-lg shadow-2xl transition-all duration-300 ${
          isMinimized ? 'w-96 h-16' : 'w-[90vw] max-w-4xl h-[80vh]'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-lg font-bold text-white">AI Agents</h2>
          <div className="flex gap-2">
            <button
              onClick={() => setIsMinimized(!isMinimized)}
              className="text-gray-400 hover:text-white text-xl px-2"
            >
              {isMinimized ? '□' : '_'}
            </button>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white text-xl px-2"
            >
              ×
            </button>
          </div>
        </div>

        {!isMinimized && (
          <>
            {/* Tabs */}
            <div className="flex border-b border-gray-700">
              {(Object.keys(agentNames) as AgentType[]).map((agent) => (
                <button
                  key={agent}
                  onClick={() => setActiveAgent(agent)}
                  className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                    activeAgent === agent
                      ? 'bg-gray-800 text-white border-b-2 border-blue-500'
                      : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
                  }`}
                >
                  {agentNames[agent]}
                </button>
              ))}
            </div>

            {/* Chat/Workflow Area */}
            <div className="flex flex-col h-[calc(80vh-8rem)]">
              {activeAgent === 'proposal' && workflowPlan ? (
                // Proposal Workflow - Split view: chat on top, workflow details below
                <>
                  {/* Chat Messages */}
                  <div className="flex-1 overflow-y-auto p-4 space-y-4 border-b border-gray-700">
                    {threads.proposal.messages.length === 0 && !threads.proposal.loading && (
                      <div className="text-center text-gray-500 py-8 text-sm">
                        Loading workflow...
                      </div>
                    )}

                    {threads.proposal.messages.map((message, index) => (
                      <div
                        key={index}
                        className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                          className={`max-w-[80%] rounded-lg px-4 py-2 ${
                            message.role === 'user'
                              ? 'bg-blue-600 text-white'
                              : 'bg-gray-800 text-gray-100'
                          }`}
                        >
                          <div className="whitespace-pre-wrap text-sm">{message.content}</div>
                        </div>
                      </div>
                    ))}

                    {threads.proposal.loading && (
                      <div className="flex justify-start">
                        <div className="bg-gray-800 text-gray-100 rounded-lg px-4 py-2">
                          <div className="flex items-center gap-2 text-sm">
                            <div className="animate-pulse">Processing...</div>
                            <div className="flex gap-1">
                              <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                              <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                              <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    <div ref={messagesEndRef} />
                  </div>

                  {/* Workflow Details - Scrollable */}
                  <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-850">
                    {/* Proposal Summary */}
                    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
                      <div className="text-lg font-semibold text-white mb-2">📋 {editData.proposal?.title}</div>
                      <div className="text-xs text-gray-300 mb-3 line-clamp-3">{editData.proposal?.content?.substring(0, 200)}...</div>
                      
                      <div className="grid grid-cols-3 gap-3 text-center">
                        <div className="bg-gray-700 rounded p-2">
                          <div className="text-2xl">👥</div>
                          <div className="text-sm font-semibold text-white">{editData.contacts?.count || 0}</div>
                          <div className="text-xs text-gray-400">Contacts</div>
                        </div>
                        <div className="bg-gray-700 rounded p-2">
                          <div className="text-2xl">📧</div>
                          <div className="text-sm font-semibold text-white">{editData.emails?.count || 0}</div>
                          <div className="text-xs text-gray-400">Emails</div>
                        </div>
                        <div className="bg-gray-700 rounded p-2">
                          <div className="text-2xl">📅</div>
                          <div className="text-sm font-semibold text-white">{editData.meetings?.count || 0}</div>
                          <div className="text-xs text-gray-400">Meetings</div>
                        </div>
                      </div>
                    </div>

                    {/* Contacts - Simplified */}
                    <div className="bg-gray-800 rounded-lg border border-gray-700">
                      <div className="px-4 py-3 border-b border-gray-700">
                        <div className="font-semibold text-white text-sm flex items-center gap-2">
                          <span>👥</span> Stakeholders ({editData.contacts?.count || 0})
                        </div>
                      </div>
                      <div className="p-3 space-y-2 max-h-48 overflow-y-auto">
                        {editData.contacts?.suggested_stakeholders.map((contact: ProposalContact, idx: number) => (
                          <div key={idx} className="bg-gray-700 rounded p-2 text-xs flex items-center gap-2">
                            <div className="flex-1">
                              <input
                                type="text"
                                value={contact.role}
                                onChange={(e) => updateContact(idx, 'role', e.target.value)}
                                className="w-full px-2 py-1 bg-gray-600 border border-gray-500 rounded text-white text-xs focus:outline-none focus:border-blue-500 mb-1"
                                placeholder="Role"
                              />
                              <input
                                type="text"
                                value={contact.email}
                                onChange={(e) => updateContact(idx, 'email', e.target.value)}
                                className="w-full px-2 py-1 bg-gray-600 border border-gray-500 rounded text-white text-xs focus:outline-none focus:border-blue-500"
                                placeholder="Email"
                              />
                            </div>
                            <button onClick={() => removeContact(idx)} className="text-red-400 hover:text-red-300">
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        ))}
                        <div className="text-gray-400 text-xs pt-2 border-t border-gray-600 italic">
                          💡 Say &quot;add John from Environment Canada&quot; to add more
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              ) : activeAgent === 'proposal' ? (
                // Loading proposal workflow
                <div className="flex-1 flex items-center justify-center">
                  <div className="text-center">
                    <div className="animate-spin text-3xl mb-3">🔄</div>
                    <div className="text-gray-400 text-sm">Generating your workflow...</div>
                  </div>
                </div>
              ) : (
                // Regular Chat for Sustainability and Indigenous Agents
                <>
                  {/* Messages */}
                  <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {currentThread.messages.length === 0 && !currentThread.loading && (
                      <div className="text-center text-gray-500 py-8 text-sm">
                        Starting conversation with {agentNames[activeAgent]} Agent...
                      </div>
                    )}

                    {currentThread.messages.map((message, index) => (
                      <div
                        key={index}
                        className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                          className={`max-w-[80%] rounded-lg px-4 py-2 ${
                            message.role === 'user'
                              ? 'bg-blue-600 text-white'
                              : 'bg-gray-800 text-gray-100'
                          }`}
                        >
                          <div className="text-xs font-semibold mb-1 opacity-75">
                            {message.role === 'user' ? 'You' : agentNames[activeAgent]}
                          </div>
                          <div className="whitespace-pre-wrap text-sm">{message.content}</div>
                        </div>
                      </div>
                    ))}

                    {currentThread.loading && (
                      <div className="flex justify-start">
                        <div className="bg-gray-800 text-gray-100 rounded-lg px-4 py-2">
                          <div className="text-xs font-semibold mb-1 opacity-75">
                            {agentNames[activeAgent]}
                          </div>
                          <div className="flex items-center gap-2 text-sm">
                            <div className="animate-pulse">Thinking...</div>
                            <div className="flex gap-1">
                              <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                              <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                              <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    <div ref={messagesEndRef} />
                  </div>
                </>
              )}
            </div>

            {/* Input Area */}
            <div className="border-t border-gray-700 p-3 bg-gray-800">
              {activeAgent === 'proposal' && workflowPlan ? (
                <div className="flex flex-col gap-2">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={inputMessage}
                      onChange={(e) => setInputMessage(e.target.value)}
                      onKeyPress={handleKeyPress}
                      placeholder="Ask for changes or refinements..."
                      disabled={threads.proposal.loading}
                      className="flex-1 bg-gray-700 text-white px-3 py-2 rounded text-sm border border-gray-600 focus:outline-none focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    />
                    <button
                      onClick={handleSendMessage}
                      disabled={!inputMessage.trim() || threads.proposal.loading}
                      className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      Chat
                    </button>
                    <button
                      onClick={executeWorkflow}
                      disabled={executing}
                      className="bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white px-3 py-2 rounded text-sm transition font-medium"
                    >
                      {executing ? '⏳ Exec' : '✅ Execute'}
                    </button>
                  </div>
                  
                  {/* Quick Command Examples for Proposal */}
                  <div className="text-xs text-gray-400 space-y-1">
                    <div className="font-semibold mb-1 opacity-75">Quick commands:</div>
                    <div className="grid grid-cols-1 gap-1">
                      <button onClick={() => setInputMessage('add Financial Advisor at john.smith@bankname.com for budget planning')} className="text-left hover:text-blue-400 transition truncate">
                        💰 Add financial advisor
                      </button>
                      <button onClick={() => setInputMessage('schedule meeting with Legal Counsel at counsel@law.com for contract review')} className="text-left hover:text-blue-400 transition truncate">
                        ⚖️ Schedule legal meeting
                      </button>
                      <button onClick={() => setInputMessage('send email to Environmental Expert at env@org.com about ecological impact assessment')} className="text-left hover:text-blue-400 transition truncate">
                        🌍 Contact environmental expert
                      </button>
                      <button onClick={() => setInputMessage('add Indigenous Elder at elder@nation.ca for cultural consultation')} className="text-left hover:text-blue-400 transition truncate">
                        🤝 Add indigenous partner
                      </button>
                      <button onClick={() => setInputMessage('schedule meeting with Community Manager at manager@community.org for stakeholder engagement')} className="text-left hover:text-blue-400 transition truncate">
                        👥 Schedule community meeting
                      </button>
                    </div>
                  </div>
                </div>
              ) : activeAgent === 'proposal' ? (
                <div className="text-center text-gray-400 text-xs py-2">
                  Loading workflow...
                </div>
              ) : (
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder={`Message ${agentNames[activeAgent]} Agent...`}
                    disabled={currentThread.loading}
                    className="flex-1 bg-gray-700 text-white px-3 py-2 rounded text-sm border border-gray-600 focus:outline-none focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={!inputMessage.trim() || currentThread.loading}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Send
                  </button>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
