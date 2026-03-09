from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from time import perf_counter
from typing import Any


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
TOOL_TIMEOUT_MS = 300


def reset_runtime_data_cache() -> None:
    _load_competitions.cache_clear()
    _load_competitions_enriched.cache_clear()
    _load_eligibility_rules.cache_clear()
    _load_recommendation_rubric.cache_clear()
    _load_timeline_templates.cache_clear()


def load_competition_by_id(competition_id: int) -> dict[str, Any]:
    return _wrap_tool("load_competition_by_id", lambda: _get_competition(competition_id))


def filter_competitions_by_profile(profile: dict[str, Any]) -> dict[str, Any]:
    def _run() -> dict[str, Any]:
        normalized = _normalize_profile(profile)
        scored: list[dict[str, Any]] = []
        for competition in _iter_enriched_competitions():
            if not _passes_profile_filter(competition, normalized):
                continue
            score = _compute_match_score(competition, normalized)
            scored.append(
                {
                    "competition": competition,
                    "score_breakdown": score,
                }
            )
        if not scored:
            for competition in _iter_enriched_competitions():
                scored.append(
                    {
                        "competition": competition,
                        "score_breakdown": _compute_match_score(competition, normalized),
                    }
                )
        scored.sort(key=lambda item: item["score_breakdown"]["total_score"], reverse=True)
        return {
            "profile": normalized,
            "matches": scored[: min(8, len(scored))],
        }

    return _wrap_tool("filter_competitions_by_profile", _run)


def check_eligibility_rules(competition_id: int, profile: dict[str, Any]) -> dict[str, Any]:
    def _run() -> dict[str, Any]:
        competition = _get_competition(competition_id)
        normalized = _normalize_profile(profile)
        rules = _load_eligibility_rules()
        default_rules = rules.get("default", {})
        field_rules = rules.get("field_expectations", {}).get(competition.get("field"), {})
        override_rules = rules.get("competition_overrides", {}).get(str(competition_id), {})

        missing_conditions: list[str] = []
        attention_points = list(dict.fromkeys(field_rules.get("attention_points", []) + override_rules.get("attention_points", [])))
        rationale: list[str] = []

        grade_rank = _grade_rank(normalized["grade"])
        recommended_grade = override_rules.get(
            "minimum_grade",
            default_rules.get("minimum_grade_by_level", {}).get(competition.get("level"), "freshman"),
        )
        if grade_rank < _grade_rank(recommended_grade):
            missing_conditions.append(f"建议至少达到 {recommended_grade} 再参加该类竞赛。")

        required_tags = override_rules.get("required_any_tags") or field_rules.get("required_any_tags") or []
        if required_tags and not any(tag in normalized["ability_tags"] for tag in required_tags):
            missing_conditions.append(f"建议至少具备以下任一能力标签：{', '.join(required_tags[:3])}。")

        hard_blocks = override_rules.get("hard_blocks", [])
        for blocker in hard_blocks:
            if blocker not in normalized["ability_tags"] and blocker not in normalized["preference_tags"]:
                missing_conditions.append(f"当前缺少关键前置条件：{blocker}。")

        if missing_conditions:
            label = "not_recommended" if len(missing_conditions) >= 2 else "borderline"
            is_eligible = False
        else:
            label = "recommended"
            is_eligible = True

        rationale.append(f"{competition['name']} 的领域为 {competition.get('field')}，当前画像方向为 {normalized['direction'] or '未指定'}。")
        rationale.append(f"竞赛难度为 {competition.get('difficulty')}，当前能力标签数量为 {len(normalized['ability_tags'])}。")
        if override_rules.get("rationale"):
            rationale.extend(override_rules["rationale"])

        return {
            "competition": competition,
            "profile": normalized,
            "eligibility_label": label,
            "is_eligible": is_eligible,
            "missing_conditions": missing_conditions,
            "attention_points": attention_points,
            "rationale": rationale,
        }

    return _wrap_tool("check_eligibility_rules", _run)


