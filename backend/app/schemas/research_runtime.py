from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


ReferenceKind = Literal["file", "doc", "schema", "dataset", "url", "note", "task", "ledger"]
OutputFormat = Literal["json", "markdown", "text", "artifact_bundle"]
TaskType = Literal[
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
ResultStatus = Literal["draft", "completed", "blocked", "needs_human"]
FindingConfidence = Literal["low", "medium", "high"]
ArtifactKind = Literal["file", "doc", "schema", "report", "note", "dataset", "ledger_entry"]
LedgerStatus = Literal["active", "paused", "completed", "archived"]
LedgerTaskStatus = Literal["queued", "running", "completed", "blocked", "cancelled"]
SourceType = Literal["doc", "paper", "web", "dataset", "interview", "note", "code"]


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


class ResearchLedger(ContractBaseModel):
    contract_version: Literal["1.0"]
    ledger_id: str
    session_id: str
    topic: str
    research_question: str
    status: LedgerStatus
    owner: Optional[str] = None
    scope: ResearchScope
    hypotheses: List[str] = Field(default_factory=list)
    task_history: List[LedgerTaskEntry]
    source_registry: List[SourceRecord]
    evidence_log: List[EvidenceRecord]
    synthesis_notes: List[str] = Field(default_factory=list)
    final_artifacts: List[ArtifactItem] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None
