from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.research_runtime import Priority, RequestedBy, ResultStatus, RunEventStatus, RunState, TaskType


TaskRunStatus = Literal["running", "completed", "failed", "awaiting_review"]


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
    used_mock_fallback: bool = False
    fallback_reason: Optional[str] = None
    elapsed_ms: Optional[float] = None
    event_count: int = 0
    artifact_count: int = 0
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