def score_competition_match(competition: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    return _wrap_tool(
        "score_competition_match",
        lambda: _compute_match_score(competition, _normalize_profile(profile)),
    )


def build_timeline_template(
    competition_id: int,
    deadline: str | None,
    constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    def _run() -> dict[str, Any]:
        competition = _get_competition(competition_id)
        enriched = competition.get("enriched", {})
        template_id = enriched.get("timeline_template_id")
        templates = _load_timeline_templates().get("templates", {})
        if template_id not in templates:
            raise ValueError(f"Timeline template is missing for competition_id={competition_id}")

        template = templates[template_id]
        deadline_value = _resolve_deadline(deadline or competition.get("deadline"), template.get("default_duration_days", 56))
        normalized_constraints = _normalize_constraints(constraints or {})

        milestones: list[dict[str, Any]] = []
        reverse_schedule: list[str] = []
        for stage in template.get("stages", []):
            due_at = (deadline_value - timedelta(days=int(stage["days_before_deadline"]))).date().isoformat()
            milestones.append(
                {
                    "stage": stage["stage"],
                    "due_at": due_at,
                    "goals": list(stage.get("goals", [])),
                    "deliverables": list(stage.get("deliverables", [])),
                }
            )
            reverse_schedule.append(f"{due_at}: {stage['stage']} -> {', '.join(stage.get('deliverables', [])[:2])}")

        checklist = list(template.get("base_checklist", []))
        if normalized_constraints["available_hours_per_week"] and normalized_constraints["available_hours_per_week"] < 6:
            checklist.append("每周可投入时间较少，优先保留最关键里程碑并尽早冻结选题。")
        if normalized_constraints["team_size"] == 1:
            checklist.append("单人作战时，优先缩小范围，避免并行过多交付物。")

        stage_plan = [
            f"{item['stage']}: 目标 {', '.join(item['goals'][:2])}"
            for item in milestones
        ]
        return {
            "competition": competition,
            "deadline": deadline_value.date().isoformat(),
            "preparation_checklist": checklist,
            "milestones": milestones,
            "stage_plan": stage_plan,
            "reverse_schedule": reverse_schedule,
            "constraints": normalized_constraints,
        }

    return _wrap_tool("build_timeline_template", _run)


def compose_recommendation_rationale(
    competition: dict[str, Any],
    scoring: dict[str, Any],
) -> dict[str, Any]:
    def _run() -> dict[str, Any]:
        enriched = competition.get("enriched", {})
        reasons: list[str] = []
        risk_notes: list[str] = []
        component_scores = scoring.get("component_scores", {})
        if component_scores.get("field_alignment", 0) > 0:
            reasons.append(f"方向匹配度较高：{competition.get('field')} 与用户方向较接近。")
        if component_scores.get("ability_alignment", 0) > 0:
            reasons.append(f"能力标签与竞赛关注点存在重合：{', '.join(enriched.get('focus_tags', [])[:3])}。")
        if component_scores.get("preference_alignment", 0) > 0:
            reasons.append("与偏好标签存在明确交集，适合作为优先尝试项。")
        if not reasons:
            reasons.append("该竞赛在当前数据集中综合评分较高，可作为保守备选。")

        if scoring.get("difficulty_gap") == "stretch":
            risk_notes.append("当前画像与竞赛难度存在跃迁，建议先完成基础训练或寻找更强队友。")
        if competition.get("difficulty") == "困难":
            risk_notes.append("该竞赛节奏紧、投入高，需预留稳定的持续投入时间。")
        risk_notes.extend(enriched.get("eligibility_notes", [])[:2])

        return {
            "reasons": list(dict.fromkeys(reasons)),
            "risk_notes": list(dict.fromkeys(risk_notes)),
        }

    return _wrap_tool("compose_recommendation_rationale", _run)


def unwrap_tool_result(result: dict[str, Any], tool_name: str) -> Any:
    if result.get("ok"):
        return result.get("data")
    error = result.get("error", {})
    raise RuntimeError(f"{tool_name} failed: {error.get('message', 'unknown error')}")


def _wrap_tool(tool_name: str, fn) -> dict[str, Any]:
    started_at = perf_counter()
    try:
        data = fn()
        elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
        if elapsed_ms > TOOL_TIMEOUT_MS:
            return {
                "ok": False,
                "tool": tool_name,
                "elapsed_ms": elapsed_ms,
                "error": {
                    "type": "timeout",
                    "message": f"{tool_name} exceeded {TOOL_TIMEOUT_MS}ms.",
                },
            }
        return {
            "ok": True,
            "tool": tool_name,
            "elapsed_ms": elapsed_ms,
            "data": data,
        }
    except Exception as exc:
        return {
            "ok": False,
            "tool": tool_name,
            "elapsed_ms": round((perf_counter() - started_at) * 1000, 2),
            "error": {
                "type": exc.__class__.__name__,
                "message": str(exc),
            },
        }


@lru_cache(maxsize=1)
def _load_competitions() -> list[dict[str, Any]]:
    return _load_json(DATA_DIR / "competitions.json")


@lru_cache(maxsize=1)
def _load_competitions_enriched() -> dict[str, Any]:
    return _load_json(DATA_DIR / "competitions_enriched.json")


@lru_cache(maxsize=1)
def _load_eligibility_rules() -> dict[str, Any]:
    return _load_json(DATA_DIR / "eligibility_rules.json")


@lru_cache(maxsize=1)
def _load_recommendation_rubric() -> dict[str, Any]:
    return _load_json(DATA_DIR / "recommendation_rubric.json")


@lru_cache(maxsize=1)
def _load_timeline_templates() -> dict[str, Any]:
    return _load_json(DATA_DIR / "timeline_templates.json")


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _iter_enriched_competitions() -> list[dict[str, Any]]:
    return [_merge_competition(item) for item in _load_competitions()]


def _get_competition(competition_id: int) -> dict[str, Any]:
    for competition in _load_competitions():
        if int(competition["id"]) == int(competition_id):
            return _merge_competition(competition)
    raise ValueError(f"Competition not found: {competition_id}")


def _merge_competition(competition: dict[str, Any]) -> dict[str, Any]:
    enriched = _load_competitions_enriched()
    field_profile = enriched.get("field_profiles", {}).get(competition.get("field"), {})
    override = enriched.get("competition_overrides", {}).get(str(competition.get("id")), {})
    merged = dict(competition)
    merged["enriched"] = {
        **field_profile,
        **override,
        "focus_tags": list(dict.fromkeys(field_profile.get("focus_tags", []) + override.get("focus_tags", []))),
        "preferred_skills": list(
            dict.fromkeys(field_profile.get("preferred_skills", []) + override.get("preferred_skills", []))
        ),
        "suitable_grades": override.get("suitable_grades", field_profile.get("suitable_grades", [])),
        "eligibility_notes": list(
            dict.fromkeys(field_profile.get("eligibility_notes", []) + override.get("eligibility_notes", []))
        ),
        "team_mode": override.get("team_mode", field_profile.get("team_mode", "team")),
        "timeline_template_id": override.get(
            "timeline_template_id",
            field_profile.get("timeline_template_id", "standard_delivery"),
        ),
        "min_recommended_weeks": override.get(
            "min_recommended_weeks",
            field_profile.get("min_recommended_weeks", 6),
        ),
    }
    return merged


def _passes_profile_filter(competition: dict[str, Any], profile: dict[str, Any]) -> bool:
    if profile["direction"]:
        direction = profile["direction"]
        field_value = str(competition.get("field", "")).lower()
        tags = [str(tag).lower() for tag in competition.get("enriched", {}).get("focus_tags", [])]
        if direction not in field_value and not any(direction in tag or tag in direction for tag in tags):
            return False
    max_difficulty = profile.get("max_difficulty")
    if max_difficulty and competition.get("difficulty") == "困难" and max_difficulty == "中等":
        return False
    return True


def _compute_match_score(competition: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    rubric = _load_recommendation_rubric()
    weights = rubric.get("weights", {})
    enriched = competition.get("enriched", {})
    field_alignment = _field_alignment_score(competition, profile) * weights.get("field_alignment", 35)
    grade_alignment = _grade_alignment_score(enriched, profile) * weights.get("grade_alignment", 20)
    ability_alignment = _ability_alignment_score(enriched, profile) * weights.get("ability_alignment", 25)
    preference_alignment = _preference_alignment_score(enriched, profile) * weights.get("preference_alignment", 10)
    difficulty_alignment, difficulty_gap = _difficulty_alignment_score(competition, profile)
    difficulty_points = difficulty_alignment * weights.get("difficulty_alignment", 10)
    level_bonus = rubric.get("level_bonus", {}).get(competition.get("level"), 0)
    total_score = round(
        field_alignment + grade_alignment + ability_alignment + preference_alignment + difficulty_points + level_bonus,
        2,
    )
    return {
        "total_score": total_score,
        "difficulty_gap": difficulty_gap,
        "component_scores": {
            "field_alignment": round(field_alignment, 2),
            "grade_alignment": round(grade_alignment, 2),
            "ability_alignment": round(ability_alignment, 2),
            "preference_alignment": round(preference_alignment, 2),
            "difficulty_alignment": round(difficulty_points, 2),
            "level_bonus": round(level_bonus, 2),
        },
    }


def _field_alignment_score(competition: dict[str, Any], profile: dict[str, Any]) -> float:
    if not profile["direction"]:
        return 0.6
    direction = profile["direction"]
    field_value = str(competition.get("field", "")).lower()
    if direction in field_value or field_value in direction:
        return 1.0
    tags = [str(tag).lower() for tag in competition.get("enriched", {}).get("focus_tags", [])]
    return 0.7 if any(direction in tag or tag in direction for tag in tags) else 0.2


def _grade_alignment_score(enriched: dict[str, Any], profile: dict[str, Any]) -> float:
    suitable_grades = enriched.get("suitable_grades", [])
    if not suitable_grades:
        return 0.7
    return 1.0 if profile["grade"] in suitable_grades else 0.3


def _ability_alignment_score(enriched: dict[str, Any], profile: dict[str, Any]) -> float:
    preferred = set(enriched.get("preferred_skills", []) + enriched.get("focus_tags", []))
    if not preferred or not profile["ability_tags"]:
        return 0.5
    overlap = len(preferred.intersection(profile["ability_tags"]))
    return min(1.0, overlap / max(2, len(preferred) / 2))


def _preference_alignment_score(enriched: dict[str, Any], profile: dict[str, Any]) -> float:
    preference_tags = set(profile["preference_tags"])
    if not preference_tags:
        return 0.5
    team_mode = enriched.get("team_mode", "team")
    team_score = 1.0 if team_mode in preference_tags or "flexible" in preference_tags else 0.3
    tag_score = 1.0 if preference_tags.intersection(set(enriched.get("focus_tags", []))) else 0.4
    return round((team_score + tag_score) / 2, 2)


def _difficulty_alignment_score(competition: dict[str, Any], profile: dict[str, Any]) -> tuple[float, str]:
    rubric = _load_recommendation_rubric()
    preferred = rubric.get("difficulty_preferences_by_grade", {}).get(profile["grade"], ["中等"])
    difficulty = competition.get("difficulty", "中等")
    if difficulty in preferred:
        return 1.0, "aligned"
    if difficulty == "困难" and "困难" not in preferred:
        return 0.35, "stretch"
    return 0.6, "manageable"


def _normalize_profile(profile: dict[str, Any] | None) -> dict[str, Any]:
    raw = profile or {}
    direction = str(raw.get("direction") or raw.get("field") or "").strip().lower()
    grade = str(raw.get("grade") or "freshman").strip().lower()
    ability_tags = _normalize_tags(raw.get("ability_tags") or raw.get("skills") or [])
    preference_tags = _normalize_tags(raw.get("preference_tags") or raw.get("preferences") or [])
    return {
        "direction": direction,
        "grade": grade,
        "ability_tags": ability_tags,
        "preference_tags": preference_tags,
        "max_difficulty": str(raw.get("max_difficulty") or "").strip(),
    }


def _normalize_constraints(constraints: dict[str, Any]) -> dict[str, Any]:
    return {
        "available_hours_per_week": int(constraints.get("available_hours_per_week") or 0),
        "team_size": int(constraints.get("team_size") or 0),
        "notes": [str(item) for item in constraints.get("notes", []) if str(item).strip()],
    }


def _normalize_tags(values: Any) -> list[str]:
    if isinstance(values, str):
        raw_values = [item.strip() for item in values.split(",")]
    elif isinstance(values, list):
        raw_values = [str(item).strip() for item in values]
    else:
        raw_values = []
    return [item.lower() for item in raw_values if item]


def _grade_rank(grade: str) -> int:
    ranking = {
        "freshman": 1,
        "sophomore": 2,
        "junior": 3,
        "senior": 4,
        "graduate": 5,
    }
    return ranking.get(str(grade).lower(), 1)


def _resolve_deadline(deadline: str | None, default_duration_days: int) -> datetime:
    if deadline:
        normalized = str(deadline).strip()
        if not normalized:
            return datetime.now(timezone.utc) + timedelta(days=default_duration_days)
        if normalized.endswith("Z"):
            normalized = normalized.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    return datetime.now(timezone.utc) + timedelta(days=default_duration_days)
