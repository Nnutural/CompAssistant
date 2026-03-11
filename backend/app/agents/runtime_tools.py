from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.agents.schema_adapter import provider_function_tool
from app.schemas.research_runtime import AgentTaskEnvelope, EvidenceRecord, FindingItem, ResearchLedger, SourceRecord
from app.tools import (
    build_timeline_template,
    check_eligibility_rules,
    compose_recommendation_rationale,
    filter_competitions_by_profile,
    load_competition_by_id,
    score_competition_match,
    unwrap_tool_result,
)

try:
    from agents.run_context import RunContextWrapper
except ImportError:
    RunContextWrapper = Any


@dataclass
class ResearchAgentContext:
    task: AgentTaskEnvelope
    ledger: ResearchLedger
    model: str
    session_db_path: str
    tracing_enabled: bool
    trace_group_id: str
    runtime_invocation_id: str = field(default_factory=lambda: uuid4().hex[:10])
    manager_trace_id: str | None = None
    specialist_outputs: dict[str, Any] = field(default_factory=dict)
    review_flags: dict[str, str] = field(default_factory=dict)
    session_ids: dict[str, str] = field(default_factory=dict)
    trace_ids: dict[str, str] = field(default_factory=dict)


def resolve_topic(task: AgentTaskEnvelope, ledger: ResearchLedger) -> str:
    return str(task.payload.get('topic') or ledger.topic or task.objective).strip()


def generate_candidate_directions(topic: str, objective: str, requested_count: int = 3) -> list[str]:
    explicit = [
        str(item).strip()
        for item in (topic.split('/') if '/' in topic else [topic])
        if str(item).strip()
    ]
    base_topic = explicit[0] if explicit else topic.strip() or 'research topic'
    templates = [
        f'{base_topic} system design patterns',
        f'{base_topic} evidence collection workflow',
        f'{base_topic} evaluation and risk controls',
    ]
    deduplicated: list[str] = []
    for item in templates:
        if item not in deduplicated:
            deduplicated.append(item)
    return deduplicated[: max(2, min(requested_count, 3))]


def build_source_and_evidence_records(
    task: AgentTaskEnvelope,
    directions: list[str],
    captured_by: str,
) -> tuple[list[SourceRecord], list[EvidenceRecord]]:
    timestamp = datetime.now(timezone.utc)
    sources: list[SourceRecord] = []
    evidence_items: list[EvidenceRecord] = []

    for index, direction in enumerate(directions, start=1):
        source_id = f'{task.task_id}-source-{index}'
        sources.append(
            SourceRecord(
                source_id=source_id,
                source_type='note',
                title=f'{direction} seed note',
                locator=f'mock://research-runtime/{task.task_id}/source/{index}',
                credibility='medium',
                captured_by=captured_by,
                tags=['offline', 'local-tool', 'phase3'],
            )
        )

        for sub_index in range(1, 3):
            evidence_items.append(
                EvidenceRecord(
                    evidence_id=f'{task.task_id}-evidence-{index}-{sub_index}',
                    source_id=source_id,
                    claim=f'{direction} benefits from stable structured outputs and ledger persistence.',
                    excerpt=(
                        f'Local evidence seed {sub_index} for {direction}: '
                        'prefer typed runtime contracts, deterministic local tools, and reproducible ledger updates.'
                    ),
                    captured_by=captured_by,
                    captured_at=timestamp,
                    related_task_id=task.task_id,
                )
            )

    return sources, evidence_items


def build_critic_assessment(topic: str, direction_count: int, evidence_count: int) -> dict[str, str]:
    return {
        'novelty': (
            f'The runtime keeps {direction_count} structured directions around {topic} inside a single ledger-aware workflow, '
            'which is useful for repeatable research demos.'
        ),
        'feasibility': (
            f'The current implementation stays lightweight by grounding {evidence_count} evidence records in local tools, '
            'typed contracts, and FastAPI routes already present in the repository.'
        ),
        'risk': (
            'The current agents remain limited to local inputs. Phase 4 should add network-backed evidence tools, '
            'better failure recovery, and richer source provenance without changing the contract layer.'
        ),
    }


