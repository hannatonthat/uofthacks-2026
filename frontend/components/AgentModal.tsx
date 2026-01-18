'use client';

import { useState, useEffect, useRef } from 'react';
import { createAgentChat, sendAgentMessage, ChatMessage } from '@/lib/api';
import { 
  trackAgentChatStarted, 
  trackAgentMessageSent, 
  trackAgentResponseReceived,
  LocationData
} from '@/lib/amplitude';
import { ChevronDown, ChevronUp, Trash2 } from 'lucide-react';

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

// interface MessageRating {
//   messageIndex: number;
//   rating: 1 | -1;
// }

interface ProposalContact {
  role: string;
  reason: string;
  email: string;
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
  // Ratings feature (currently disabled)
  // const [ratings, setRatings] = useState<Record<AgentType, MessageRating[]>>({
  //   sustainability: [],
  //   indigenous: [],
  //   proposal: [],
  // });
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Proposal workflow state
  const [workflowPlan, setWorkflowPlan] = useState<WorkflowPlan | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['contacts']));
  const [editData, setEditData] = useState<Partial<WorkflowPlan>>({});
  const [executing, setExecuting] = useState(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [threads, activeAgent]);

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
      } else if (agent === 'proposal') {
        initialMessage = `What are the steps in the proposal workflow for a project at ${locationData?.address || 'this location'}?`;
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

  useEffect(() => {
    if (isOpen && !threads[activeAgent].threadId && !threads[activeAgent].loading) {
      if (activeAgent === 'proposal') {
        // Auto-generate workflow for proposal tab
        generateWorkflowAuto();
      } else {
        initializeAgent(activeAgent);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, activeAgent]);

  const generateWorkflowAuto = async () => {
    setThreads(prev => ({
      ...prev,
      proposal: { ...prev.proposal, loading: true }
    }));

    try {
      const proposalRequest = {
        location: locationData?.address || 'Location',
        land_use: 'Sustainable Development Initiative',
        objectives: 'Community-centered development integrating indigenous perspectives and sustainability practices',
        timeframe: '2-3 years',
      };

      const response = await fetch('http://localhost:8000/workflow/generate-action-plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(proposalRequest),
      });

      if (!response.ok) throw new Error('Failed to generate workflow');

      const plan = await response.json();
      
      // Ensure at least 1 contact exists
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
      setExpandedSections(new Set(['proposal']));

      // Create initial chat message
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

You can:
• Chat to add/modify contacts ("add John Doe as director")
• Edit stakeholder details and emails below
• Ask about the proposal
• Execute when ready!

What would you like to adjust?`
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

  const parseAndApplyChatCommand = (userMessage: string) => {
    const lowerMsg = userMessage.toLowerCase();
    
    // Command: Add a contact
    if (lowerMsg.includes('add') && (lowerMsg.includes('contact') || lowerMsg.includes('stakeholder'))) {
      // Extract name if provided
      const nameMatch = userMessage.match(/(?:add|contact|stakeholder).*?(?:named|called|is)\s+([A-Za-z\s]+?)(?:\s+as|\s+from|$)/i);
      const name = nameMatch?.[1]?.trim() || 'New Stakeholder';
      
      const newContact: ProposalContact = {
        role: name,
        reason: 'Added via chat',
        email: 'contact@example.com',
      };
      
      setEditData(prev => ({
        ...prev,
        contacts: {
          ...prev.contacts!,
          count: (prev.contacts?.count || 0) + 1,
          suggested_stakeholders: [
            ...(prev.contacts?.suggested_stakeholders || []),
            newContact
          ]
        }
      }));
      
      return `Added "${name}" to contacts. You can edit their role and email below.`;
    }
    
    // Command: Modify contact email
    if (lowerMsg.includes('email') && (lowerMsg.includes('change') || lowerMsg.includes('update') || lowerMsg.includes('to'))) {
      const emailMatch = userMessage.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/);
      if (emailMatch && editData.contacts?.suggested_stakeholders.length) {
        const newEmail = emailMatch[1];
        const lastContact = editData.contacts.suggested_stakeholders.length - 1;
        
        setEditData(prev => ({
          ...prev,
          contacts: {
            ...prev.contacts!,
            suggested_stakeholders: prev.contacts!.suggested_stakeholders.map((c, i) =>
              i === lastContact ? { ...c, email: newEmail } : c
            )
          }
        }));
        
        return `Updated contact email to ${newEmail}.`;
      }
    }
    
    // Command: Modify proposal/add meeting request
    if (lowerMsg.includes('meeting') || lowerMsg.includes('schedule') || lowerMsg.includes('consultation')) {
      // Detect if they want to book with a specific contact
      const contactMatch = userMessage.match(/with\s+([A-Za-z\s]+?)(?:\s+to|\s+for|$)/i);
      const contactName = contactMatch?.[1]?.trim();
      
      return `Great! I'll note that you want to schedule a meeting${contactName ? ` with ${contactName}` : ''}. When you execute the workflow, I'll automatically book the meeting and send calendar invites to all stakeholders.`;
    }
    
    // Command: Modify email/proposal content
    if (lowerMsg.includes('email') && (lowerMsg.includes('add') || lowerMsg.includes('mention') || lowerMsg.includes('include'))) {
      return `You can edit the email drafts below to include any additional information or context you'd like to add.`;
    }
    
    return null;
  };

  const executeWorkflow = async () => {
    if (!editData.contacts?.suggested_stakeholders.length) {
      alert('No contacts to process');
      return;
    }

    setExecuting(true);
    try {
      const threadId = `workflow-${Date.now()}`;
      
      // Add contacts
      for (const contact of editData.contacts.suggested_stakeholders) {
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

      // Request full outreach
      const outreachResponse = await fetch(`http://localhost:8000/workflow/full-outreach?threadid=${threadId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          proposal_title: editData.proposal?.title || 'Workflow Proposal',
          event_type_name: 'Community Consultation',
        }),
      });

      if (!outreachResponse.ok) throw new Error('Failed to request outreach');
      const outreachResult = await outreachResponse.json();

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

      alert('✅ Workflow executed!\n📧 Emails sent\n📅 Meetings booked\n📢 Slack notifications sent');
      setWorkflowPlan(null);
      setEditData({});
    } catch (error) {
      console.error('Error executing workflow:', error);
      alert('Failed to execute workflow');
    } finally {
      setExecuting(false);
    }
  };

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
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

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    const currentThread = threads[activeAgent];
    if (!currentThread.threadId) {
      if (activeAgent === 'proposal') {
        await generateWorkflowAuto();
      } else {
        await initializeAgent(activeAgent);
      }
      return;
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

      // Parse chat commands
      const commandResponse = parseAndApplyChatCommand(userMessage);
      
      // Simulate assistant response
      setTimeout(() => {
        setThreads(prev => ({
          ...prev,
          proposal: {
            ...prev.proposal,
            messages: [
              ...prev.proposal.messages,
              {
                role: 'assistant',
                content: commandResponse || `I've noted: "${userMessage}"

You can edit any details in the workflow sections below. I'll automatically:
• Book calendar meetings with all stakeholders
• Send personalized emails from sustainability + indigenous context
• Post team coordination messages to Slack

Feel free to adjust the contacts and emails, then click "Execute" when ready!`
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

  // Rating functions (currently unused but kept for future feature)
  // const handleRating = async (messageIndex: number, rating: 1 | -1) => {
  //   const currentThread = threads[activeAgent];
  //   if (!currentThread.threadId) return;

  //   // Find the user message and agent response
  //   const userMessage = currentThread.messages[messageIndex - 1]?.content || '';
  //   const agentResponse = currentThread.messages[messageIndex]?.content || '';

  //   // Update local state
  //   setRatings(prev => ({
  //     ...prev,
  //     [activeAgent]: [
  //       ...prev[activeAgent].filter(r => r.messageIndex !== messageIndex),
  //       { messageIndex, rating }
  //     ]
  //   }));

  //   // Track with Amplitude
  //   const location: LocationData | undefined = locationData ? {
  //     lat: locationData.lat,
  //     lon: locationData.lon,
  //     territory: locationData.territory,
  //     address: locationData.address,
  //   } : undefined;

  //   trackAgentResponseRated(
  //     activeAgent,
  //     currentThread.threadId,
  //     messageIndex,
  //     rating,
  //     userMessage,
  //     agentResponse,
  //     location
  //   );

  //   // Send to backend for storage and AI analysis
  //   try {
  //     const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  //     await fetch(`${API_BASE_URL}/api/ratings`, {
  //       method: 'POST',
  //       headers: {
  //         'Content-Type': 'application/json',
  //       },
  //       body: JSON.stringify({
  //         user_id: getDeviceId(),
  //         thread_id: currentThread.threadId,
  //         agent_type: activeAgent,
  //         message_index: messageIndex,
  //         rating,
  //         context: {
  //           user_message: userMessage,
  //           agent_response: agentResponse,
  //           location: locationData ? {
  //             lat: locationData.lat,
  //             lon: locationData.lon,
  //           } : undefined,
  //         }
  //       }),
  //     });
  //   } catch (error) {
  //     console.error('Failed to save rating:', error);
  //   }
  // };

  // const getRatingForMessage = (messageIndex: number): 1 | -1 | null => {
  //   const rating = ratings[activeAgent].find(r => r.messageIndex === messageIndex);
  //   return rating ? rating.rating : null;
  // };

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
              {activeAgent === 'proposal' ? (
                // Proposal Workflow Generator
                workflowPlan ? (
                  // Workflow Display
                  <div className="flex-1 overflow-y-auto p-4 space-y-3">
                    {/* Show sustainability and indigenous history */}
                    <div className="bg-gray-800 rounded-lg p-3 text-xs">
                      <div className="font-semibold text-blue-400 mb-2">💡 Insights from Agents</div>
                      <div className="space-y-2 text-gray-300">
                        {threads.sustainability.messages.length > 0 && (
                          <div>
                            <div className="font-medium text-slate-300">Sustainability Agent:</div>
                            <div className="ml-2 text-gray-400">{threads.sustainability.messages[threads.sustainability.messages.length - 1].content.substring(0, 200)}...</div>
                          </div>
                        )}
                        {threads.indigenous.messages.length > 0 && (
                          <div>
                            <div className="font-medium text-slate-300">Indigenous Context Agent:</div>
                            <div className="ml-2 text-gray-400">{threads.indigenous.messages[threads.indigenous.messages.length - 1].content.substring(0, 200)}...</div>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Proposal */}
                    <div className="bg-gray-800 rounded-lg border border-gray-700">
                      <button
                        onClick={() => toggleSection('proposal')}
                        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-750 transition"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-lg">📋</span>
                          <div className="text-left">
                            <div className="font-semibold text-white text-sm">{editData.proposal?.title}</div>
                          </div>
                        </div>
                        {expandedSections.has('proposal') ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                      {expandedSections.has('proposal') && (
                        <div className="px-4 py-3 bg-gray-750 border-t border-gray-700 text-xs text-gray-300 max-h-40 overflow-y-auto">
                          {editData.proposal?.content}
                        </div>
                      )}
                    </div>

                    {/* Contacts */}
                    <div className="bg-gray-800 rounded-lg border border-gray-700">
                      <button
                        onClick={() => toggleSection('contacts')}
                        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-750 transition"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-lg">👥</span>
                          <div className="text-left">
                            <div className="font-semibold text-white text-sm">Stakeholders ({editData.contacts?.count || 0})</div>
                          </div>
                        </div>
                        {expandedSections.has('contacts') ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                      {expandedSections.has('contacts') && (
                        <div className="px-4 py-3 bg-gray-750 border-t border-gray-700 space-y-2 max-h-40 overflow-y-auto">
                          {editData.contacts?.suggested_stakeholders.map((contact: ProposalContact, idx: number) => (
                            <div key={idx} className="bg-gray-700 rounded p-2 text-xs space-y-1">
                              <input
                                type="text"
                                value={contact.role}
                                onChange={(e) => updateContact(idx, 'role', e.target.value)}
                                className="w-full px-2 py-1 bg-gray-600 border border-gray-500 rounded text-white text-xs focus:outline-none focus:border-blue-500"
                              />
                              <input
                                type="text"
                                value={contact.email}
                                onChange={(e) => updateContact(idx, 'email', e.target.value)}
                                className="w-full px-2 py-1 bg-gray-600 border border-gray-500 rounded text-white text-xs focus:outline-none focus:border-blue-500 mb-1"
                              />
                              <button onClick={() => removeContact(idx)} className="text-red-400 hover:text-red-300 flex items-center gap-1">
                                <Trash2 className="w-3 h-3" /> Remove
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Emails */}
                    <div className="bg-gray-800 rounded-lg border border-gray-700">
                      <button
                        onClick={() => toggleSection('emails')}
                        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-750 transition"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-lg">📧</span>
                          <div className="text-left">
                            <div className="font-semibold text-white text-sm">Email Drafts ({editData.emails?.count || 0})</div>
                          </div>
                        </div>
                        {expandedSections.has('emails') ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                      {expandedSections.has('emails') && (
                        <div className="px-4 py-3 bg-gray-750 border-t border-gray-700 space-y-2 max-h-40 overflow-y-auto text-xs">
                          {editData.emails?.drafts.map((email: { to: string; subject: string; body: string }, idx: number) => (
                            <div key={idx} className="bg-gray-700 rounded p-2">
                              <div className="font-semibold text-blue-300">{email.subject}</div>
                              <div className="text-gray-400 text-xs">to: {email.to}</div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  // Workflow Generation Form
                  <div className="flex-1 overflow-y-auto p-4 space-y-3">
                    <div>
                      <label className="block text-xs font-medium text-slate-300 mb-1">Location</label>
                      <input
                        type="text"
                        value={formData.location}
                        onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                        className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded-lg text-white text-xs focus:outline-none focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-300 mb-1">Land Use</label>
                      <input
                        type="text"
                        value={formData.land_use}
                        onChange={(e) => setFormData({ ...formData, land_use: e.target.value })}
                        className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded-lg text-white text-xs focus:outline-none focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-300 mb-1">Objectives</label>
                      <textarea
                        value={formData.objectives}
                        onChange={(e) => setFormData({ ...formData, objectives: e.target.value })}
                        rows={2}
                        className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded-lg text-white text-xs focus:outline-none focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-300 mb-1">Timeframe</label>
                      <input
                        type="text"
                        value={formData.timeframe}
                        onChange={(e) => setFormData({ ...formData, timeframe: e.target.value })}
                        className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded-lg text-white text-xs focus:outline-none focus:border-blue-500"
                      />
                    </div>
                  </div>
                )
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
              {activeAgent === 'proposal' ? (
                workflowPlan ? (
                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        setWorkflowPlan(null);
                        setEditData({});
                      }}
                      className="flex-1 bg-gray-700 hover:bg-gray-600 text-white px-3 py-2 rounded text-sm transition"
                    >
                      ← Back
                    </button>
                    <button
                      onClick={executeWorkflow}
                      disabled={executing}
                      className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white px-3 py-2 rounded text-sm transition font-medium"
                    >
                      {executing ? '⏳ Executing...' : '✅ Execute'}
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={generateWorkflow}
                    disabled={workflowLoading}
                    className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white px-3 py-2 rounded text-sm transition font-medium"
                  >
                    {workflowLoading ? '🔄 Generating...' : '🚀 Generate Workflow'}
                  </button>
                )
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
