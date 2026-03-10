from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


ReferenceKind = Literal["file", "doc", "schema", "dataset", "url", "note", "task", "ledger"]
OutputFormat = Literal["json", "markdown", "text", "artifact_bundle"]
TaskType = Literal[
    "competition_recommendation",
    "competition_eligibility_check",
    "competition_timeline_plan",
    "research_plan",
    "source_discovery",
    "evidence_extraction",
    "synthesis",
    "review",
    "report_draft",
    "schema_validation",
    "general",
]
RequestedBy = Literal["user", "codex", "system", "agent"]
Priority = Literal["low", "normal", "high"]
RuntimeMode = Literal["mock", "agents_sdk"]
ResultStatus = Literal["draft", "completed", "blocked", "needs_human"]
FindingConfidence = Literal["low", "medium", "high"]
ArtifactKind = Literal["file", "doc", "schema", "report", "note", "dataset", "ledger_entry"]
LedgerStatus = Literal["active", "paused", "completed", "archived"]
LedgerTaskStatus = Literal["queued", "running", "completed", "blocked", "cancelled"]
SourceType = Literal["doc", "paper", "web", "dataset", "interview", "note", "code"]
RunState = Literal[
    "received",
    "queued",
    "running",
    "planning",
    "retrieving_local_context",
    "reasoning",
    "validating_output",
    "persisting_artifacts",
    "completed",
    "cancelled",
    "failed",
    "awaiting_review",
]
RunEventStatus = Literal["entered", "completed", "error", "warning", "fallback", "info"]
ValidationIssueKind = Literal[
    "parse_error",
    "validation_error",
    "repair_warning",
    "runtime_error",
    "schema_compatibility_error",
    "provider_response_parse_error",
    "provider_exception",
]
ControlAction = Literal["retry", "cancel", "review_accept", "review_reject", "review_annotate"]


class ContractBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReferenceItem(ContractBaseModel):
    kind: ReferenceKind
    ref: str
    title: Optional[str] = None
    description: Optional[str] = None


class ExpectedOutput(ContractBaseModel):
    format: OutputFormat
    schema_ref: Optional[str] = None
    target_path: Optional[str] = None
    sections: List[str] = Field(default_factory=list)


class AgentTaskEnvelope(ContractBaseModel):
    contract_version: Literal["1.0"]
    task_id: str
    session_id: str
    workflow_id: Optional[str] = None
    task_type: TaskType
    requested_by: RequestedBy
    priority: Priority = "normal"
    objective: str
    payload: Dict[str, Any]
    context_refs: List[ReferenceItem] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    expected_output: Optional[ExpectedOutput] = None
    dry_run: bool = True
    created_at: Optional[datetime] = None


class AgentHandoff(ContractBaseModel):
    contract_version: Literal["1.0"]
    handoff_id: str
    task_id: str
    from_agent: str
    to_agent: str
    objective: str
    rationale: Optional[str] = None
    input_refs: List[ReferenceItem]
    constraints: List[str] = Field(default_factory=list)
    carry_forward_notes: List[str] = Field(default_factory=list)
    expected_output: Optional[ExpectedOutput] = None
    requested_at: Optional[datetime] = None


class FindingItem(ContractBaseModel):
    finding_id: Optional[str] = None
    claim: str
    evidence_refs: List[str] = Field(default_factory=list)
    confidence: FindingConfidence = "medium"


class ArtifactItem(ContractBaseModel):
    kind: ArtifactKind
    ref: str
    title: Optional[str] = None


class AgentResult(ContractBaseModel):
    contract_version: Literal["1.0"]
    task_id: str
    produced_by: str
    status: ResultStatus
    summary: str
    findings: List[FindingItem] = Field(default_factory=list)
    changed_paths: List[str] = Field(default_factory=list)
    artifacts: List[ArtifactItem] = Field(default_factory=list)
    follow_up_items: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
    completed_at: Optional[datetime] = None


class RunEvent(ContractBaseModel):
    event_id: str
    state: RunState
    status: RunEventStatus
    message: str
    actor: Optional[str] = None
    detail: Optional[Dict[str, Any]] = None
    created_at: datetime


class ValidationIssue(ContractBaseModel):
    stage: str
    kind: ValidationIssueKind
    message: str
    agent: Optional[str] = None
    detail: Optional[str] = None
    created_at: Optional[datetime] = None


