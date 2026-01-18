/**
 * Proposal Workflow API Client
 * Handles communication with /proposal-workflow endpoints
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface WorkflowInstruction {
  id: string;
  type: 'email' | 'meeting' | 'slack' | 'milestone';
  target: string;
  subject: string;
  body: string;
  status: 'pending' | 'completed' | 'failed';
  metadata?: Record<string, string | number | boolean | null>;
}

export interface ProposalWorkflowState {
  thread_id: string;
  proposal_title: string;
  location: string;
  email_sender: string;
  meeting_recipient: string;
  stakeholders: Record<string, { role: string; context: string; added_at: string }>;
  instructions: WorkflowInstruction[];
  summary: {
    thread_id: string;
    proposal_title: string;
    location: string;
    email_sender: string;
    meeting_recipient: string;
    stakeholder_count: number;
    email_count: number;
    meeting_count: number;
    total_instructions: number;
    last_updated: string;
    created_at: string;
  };
}

export interface InitWorkflowRequest {
  proposal_title: string;
  location: string;
  sustainability_context: string;
  indigenous_context: string;
}

export interface WorkflowMessageRequest {
  thread_id: string;
  user_message: string;
}

export interface WorkflowConfigRequest {
  thread_id: string;
  email_sender?: string;
  meeting_recipient?: string;
}

export interface WorkflowMessageResponse {
  thread_id: string;
  user_message: string;
  response: string;
  instructions: WorkflowInstruction[];
  stakeholder_count: number;
  email_count: number;
  meeting_count: number;
  summary: string | Record<string, string | number | boolean | null>;
}

export interface WorkflowExecuteResponse {
  thread_id: string;
  executed: number;
  failed: number;
  total: number;
  results: Array<{
    instruction_id: string;
    type: string;
    target: string;
    success: boolean;
    message: string;
    timestamp: string;
  }>;
  execution_summary: {
    success_rate: string;
    timestamp: string;
    status: 'completed' | 'failed';
  };
}

/**
 * Initialize a new proposal workflow
 */
export async function initializeProposalWorkflow(
  request: InitWorkflowRequest
): Promise<{ thread_id: string; instructions: WorkflowInstruction[] }> {
  const response = await fetch(`${API_BASE_URL}/proposal-workflow/init`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Failed to initialize workflow: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Add a message to workflow and get regenerated instructions
 */
export async function addWorkflowMessage(
  request: WorkflowMessageRequest
): Promise<WorkflowMessageResponse> {
  const response = await fetch(`${API_BASE_URL}/proposal-workflow/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Failed to add message: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get current workflow status
 */
export async function getWorkflowStatus(threadId: string): Promise<ProposalWorkflowState> {
  const response = await fetch(`${API_BASE_URL}/proposal-workflow/status/${threadId}`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Failed to get status: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Update workflow configuration (email sender, meeting recipient)
 */
export async function updateWorkflowConfig(
  request: WorkflowConfigRequest
): Promise<WorkflowMessageResponse> {
  const response = await fetch(`${API_BASE_URL}/proposal-workflow/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Failed to update config: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Execute all workflow instructions
 */
export async function executeWorkflow(
  threadId: string,
  userConfirmation: boolean = true
): Promise<WorkflowExecuteResponse> {
  const response = await fetch(`${API_BASE_URL}/proposal-workflow/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      thread_id: threadId,
      user_confirmation: userConfirmation,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to execute workflow: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Delete a workflow thread
 */
export async function deleteWorkflowThread(threadId: string): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE_URL}/proposal-workflow/delete/${threadId}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Failed to delete thread: ${response.statusText}`);
  }

  return response.json();
}

/**
 * List all active workflow threads
 */
export interface WorkflowThreadInfo {
  thread_id: string;
  proposal_title: string;
  created_at: string;
  message_count: number;
}

export async function listWorkflowThreads(): Promise<{ count: number; threads: WorkflowThreadInfo[] }> {
  const response = await fetch(`${API_BASE_URL}/proposal-workflow/threads`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Failed to list threads: ${response.statusText}`);
  }

  return response.json();
}
