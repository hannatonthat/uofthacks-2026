'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, Plus, Trash2, CheckCircle, AlertCircle } from 'lucide-react';

interface ProposalSection {
  title: string;
  content: string;
}

interface Contact {
  role: string;
  reason: string;
  email: string;
  suggested_email?: string;
}

interface EmailDraft {
  to: string;
  subject: string;
  body: string;
  stakeholder_email?: string;
  stakeholder_role?: string;
}

interface Meeting {
  title: string;
  attendees: string[];
  duration_minutes: number;
  purpose: string;
}

interface SlackNotification {
  channel: string;
  message: string;
  priority: string;
}

interface WorkflowPlan {
  proposal: ProposalSection;
  contacts: {
    count: number;
    suggested_stakeholders: Contact[];
  };
  emails: {
    count: number;
    drafts: EmailDraft[];
  };
  meetings: {
    count: number;
    suggested_meetings: Meeting[];
  };
  notifications: {
    count: number;
    slack_messages: SlackNotification[];
  };
  workflow_summary: {
    next_steps: string[];
    key_principles: string[];
  };
}

export default function WorkflowBuilder() {
  const [loading, setLoading] = useState(false);
  const [workflowPlan, setWorkflowPlan] = useState<WorkflowPlan | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['proposal']));
  const [editMode, setEditMode] = useState<Record<string, boolean>>({});
  const [editData, setEditData] = useState<Partial<WorkflowPlan>>({});
  const [executing, setExecuting] = useState(false);

  // Form inputs for generating workflow
  const [formData, setFormData] = useState({
    location: 'Traditional Haudenosaunee Territory',
    land_use: 'Sustainable Forest Management',
    objectives: 'Preserve traditional land practices while supporting modern conservation',
    timeframe: '2-3 years',
  });

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
  };

  const generateWorkflow = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/workflow/generate-action-plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      if (!response.ok) throw new Error('Failed to generate workflow');

      const plan = await response.json();
      setWorkflowPlan(plan);
      setEditData(JSON.parse(JSON.stringify(plan))); // Deep copy for editing
      setExpandedSections(new Set(['proposal', 'contacts', 'emails']));
    } catch (error) {
      console.error('Error generating workflow:', error);
      alert('Failed to generate workflow. Check console for details.');
    } finally {
      setLoading(false);
    }
  };

  const addContact = () => {
    if (!editData.contacts) return;
    const newContact: Contact = {
      role: 'New Stakeholder',
      reason: 'Reason for contact',
      email: 'stakeholder@example.com',
    };
    setEditData({
      ...editData,
      contacts: {
        ...editData.contacts,
        count: editData.contacts.count + 1,
        suggested_stakeholders: [...editData.contacts.suggested_stakeholders, newContact],
      },
    });
  };

  const removeContact = (index: number) => {
    if (!editData.contacts) return;
    const updated = editData.contacts.suggested_stakeholders.filter((_, i) => i !== index);
    setEditData({
      ...editData,
      contacts: {
        ...editData.contacts,
        count: updated.length,
        suggested_stakeholders: updated,
      },
    });
  };

  const updateContact = (index: number, field: keyof Contact, value: string) => {
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

  const updateEmail = (index: number, field: keyof EmailDraft, value: string) => {
    if (!editData.emails) return;
    const updated = [...editData.emails.drafts];
    updated[index] = { ...updated[index], [field]: value };
    setEditData({
      ...editData,
      emails: {
        ...editData.emails,
        drafts: updated,
      },
    });
  };

  const executeWorkflow = async () => {
    if (!editData.contacts?.suggested_stakeholders.length) {
      alert('No contacts to process');
      return;
    }

    setExecuting(true);
    try {
      // Step 1: Create workflow thread and add contacts
      const threadId = `workflow-${Date.now()}`;
      
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

      // Step 2: Request full outreach
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

      // Step 3: Approve the action
      const confirmResponse = await fetch('http://localhost:8000/workflow/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action_id: outreachResult.action_id,
          approved: true,
        }),
      });

      if (!confirmResponse.ok) throw new Error('Failed to approve action');

      alert('✅ Workflow executed successfully!\n\n📧 Emails sent\n📅 Meetings booked\n📢 Slack notifications sent');
      setWorkflowPlan(null);
      setEditData({});
    } catch (error) {
      console.error('Error executing workflow:', error);
      alert('Failed to execute workflow. Check console for details.');
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">🌍 Workflow Builder</h1>
          <p className="text-slate-400">Generate indigenous-informed proposals and execute complete outreach workflows</p>
        </div>

        {/* Generator Section */}
        {!workflowPlan ? (
          <div className="bg-slate-800 rounded-lg p-8 border border-slate-700 shadow-lg">
            <h2 className="text-2xl font-semibold text-white mb-6">Generate Workflow Plan</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Location</label>
                <input
                  type="text"
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Land Use / Initiative</label>
                <input
                  type="text"
                  value={formData.land_use}
                  onChange={(e) => setFormData({ ...formData, land_use: e.target.value })}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-slate-300 mb-2">Objectives</label>
                <textarea
                  value={formData.objectives}
                  onChange={(e) => setFormData({ ...formData, objectives: e.target.value })}
                  rows={3}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Timeframe</label>
                <input
                  type="text"
                  value={formData.timeframe}
                  onChange={(e) => setFormData({ ...formData, timeframe: e.target.value })}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>

            <button
              onClick={generateWorkflow}
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white font-semibold py-3 px-6 rounded-lg transition flex items-center justify-center gap-2"
            >
              {loading ? '🔄 Generating...' : '🚀 Generate Workflow'}
            </button>
          </div>
        ) : (
          <>
            {/* Workflow Sections */}
            <div className="space-y-4 mb-8">
              {/* Proposal Section */}
              <div className="bg-slate-800 rounded-lg border border-slate-700 shadow-lg overflow-hidden">
                <button
                  onClick={() => toggleSection('proposal')}
                  className="w-full px-6 py-4 flex items-center justify-between hover:bg-slate-750 transition"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">📋</span>
                    <div className="text-left">
                      <h3 className="text-lg font-semibold text-white">Proposal</h3>
                      <p className="text-sm text-slate-400">{editData.proposal?.title}</p>
                    </div>
                  </div>
                  {expandedSections.has('proposal') ? (
                    <ChevronUp className="text-slate-400" />
                  ) : (
                    <ChevronDown className="text-slate-400" />
                  )}
                </button>

                {expandedSections.has('proposal') && (
                  <div className="px-6 py-4 bg-slate-750 border-t border-slate-700">
                    <p className="text-slate-300 whitespace-pre-wrap text-sm leading-relaxed max-h-96 overflow-y-auto">
                      {editData.proposal?.content}
                    </p>
                  </div>
                )}
              </div>

              {/* Contacts Section */}
              <div className="bg-slate-800 rounded-lg border border-slate-700 shadow-lg overflow-hidden">
                <button
                  onClick={() => toggleSection('contacts')}
                  className="w-full px-6 py-4 flex items-center justify-between hover:bg-slate-750 transition"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">👥</span>
                    <div className="text-left">
                      <h3 className="text-lg font-semibold text-white">Stakeholders</h3>
                      <p className="text-sm text-slate-400">{editData.contacts?.count} identified</p>
                    </div>
                  </div>
                  {expandedSections.has('contacts') ? (
                    <ChevronUp className="text-slate-400" />
                  ) : (
                    <ChevronDown className="text-slate-400" />
                  )}
                </button>

                {expandedSections.has('contacts') && (
                  <div className="px-6 py-4 bg-slate-750 border-t border-slate-700 space-y-4">
                    {editData.contacts?.suggested_stakeholders.map((contact, idx) => (
                      <div key={idx} className="bg-slate-700 rounded-lg p-4 space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <input
                              type="text"
                              value={contact.role}
                              onChange={(e) => updateContact(idx, 'role', e.target.value)}
                              className="w-full px-3 py-2 bg-slate-600 border border-slate-500 rounded text-white text-sm focus:outline-none focus:border-blue-500 mb-2"
                              placeholder="Role"
                            />
                            <input
                              type="text"
                              value={contact.email}
                              onChange={(e) => updateContact(idx, 'email', e.target.value)}
                              className="w-full px-3 py-2 bg-slate-600 border border-slate-500 rounded text-white text-sm focus:outline-none focus:border-blue-500 mb-2"
                              placeholder="Email"
                            />
                            <textarea
                              value={contact.reason}
                              onChange={(e) => updateContact(idx, 'reason', e.target.value)}
                              rows={2}
                              className="w-full px-3 py-2 bg-slate-600 border border-slate-500 rounded text-white text-sm focus:outline-none focus:border-blue-500"
                              placeholder="Reason for contact"
                            />
                          </div>
                          <button
                            onClick={() => removeContact(idx)}
                            className="ml-3 p-2 hover:bg-red-600 rounded transition"
                          >
                            <Trash2 className="w-5 h-5 text-red-400" />
                          </button>
                        </div>
                      </div>
                    ))}
                    <button
                      onClick={addContact}
                      className="w-full py-2 px-4 bg-slate-600 hover:bg-slate-500 text-white rounded-lg flex items-center justify-center gap-2 transition"
                    >
                      <Plus className="w-4 h-4" /> Add Stakeholder
                    </button>
                  </div>
                )}
              </div>

              {/* Emails Section */}
              <div className="bg-slate-800 rounded-lg border border-slate-700 shadow-lg overflow-hidden">
                <button
                  onClick={() => toggleSection('emails')}
                  className="w-full px-6 py-4 flex items-center justify-between hover:bg-slate-750 transition"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">📧</span>
                    <div className="text-left">
                      <h3 className="text-lg font-semibold text-white">Email Drafts</h3>
                      <p className="text-sm text-slate-400">{editData.emails?.count} emails</p>
                    </div>
                  </div>
                  {expandedSections.has('emails') ? (
                    <ChevronUp className="text-slate-400" />
                  ) : (
                    <ChevronDown className="text-slate-400" />
                  )}
                </button>

                {expandedSections.has('emails') && (
                  <div className="px-6 py-4 bg-slate-750 border-t border-slate-700 space-y-4">
                    {editData.emails?.drafts.map((email, idx) => (
                      <div key={idx} className="bg-slate-700 rounded-lg p-4 space-y-3">
                        <div>
                          <label className="block text-xs font-medium text-slate-300 mb-1">To</label>
                          <input
                            type="text"
                            value={email.to}
                            onChange={(e) => updateEmail(idx, 'to', e.target.value)}
                            className="w-full px-3 py-2 bg-slate-600 border border-slate-500 rounded text-white text-sm focus:outline-none focus:border-blue-500"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-slate-300 mb-1">Subject</label>
                          <input
                            type="text"
                            value={email.subject}
                            onChange={(e) => updateEmail(idx, 'subject', e.target.value)}
                            className="w-full px-3 py-2 bg-slate-600 border border-slate-500 rounded text-white text-sm focus:outline-none focus:border-blue-500"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-slate-300 mb-1">Body</label>
                          <textarea
                            value={email.body}
                            onChange={(e) => updateEmail(idx, 'body', e.target.value)}
                            rows={4}
                            className="w-full px-3 py-2 bg-slate-600 border border-slate-500 rounded text-white text-sm focus:outline-none focus:border-blue-500"
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Meetings Section */}
              <div className="bg-slate-800 rounded-lg border border-slate-700 shadow-lg overflow-hidden">
                <button
                  onClick={() => toggleSection('meetings')}
                  className="w-full px-6 py-4 flex items-center justify-between hover:bg-slate-750 transition"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">📅</span>
                    <div className="text-left">
                      <h3 className="text-lg font-semibold text-white">Meetings</h3>
                      <p className="text-sm text-slate-400">{editData.meetings?.count} suggested</p>
                    </div>
                  </div>
                  {expandedSections.has('meetings') ? (
                    <ChevronUp className="text-slate-400" />
                  ) : (
                    <ChevronDown className="text-slate-400" />
                  )}
                </button>

                {expandedSections.has('meetings') && (
                  <div className="px-6 py-4 bg-slate-750 border-t border-slate-700 space-y-4">
                    {editData.meetings?.suggested_meetings.map((meeting, idx) => (
                      <div key={idx} className="bg-slate-700 rounded-lg p-4">
                        <h4 className="font-semibold text-white mb-2">{meeting.title}</h4>
                        <p className="text-sm text-slate-300 mb-2">{meeting.purpose}</p>
                        <div className="grid grid-cols-2 gap-2 text-xs text-slate-400">
                          <div>⏱️ {meeting.duration_minutes} minutes</div>
                          <div>👥 {meeting.attendees.length} attendees</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Notifications Section */}
              <div className="bg-slate-800 rounded-lg border border-slate-700 shadow-lg overflow-hidden">
                <button
                  onClick={() => toggleSection('notifications')}
                  className="w-full px-6 py-4 flex items-center justify-between hover:bg-slate-750 transition"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">📢</span>
                    <div className="text-left">
                      <h3 className="text-lg font-semibold text-white">Slack Notifications</h3>
                      <p className="text-sm text-slate-400">{editData.notifications?.count} messages</p>
                    </div>
                  </div>
                  {expandedSections.has('notifications') ? (
                    <ChevronUp className="text-slate-400" />
                  ) : (
                    <ChevronDown className="text-slate-400" />
                  )}
                </button>

                {expandedSections.has('notifications') && (
                  <div className="px-6 py-4 bg-slate-750 border-t border-slate-700 space-y-4">
                    {editData.notifications?.slack_messages.map((notif, idx) => (
                      <div key={idx} className="bg-slate-700 rounded-lg p-4">
                        <div className="font-semibold text-white mb-2">{notif.channel}</div>
                        <p className="text-sm text-slate-300 whitespace-pre-wrap">{notif.message}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-4">
              <button
                onClick={() => {
                  setWorkflowPlan(null);
                  setEditData({});
                }}
                className="flex-1 bg-slate-700 hover:bg-slate-600 text-white font-semibold py-3 px-6 rounded-lg transition"
              >
                ← Back
              </button>
              <button
                onClick={executeWorkflow}
                disabled={executing}
                className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-slate-600 text-white font-semibold py-3 px-6 rounded-lg transition flex items-center justify-center gap-2"
              >
                {executing ? '⏳ Executing...' : '✅ Execute Workflow'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
