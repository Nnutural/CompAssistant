from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.research_runtime import (
    ControlAction,
    Priority,
    RequestedBy,
    ResultStatus,
    RuntimeMode,
    RunEventStatus,
    RunState,
    TaskType,
)


TaskRunStatus = Literal["queued", "running", "completed", "cancelled", "failed", "awaiting_review"]
ReviewDecision = Literal["accept", "reject", "annotate"]


class AgentTaskApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentTaskCreateRequest(AgentTaskApiModel):
    task_type: TaskType
    objective: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    task_id: Optional[str] = None
    session_id: Optional[str] = None
    requested_by: RequestedBy = "user"
    priority: Priority = "normal"
    constraints: List[str] = Field(default_factory=list)
    dry_run: bool = False


class AgentTaskResultSummary(AgentTaskApiModel):
    status: Optional[ResultStatus] = None
    summary: Optional[str] = None
    finding_count: int = 0
    follow_up_items: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)


class AgentTaskStatusResponse(AgentTaskApiModel):
    run_id: str
    task_id: str
    session_id: str
    ledger_id: str
    task_type: Optional[TaskType] = None
    status: TaskRunStatus
    current_state: Optional[RunState] = None
    completed_states: List[RunState] = Field(default_factory=list)
    error_stage: Optional[RunState] = None
    result: AgentTaskResultSummary
    requested_runtime_mode: Optional[str] = None
    effective_runtime_mode: Optional[RuntimeMode] = None
    effective_model: Optional[str] = None
    provider_success_path: Optional[Literal["structured", "plain_json_fallback"]] = None
    used_mock_fallback: bool = False
    fallback_reason: Optional[str] = None
    elapsed_ms: Optional[float] = None
    event_count: int = 0
    artifact_count: int = 0
    available_actions: List[ControlAction] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None


class AgentTaskEventItem(AgentTaskApiModel):
    event_id: str
    run_id: str
    state: RunState
    status: RunEventStatus
    message: str
    actor: Optional[str] = None
    detail: Optional[Dict[str, Any]] = None
    created_at: datetime


class AgentTaskEventsResponse(AgentTaskApiModel):
    run_id: str
    task_id: str
    task_type: Optional[TaskType] = None
    current_state: Optional[RunState] = None
    items: List[AgentTaskEventItem] = Field(default_factory=list)


class AgentTaskArtifactItem(AgentTaskApiModel):
    artifact_id: str
    run_id: str
    artifact_type: str
    title: str
    payload: Any = None
    ref: Optional[str] = None
    created_at: Optional[datetime] = None


class AgentTaskArtifactsResponse(AgentTaskApiModel):
    run_id: str
    task_id: str
    task_type: Optional[TaskType] = None
    current_state: Optional[RunState] = None
    items: List[AgentTaskArtifactItem] = Field(default_factory=list)


class AgentTaskHistoryItem(AgentTaskApiModel):
    run_id: str
    task_id: str
    session_id: str
    ledger_id: str
    task_type: Optional[TaskType] = None
    status: TaskRunStatus
    current_state: Optional[RunState] = None
    result_status: Optional[ResultStatus] = None
    result_summary: Optional[str] = None
    artifact_count: int = 0
    has_artifacts: bool = False
    awaiting_review: bool = False
    requested_runtime_mode: Optional[str] = None
    effective_runtime_mode: Optional[RuntimeMode] = None
    effective_model: Optional[str] = None
    provider_success_path: Optional[Literal["structured", "plain_json_fallback"]] = None
    used_mock_fallback: bool = False
    parent_run_id: Optional[str] = None
    available_actions: List[ControlAction] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None


class AgentTaskHistoryResponse(AgentTaskApiModel):
    items: List[AgentTaskHistoryItem] = Field(default_factory=list)
    total: int
    limit: int
    offset: int


class AgentTaskCancelRequest(AgentTaskApiModel):
    note: Optional[str] = None


class AgentTaskReviewRequest(AgentTaskApiModel):
    decision: ReviewDecision
    note: Optional[str] = None


class AgentTaskControlResponse(AgentTaskApiModel):
    action: ControlAction
    message: str
    task: AgentTaskStatusResponse


class AgentTaskRetryResponse(AgentTaskApiModel):
    action: Literal["retry"]
    source_run_id: str
    new_run: AgentTaskStatusResponse
    message: str
