from __future__ import annotations

import logging
from time import perf_counter
from datetime import datetime, timezone
from typing import Iterable, Optional

from app.agents.manager import ResearchRuntimeManager
from app.agents.sdk_runtime import AgentsSDKResearchRuntime
from app.core.config import Settings, settings
from app.repositories.ledger_repository import LedgerRepository
from app.schemas.research_runtime import AgentResult, AgentTaskEnvelope, ArtifactItem, ResearchLedger, ResearchScope

logger = logging.getLogger("uvicorn.error")


class ResearchRuntimeService:
    def __init__(
        self,
        repository: Optional[LedgerRepository] = None,
        manager: Optional[ResearchRuntimeManager] = None,
        sdk_runtime: Optional[AgentsSDKResearchRuntime] = None,
        settings_obj: Optional[Settings] = None,
        runtime_mode: Optional[str] = None,
        strict_mode: Optional[bool] = None,
    ):
        self.settings = settings_obj or settings
        self.repository = repository or LedgerRepository()
        self.manager = manager or ResearchRuntimeManager()
        self.sdk_runtime = sdk_runtime
        self.runtime_mode = runtime_mode or self.settings.research_runtime_mode
        self.strict_mode = self.settings.research_runtime_strict_mode if strict_mode is None else strict_mode

    def run_task(self, task: AgentTaskEnvelope) -> AgentResult:
        started_at = perf_counter()
        logger.info(
            "[research-runtime] run_task start task_id=%s session_id=%s runtime_mode=%s strict_mode=%s",
            task.task_id,
            task.session_id,
            self.runtime_mode,
            self.strict_mode,
        )
        ledger = self._load_or_create_ledger(task)
        result, updated_ledger = self._run_runtime(task, ledger)
        self.repository.update(updated_ledger)

        changed_path = self._to_repo_relative(self.repository.get_storage_path(updated_ledger.ledger_id))
        if changed_path not in result.changed_paths:
            result.changed_paths.append(changed_path)
        if not any(item.kind == 'ledger_entry' and item.ref == updated_ledger.ledger_id for item in result.artifacts):
            result.artifacts.append(
                ArtifactItem(kind='ledger_entry', ref=updated_ledger.ledger_id, title='Research Ledger entry')
            )
        logger.info(
            "[research-runtime] run_task completed task_id=%s ledger_id=%s status=%s findings=%s artifacts=%s task_history=%s evidence_log=%s changed_path=%s elapsed_ms=%.2f",
            task.task_id,
            updated_ledger.ledger_id,
            result.status,
            len(result.findings),
            len(result.artifacts),
            len(updated_ledger.task_history),
            len(updated_ledger.evidence_log),
            changed_path,
            (perf_counter() - started_at) * 1000,
        )
        return result

    def get_ledger(self, ledger_id: str) -> Optional[ResearchLedger]:
        return self.repository.get(ledger_id)

    def list_ledgers(self) -> list[ResearchLedger]:
        return self.repository.list()

    def _run_runtime(self, task: AgentTaskEnvelope, ledger: ResearchLedger) -> tuple[AgentResult, ResearchLedger]:
        runtime_started_at = perf_counter()
        if self.runtime_mode == 'agents_sdk':
            try:
                logger.info(
                    "[research-runtime] selecting agents_sdk runtime task_id=%s ledger_id=%s",
                    task.task_id,
                    ledger.ledger_id,
                )
                runtime = self._get_sdk_runtime()
                if not runtime.is_available():
                    raise RuntimeError(
                        'Ark chat-completions runtime is unavailable because OPENAI_API_KEY or SDK dependencies are missing.'
                    )
                result, updated_ledger = runtime.run(task, ledger)
                logger.info(
                    "[research-runtime] agents_sdk runtime finished task_id=%s ledger_id=%s status=%s elapsed_ms=%.2f",
                    task.task_id,
                    ledger.ledger_id,
                    result.status,
                    (perf_counter() - runtime_started_at) * 1000,
                )
                return result, updated_ledger
            except Exception as exc:
                note = f'Ark chat-completions runtime failed: {exc}'
                logger.warning(
                    "[research-runtime] agents_sdk runtime failed task_id=%s ledger_id=%s strict_mode=%s error=%s",
                    task.task_id,
                    ledger.ledger_id,
                    self.strict_mode,
                    exc,
                )
                if self.strict_mode:
                    raise RuntimeError(note) from exc
                return self._run_mock_with_note(task, ledger, note)

        logger.info(
            "[research-runtime] selecting mock runtime task_id=%s ledger_id=%s",
            task.task_id,
            ledger.ledger_id,
        )
        result, updated_ledger = self.manager.run(task, ledger)
        logger.info(
            "[research-runtime] mock runtime finished task_id=%s ledger_id=%s status=%s elapsed_ms=%.2f",
            task.task_id,
            ledger.ledger_id,
            result.status,
            (perf_counter() - runtime_started_at) * 1000,
        )
        return result, updated_ledger

    def _get_sdk_runtime(self) -> AgentsSDKResearchRuntime:
        if self.sdk_runtime is None:
            self.sdk_runtime = AgentsSDKResearchRuntime(
                model=self.settings.openai_default_model,
                openai_api_key=self.settings.openai_api_key,
                openai_base_url=self.settings.openai_base_url,
                tracing_enabled=self.settings.research_runtime_tracing_enabled,
                session_db_path=self.settings.research_runtime_session_db,
            )
        return self.sdk_runtime

    def _run_mock_with_note(
        self,
        task: AgentTaskEnvelope,
        ledger: ResearchLedger,
        note: str,
    ) -> tuple[AgentResult, ResearchLedger]:
        fallback_started_at = perf_counter()
        logger.info(
            "[research-runtime] falling back to mock runtime task_id=%s ledger_id=%s reason=%s",
            task.task_id,
            ledger.ledger_id,
            note,
        )
        result, updated_ledger = self.manager.run(task, ledger)
        fallback_note = f'Returned mock-derived result because {note}'
        if fallback_note not in result.follow_up_items:
            result.follow_up_items.insert(0, fallback_note)
        if note not in updated_ledger.synthesis_notes:
            updated_ledger.synthesis_notes.append(note)
        fallback_metadata = [
            f'runtime model: {self.settings.openai_default_model}',
            f'runtime base url: {self.settings.openai_base_url}',
            f'tracing enabled: {str(bool(self.settings.research_runtime_tracing_enabled)).lower()}',
            'used mock fallback: true',
            f'fallback reason: {note}',
        ]
        for metadata_note in fallback_metadata:
            if metadata_note not in updated_ledger.synthesis_notes:
                updated_ledger.synthesis_notes.append(metadata_note)
        logger.info(
            "[research-runtime] mock fallback completed task_id=%s ledger_id=%s status=%s elapsed_ms=%.2f",
            task.task_id,
            ledger.ledger_id,
            result.status,
            (perf_counter() - fallback_started_at) * 1000,
        )
        return result, updated_ledger

    def _load_or_create_ledger(self, task: AgentTaskEnvelope) -> ResearchLedger:
        ledger_id = self._resolve_ledger_id(task)
        existing = self.repository.get(ledger_id)
        if existing:
            logger.info(
                "[research-runtime] reusing existing ledger ledger_id=%s session_id=%s",
                ledger_id,
                task.session_id,
            )
            return existing

        timestamp = task.created_at or datetime.now(timezone.utc)
        topic = str(task.payload.get('topic') or task.objective)
        question = str(task.payload.get('research_question') or task.objective)
        scope = ResearchScope(
            included_topics=self._coerce_str_list(task.payload.get('included_topics'), default=[topic]),
            excluded_topics=self._coerce_str_list(task.payload.get('excluded_topics'), default=[]),
            success_criteria=self._coerce_str_list(
                task.payload.get('success_criteria'),
                default=['Return AgentResult', 'Persist the Research Ledger'],
            ),
        )
        ledger = ResearchLedger(
            contract_version='1.0',
            ledger_id=ledger_id,
            session_id=task.session_id,
            topic=topic,
            research_question=question,
            status='active',
            owner=task.requested_by,
            scope=scope,
            hypotheses=self._coerce_str_list(task.payload.get('hypotheses'), default=[]),
            task_history=[],
            source_registry=[],
            evidence_log=[],
            synthesis_notes=[],
            final_artifacts=[],
            open_questions=self._coerce_str_list(task.payload.get('open_questions'), default=[]),
            created_at=timestamp,
            updated_at=timestamp,
        )
        logger.info(
            "[research-runtime] creating new ledger ledger_id=%s session_id=%s topic=%s",
            ledger_id,
            task.session_id,
            topic,
        )
        return self.repository.create(ledger)

    def _resolve_ledger_id(self, task: AgentTaskEnvelope) -> str:
        payload_ledger_id = task.payload.get('ledger_id')
        if isinstance(payload_ledger_id, str) and payload_ledger_id.strip():
            return payload_ledger_id.strip()
        return f'ledger-{task.session_id}'

    def _coerce_str_list(self, value, default: Iterable[str]) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        return list(default)

    def _to_repo_relative(self, path) -> str:
        repo_root = path.resolve().parents[3]
        return path.resolve().relative_to(repo_root).as_posix()