def build_critic_findings(task_id: str, evidence_ids: list[str]) -> list[FindingItem]:
    refs = evidence_ids[:3]
    return [
        FindingItem(
            finding_id=f'{task_id}-finding-1',
            claim='The research runtime already has a stable contract layer that supports a real SDK-backed orchestration path.',
            evidence_refs=refs,
            confidence='high',
        ),
        FindingItem(
            finding_id=f'{task_id}-finding-2',
            claim='The Research Ledger is the right place to consolidate task history, source records, evidence, and runtime metadata.',
            evidence_refs=refs,
            confidence='high',
        ),
    ]


def resolve_session_db_path(raw_path: str | None) -> str:
    if raw_path and str(raw_path).strip():
        path = Path(raw_path).expanduser().resolve()
    else:
        path = Path(__file__).resolve().parents[2] / 'data' / 'research_runtime_sessions.sqlite3'
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


def build_trend_tools() -> list[Any]:
    try:
        from agents import function_tool
    except ImportError as exc:
        raise RuntimeError('openai-agents is not installed') from exc

    @function_tool(
        name_override='generate_candidate_directions',
        description_override='Generate 2 to 3 candidate research directions from the current task topic and objective.',
    )
    def generate_candidate_directions_tool(ctx: RunContextWrapper[ResearchAgentContext]) -> list[str]:
        topic = resolve_topic(ctx.context.task, ctx.context.ledger)
        return generate_candidate_directions(topic, ctx.context.task.objective)

    return [generate_candidate_directions_tool]


def build_evidence_tools() -> list[Any]:
    try:
        from agents import function_tool
    except ImportError as exc:
        raise RuntimeError('openai-agents is not installed') from exc

    @function_tool(
        name_override='build_evidence_seed',
        description_override='Build deterministic local source and evidence seeds for the provided research directions.',
    )
    def build_evidence_seed_tool(
        ctx: RunContextWrapper[ResearchAgentContext],
        directions: list[str],
    ) -> dict[str, Any]:
        sources, evidence_items = build_source_and_evidence_records(
            task=ctx.context.task,
            directions=directions,
            captured_by='evidence-scout',
        )
        return {
            'sources': [item.model_dump(mode='json') for item in sources],
            'evidence': [item.model_dump(mode='json') for item in evidence_items],
        }

    return [build_evidence_seed_tool]


def build_critic_tools() -> list[Any]:
    try:
        from agents import function_tool
    except ImportError as exc:
        raise RuntimeError('openai-agents is not installed') from exc

    @function_tool(
        name_override='score_runtime_output',
        description_override='Return a local novelty, feasibility, and risk assessment plus suggested findings.',
    )
    def score_runtime_output_tool(
        ctx: RunContextWrapper[ResearchAgentContext],
        direction_count: int,
        evidence_ids: list[str],
    ) -> dict[str, Any]:
        topic = resolve_topic(ctx.context.task, ctx.context.ledger)
        assessment = build_critic_assessment(topic, direction_count, len(evidence_ids))
        findings = build_critic_findings(ctx.context.task.task_id, evidence_ids)
        return {
            'assessment': assessment,
            'findings': [item.model_dump(mode='json') for item in findings],
        }

    return [score_runtime_output_tool]


def build_recommendation_tools() -> list[Any]:
    @provider_function_tool(
        name_override='filter_competitions_by_profile',
        description_override=(
            'Return locally ranked recommendation candidates for the provided profile. '
            'Each match already contains canonical recommendation fields plus concise reasons and risk notes.'
        ),
    )
    def filter_competitions_by_profile_tool(
        ctx: RunContextWrapper[ResearchAgentContext],
        profile: dict[str, Any],
    ) -> dict[str, Any]:
        result = unwrap_tool_result(filter_competitions_by_profile(profile), 'filter_competitions_by_profile')
        simplified_matches: list[dict[str, Any]] = []
        for item in result.get("matches", [])[:5]:
            simplified_matches.append(_build_provider_recommendation_match(item))
        return {"matches": simplified_matches}

    return [filter_competitions_by_profile_tool]


