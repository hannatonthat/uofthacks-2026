/**
 * Workflow API client for instruction generation, refinement, and execution
 */

export interface WorkflowInstruction {
  id: string;
  type: 'email' | 'meeting' | 'slack' | 'milestone';
  target: string;
  subject: string;
  body: string;
  duration_minutes?: number;
  description?: string;
  status: 'pending' | 'executed' | 'failed';
  metadata?: Record<string, string | number | boolean | null>;
}

export interface GenerateInstructionsRequest {
  sustainability_context: string;
  indigenous_context: string;
  proposal_title: string;
  location: string;
  suggested_stakeholders?: Array<{
    name?: string;
    role: string;
    email: string;
    reason?: string;
  }>;
}

export interface RefineInstructionsRequest {
  thread_id: string;
  user_message: string;
  instruction_index?: number;
}

export interface ExecuteWorkflowRequest {
  thread_id: string;
  instructions: Array<Record<string, string | number | boolean | null>>;
  user_confirmation: boolean;
}

export interface WorkflowResponse {
  thread_id: string;
  proposal_title?: string;
  location?: string;
  instructions?: WorkflowInstruction[];
  summary?: string;
  status?: string;
  message?: string;
}

export interface ExecutionResult {
  thread_id: string;
  total_instructions: number;
  executed: number;
  failed: number;
  results: Array<{
    instruction_id: string;
    success: boolean;
    message: string;
    result?: string | number | boolean | null;
    error?: string;
  }>;
  execution_summary: {
    success_count: number;
    failure_count: number;
  };
  status: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Generate initial workflow instructions from sustainability + indigenous context
 */
export async function generateWorkflowInstructions(
  request: GenerateInstructionsRequest
): Promise<WorkflowResponse> {
  const response = await fetch(`${API_BASE_URL}/workflow/generate-instructions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Failed to generate instructions: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Refine workflow by adding/modifying instructions via chat
 */
export async function refineWorkflowInstructions(
  request: RefineInstructionsRequest
): Promise<WorkflowResponse> {
  const response = await fetch(`${API_BASE_URL}/workflow/refine-instructions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Failed to refine instructions: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Execute workflow instructions against Gmail, Google Calendar, Slack
 */
export async function executeWorkflow(
  request: ExecuteWorkflowRequest
): Promise<ExecutionResult> {
  const response = await fetch(`${API_BASE_URL}/workflow/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Failed to execute workflow: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get workflow status
 */
export async function getWorkflowStatus(threadId: string): Promise<WorkflowResponse> {
  const response = await fetch(`${API_BASE_URL}/workflow/status/${threadId}`);

  if (!response.ok) {
    throw new Error(`Failed to get workflow status: ${response.statusText}`);
  }

  return response.json();
}
