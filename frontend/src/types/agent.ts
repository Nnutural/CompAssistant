export type AgentTaskType =
  | 'competition_recommendation'
  | 'competition_eligibility_check'
  | 'competition_timeline_plan'
  | 'research_plan'
  | 'source_discovery'
  | 'evidence_extraction'
  | 'synthesis'
  | 'review'
  | 'report_draft'
  | 'schema_validation'
  | 'general'

export type AgentTaskRunStatus = 'running' | 'completed' | 'failed' | 'awaiting_review'

export type AgentResultStatus = 'draft' | 'completed' | 'blocked' | 'needs_human'

export type AgentRunState =
  | 'received'
  | 'planning'
  | 'retrieving_local_context'
  | 'reasoning'
  | 'validating_output'
  | 'persisting_artifacts'
  | 'completed'
  | 'failed'
  | 'awaiting_review'

export type AgentEventStatus = 'entered' | 'completed' | 'error' | 'warning' | 'fallback' | 'info'

export interface AgentTaskCreateRequest {
  task_type: AgentTaskType
  objective?: string
  payload: Record<string, unknown>
  task_id?: string
  session_id?: string
  requested_by?: 'user' | 'codex' | 'system' | 'agent'
  priority?: 'low' | 'normal' | 'high'
  constraints?: string[]
  dry_run?: boolean
}

export interface AgentTaskResultSummary {
  status?: AgentResultStatus | null
  summary?: string | null
  finding_count: number
  follow_up_items: string[]
  blockers: string[]
}

export interface AgentTaskStatusResponse {
  run_id: string
  task_id: string
  session_id: string
  ledger_id: string
  task_type?: AgentTaskType | null
  status: AgentTaskRunStatus
  current_state?: AgentRunState | null
  completed_states: AgentRunState[]
  error_stage?: AgentRunState | null
  result: AgentTaskResultSummary
  used_mock_fallback: boolean
  fallback_reason?: string | null
  elapsed_ms?: number | null
  event_count: number
  artifact_count: number
  created_at: string
  updated_at?: string | null
}

export interface AgentTaskEventItem {
  event_id: string
  run_id: string
  state: AgentRunState
  status: AgentEventStatus
  message: string
  actor?: string | null
  detail?: Record<string, unknown> | null
  created_at: string
}

export interface AgentTaskEventsResponse {
  run_id: string
  task_id: string
  task_type?: AgentTaskType | null
  current_state?: AgentRunState | null
  items: AgentTaskEventItem[]
}

export interface AgentTaskArtifactItem {
  artifact_id: string
  run_id: string
  artifact_type: string
  title: string
  payload?: unknown
  ref?: string | null
  created_at?: string | null
}

export interface AgentTaskArtifactsResponse {
  run_id: string
  task_id: string
  task_type?: AgentTaskType | null
  current_state?: AgentRunState | null
  items: AgentTaskArtifactItem[]
}

export type AgentTaskSummary = AgentTaskStatusResponse