def build_eligibility_tools() -> list[Any]:
    @provider_function_tool(
        name_override='load_competition_by_id',
        description_override='Load a locally enriched competition record by id.',
    )
    def load_competition_by_id_tool(
        ctx: RunContextWrapper[ResearchAgentContext],
        competition_id: int,
    ) -> dict[str, Any]:
        return unwrap_tool_result(load_competition_by_id(competition_id), 'load_competition_by_id')

    @provider_function_tool(
        name_override='check_eligibility_rules',
        description_override='Check local eligibility and suitability rules for a competition and profile.',
    )
    def check_eligibility_rules_tool(
        ctx: RunContextWrapper[ResearchAgentContext],
        competition_id: int,
        profile: dict[str, Any],
    ) -> dict[str, Any]:
        return unwrap_tool_result(check_eligibility_rules(competition_id, profile), 'check_eligibility_rules')

    return [load_competition_by_id_tool, check_eligibility_rules_tool]


def build_timeline_tools() -> list[Any]:
    @provider_function_tool(
        name_override='build_timeline_template',
        description_override='Build a local reverse timeline plan from competition id, deadline, and constraints.',
    )
    def build_timeline_template_tool(
        ctx: RunContextWrapper[ResearchAgentContext],
        competition_id: int,
        deadline: str | None,
        constraints: dict[str, Any],
    ) -> dict[str, Any]:
        return unwrap_tool_result(
            build_timeline_template(competition_id, deadline, constraints),
            'build_timeline_template',
        )

    @provider_function_tool(
        name_override='score_competition_match',
        description_override='Score a local competition match against the current profile to decide workload stretch.',
    )
    def score_competition_match_tool(
        ctx: RunContextWrapper[ResearchAgentContext],
        competition: dict[str, Any],
        profile: dict[str, Any],
    ) -> dict[str, Any]:
        return unwrap_tool_result(score_competition_match(competition, profile), 'score_competition_match')

    return [build_timeline_template_tool, score_competition_match_tool]


def _build_provider_recommendation_match(item: dict[str, Any]) -> dict[str, Any]:
    competition = item.get("competition", {})
    scoring = item.get("score_breakdown", {})
    rationale = unwrap_tool_result(
        compose_recommendation_rationale(competition, scoring),
        'compose_recommendation_rationale',
    )
    return _compact_provider_payload(
        {
            "competition_id": competition.get("id"),
            "competition_name": competition.get("name"),
            "match_score": scoring.get("total_score"),
            "reasons": rationale.get("reasons", []),
            "risk_notes": rationale.get("risk_notes", []),
            "focus_tags": competition.get("enriched", {}).get("focus_tags", [])[:4],
            "match_context": {
                "field": competition.get("field"),
                "difficulty": competition.get("difficulty"),
                "level": competition.get("level"),
                "deadline": competition.get("deadline"),
                "difficulty_gap": scoring.get("difficulty_gap"),
                "component_scores": scoring.get("component_scores", {}),
            },
        }
    )


def _compact_provider_payload(value: Any) -> Any:
    if isinstance(value, dict):
        compacted: dict[str, Any] = {}
        for key, item in value.items():
            normalized = _compact_provider_payload(item)
            if normalized is None:
                continue
            if isinstance(normalized, str) and not normalized.strip():
                continue
            if isinstance(normalized, dict) and not normalized:
                continue
            compacted[key] = normalized
        return compacted
    if isinstance(value, list):
        return [_compact_provider_payload(item) for item in value]
    return value