class RuntimeArtifact(ContractBaseModel):
    artifact_id: str
    artifact_type: str
    title: str
    payload: Any
    created_at: Optional[datetime] = None


class ControlRecord(ContractBaseModel):
    action_id: str
    action: ControlAction
    actor: str
    note: Optional[str] = None
    related_run_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ResearchScope(ContractBaseModel):
    included_topics: List[str] = Field(default_factory=list)
    excluded_topics: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)


class LedgerTaskEntry(ContractBaseModel):
    task_id: str
    agent: str
    status: LedgerTaskStatus
    summary: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class SourceRecord(ContractBaseModel):
    source_id: str
    source_type: SourceType
    title: str
    locator: str
    credibility: Optional[FindingConfidence] = None
    captured_by: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class EvidenceRecord(ContractBaseModel):
    evidence_id: str
    source_id: str
    claim: str
    excerpt: str
    captured_by: str
    captured_at: Optional[datetime] = None
    related_task_id: Optional[str] = None


class RecommendationItem(ContractBaseModel):
    competition_id: int
    competition_name: str
    match_score: float
    reasons: List[str] = Field(default_factory=list)
    risk_notes: List[str] = Field(default_factory=list)
    focus_tags: List[str] = Field(default_factory=list)


class CompetitionRecommendationArtifact(ContractBaseModel):
    task_type: Literal["competition_recommendation"]
    profile_summary: str
    recommendations: List[RecommendationItem]
    risk_overview: List[str] = Field(default_factory=list)


class CompetitionEligibilityArtifact(ContractBaseModel):
    task_type: Literal["competition_eligibility_check"]
    competition_id: int
    competition_name: str
    eligibility_label: Literal["recommended", "borderline", "not_recommended"]
    is_eligible: bool
    missing_conditions: List[str] = Field(default_factory=list)
    attention_points: List[str] = Field(default_factory=list)
    rationale: List[str] = Field(default_factory=list)


class TimelineMilestone(ContractBaseModel):
    stage: str
    due_at: str
    goals: List[str] = Field(default_factory=list)
    deliverables: List[str] = Field(default_factory=list)


class CompetitionTimelineArtifact(ContractBaseModel):
    task_type: Literal["competition_timeline_plan"]
    competition_id: int
    competition_name: str
    deadline: str
    preparation_checklist: List[str] = Field(default_factory=list)
    milestones: List[TimelineMilestone] = Field(default_factory=list)
    stage_plan: List[str] = Field(default_factory=list)
    reverse_schedule: List[str] = Field(default_factory=list)


class ResearchLedger(ContractBaseModel):
    contract_version: Literal["1.0"]
    ledger_id: str
    session_id: str
    topic: str
    research_question: str
    status: LedgerStatus
    owner: Optional[str] = None
    parent_run_id: Optional[str] = None
    run_id: Optional[str] = None
    task_type: Optional[TaskType] = None
    current_state: Optional[RunState] = None
    completed_states: List[RunState] = Field(default_factory=list)
    error_stage: Optional[RunState] = None
    scope: ResearchScope
    hypotheses: List[str] = Field(default_factory=list)
    task_history: List[LedgerTaskEntry]
    source_registry: List[SourceRecord]
    evidence_log: List[EvidenceRecord]
    events: List[RunEvent] = Field(default_factory=list)
    raw_outputs: Dict[str, Any] = Field(default_factory=dict)
    repaired_outputs: Dict[str, Any] = Field(default_factory=dict)
    validation_errors: List[ValidationIssue] = Field(default_factory=list)
    parse_errors: List[ValidationIssue] = Field(default_factory=list)
    artifacts: List[RuntimeArtifact] = Field(default_factory=list)
    control_records: List[ControlRecord] = Field(default_factory=list)
    synthesis_notes: List[str] = Field(default_factory=list)
    final_artifacts: List[ArtifactItem] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    request_objective: Optional[str] = None
    request_payload: Dict[str, Any] = Field(default_factory=dict)
    request_constraints: List[str] = Field(default_factory=list)
    requested_runtime_mode: Optional[str] = None
    effective_runtime_mode: Optional[RuntimeMode] = None
    effective_model: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    used_mock_fallback: bool = False
    fallback_reason: Optional[str] = None
    elapsed_ms: Optional[float] = None
    result_status: Optional[ResultStatus] = None
    result_summary: Optional[str] = None
    follow_up_items: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
    finding_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
