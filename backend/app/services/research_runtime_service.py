from datetime import datetime, timezone
from typing import Iterable, Optional

from app.agents.manager import ResearchRuntimeManager
from app.repositories.ledger_repository import LedgerRepository
from app.schemas.research_runtime import AgentResult, AgentTaskEnvelope, ArtifactItem, ResearchLedger, ResearchScope


class ResearchRuntimeService:
    def __init__(
        self,
        repository: Optional[LedgerRepository] = None,
        manager: Optional[ResearchRuntimeManager] = None,
    ):
        self.repository = repository or LedgerRepository()
        self.manager = manager or ResearchRuntimeManager()

    def run_task(self, task: AgentTaskEnvelope) -> AgentResult:
        ledger = self._load_or_create_ledger(task)
        result, updated_ledger = self.manager.run(task, ledger)
        self.repository.update(updated_ledger)

        changed_path = self._to_repo_relative(self.repository.get_storage_path(updated_ledger.ledger_id))
        if changed_path not in result.changed_paths:
            result.changed_paths.append(changed_path)
        if not any(item.kind == "ledger_entry" and item.ref == updated_ledger.ledger_id for item in result.artifacts):
            result.artifacts.append(
                ArtifactItem(kind="ledger_entry", ref=updated_ledger.ledger_id, title="Research Ledger 条目")
            )
        return result

    def get_ledger(self, ledger_id: str) -> Optional[ResearchLedger]:
        return self.repository.get(ledger_id)

    def list_ledgers(self) -> list[ResearchLedger]:
        return self.repository.list()

    def _load_or_create_ledger(self, task: AgentTaskEnvelope) -> ResearchLedger:
        ledger_id = self._resolve_ledger_id(task)
        existing = self.repository.get(ledger_id)
        if existing:
            return existing

        timestamp = task.created_at or datetime.now(timezone.utc)
        topic = str(task.payload.get("topic") or task.objective)
        question = str(task.payload.get("research_question") or task.objective)
        scope = ResearchScope(
            included_topics=self._coerce_str_list(task.payload.get("included_topics"), default=[topic]),
            excluded_topics=self._coerce_str_list(task.payload.get("excluded_topics"), default=[]),
            success_criteria=self._coerce_str_list(
                task.payload.get("success_criteria"),
                default=["返回 AgentResult", "写回 Research Ledger"],
            ),
        )
        ledger = ResearchLedger(
            contract_version="1.0",
            ledger_id=ledger_id,
            session_id=task.session_id,
            topic=topic,
            research_question=question,
            status="active",
            owner=task.requested_by,
            scope=scope,
            hypotheses=self._coerce_str_list(task.payload.get("hypotheses"), default=[]),
            task_history=[],
            source_registry=[],
            evidence_log=[],
            synthesis_notes=[],
            final_artifacts=[],
            open_questions=self._coerce_str_list(task.payload.get("open_questions"), default=[]),
            created_at=timestamp,
            updated_at=timestamp,
        )
        return self.repository.create(ledger)

    def _resolve_ledger_id(self, task: AgentTaskEnvelope) -> str:
        payload_ledger_id = task.payload.get("ledger_id")
        if isinstance(payload_ledger_id, str) and payload_ledger_id.strip():
            return payload_ledger_id.strip()
        return f"ledger-{task.session_id}"

    def _coerce_str_list(self, value, default: Iterable[str]) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        return list(default)

    def _to_repo_relative(self, path) -> str:
        repo_root = path.resolve().parents[3]
        return path.resolve().relative_to(repo_root).as_posix()