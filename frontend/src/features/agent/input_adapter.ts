import type { CompetitionOption } from '../../api/competitions'
import type { AgentTaskCreateRequest } from '../../types/agent'

export type SupportedAgentTaskType =
  | 'competition_recommendation'
  | 'competition_eligibility_check'
  | 'competition_timeline_plan'

export type GradeValue = 'freshman' | 'sophomore' | 'junior' | 'senior' | 'graduate'
export type TeamModeValue = 'team' | 'individual' | 'flexible'
export type CompetitionSuggestionMatchKind = 'exact_id' | 'exact_name' | 'prefix' | 'contains'
export type CompetitionSuggestionMatchField = 'id' | 'name' | 'field'

export interface AttachmentMetadata {
  name: string
  kind: string
  mime_type: string
  local_ref: string
}

export interface RecommendationSimpleForm {
  direction: string
  grade: GradeValue
  abilities: string
  preference_tags: string
  extra_notes: string
  attachments: AttachmentMetadata[]
}

export interface EligibilitySimpleForm {
  competition_query: string
  competition_id: number | null
  grade: GradeValue
  achievements: string
  prerequisites: string
  team_mode: TeamModeValue
  extra_notes: string
  attachments: AttachmentMetadata[]
}

export interface TimelineSimpleForm {
  competition_query: string
  competition_id: number | null
  deadline: string
  weekly_hours: number
  current_stage: string
  goals_or_constraints: string
  extra_notes: string
  attachments: AttachmentMetadata[]
}

export interface SimpleTaskDrafts {
  competition_recommendation: RecommendationSimpleForm
  competition_eligibility_check: EligibilitySimpleForm
  competition_timeline_plan: TimelineSimpleForm
}

export interface CompetitionSuggestion {
  id: number
  name: string
  field: string
  match_kind: CompetitionSuggestionMatchKind
  match_field: CompetitionSuggestionMatchField
  label: string
}

export function buildDefaultSimpleDrafts(): SimpleTaskDrafts {
  return {
    competition_recommendation: {
      direction: '算法/编程',
      grade: 'freshman',
      abilities: 'algorithms, cpp, problem-solving',
      preference_tags: 'team, onsite',
      extra_notes: '',
      attachments: [],
    },
    competition_eligibility_check: {
      competition_query: '蓝桥杯全国软件和信息技术专业人才大赛',
      competition_id: 14,
      grade: 'freshman',
      achievements: 'algorithms, python',
      prerequisites: 'problem-solving',
      team_mode: 'team',
      extra_notes: '',
      attachments: [],
    },
    competition_timeline_plan: {
      competition_query: '中国软件杯大学生软件设计大赛',
      competition_id: 24,
      deadline: '2026-06-20T18:00',
      weekly_hours: 6,
      current_stage: '已完成初步方向选择，准备细化任务拆解。',
      goals_or_constraints: '希望在截止前完成可提交版本；团队 2 人；优先保证核心功能。',
      extra_notes: '',
      attachments: [],
    },
  }
}

export function buildSimpleTaskRequest(
  taskType: SupportedAgentTaskType,
  drafts: SimpleTaskDrafts,
  competitions: CompetitionOption[],
): AgentTaskCreateRequest {
  if (taskType === 'competition_recommendation') {
    return buildRecommendationRequest(drafts.competition_recommendation)
  }
  if (taskType === 'competition_eligibility_check') {
    return buildEligibilityRequest(drafts.competition_eligibility_check, competitions)
  }
  return buildTimelineRequest(drafts.competition_timeline_plan, competitions)
}

export function createAttachmentMetadata(file: File): AttachmentMetadata {
  return {
    name: file.name,
    kind: inferAttachmentKind(file.type),
    mime_type: file.type || 'application/octet-stream',
    local_ref: `local-file://${file.name}-${file.size}-${file.lastModified}`,
  }
}

export function resolveCompetitionSelection(
  query: string,
  competitions: CompetitionOption[],
): { competitionId: number | null; normalizedQuery: string } {
  const normalizedQuery = query.trim()
  if (!normalizedQuery) {
    return { competitionId: null, normalizedQuery: '' }
  }

  if (/^\d+$/.test(normalizedQuery)) {
    return { competitionId: Number(normalizedQuery), normalizedQuery }
  }

  const exactMatch = competitions.find(
    (item) => item.name.trim().toLowerCase() === normalizedQuery.toLowerCase(),
  )
  if (exactMatch) {
    return {
      competitionId: exactMatch.id,
      normalizedQuery: exactMatch.name,
    }
  }

  return {
    competitionId: null,
    normalizedQuery,
  }
}

export function searchCompetitionSuggestions(
  query: string,
  competitions: CompetitionOption[],
  limit = 6,
): CompetitionSuggestion[] {
  const normalizedQuery = query.trim().toLowerCase()
  if (!normalizedQuery) {
    return []
  }

  const numericQuery = /^\d+$/.test(normalizedQuery) ? Number(normalizedQuery) : null
  const ranked = competitions
    .map((item) => {
      const name = item.name.trim()
      const field = item.field?.trim() || '未标注领域'
      const lowerName = name.toLowerCase()
      const lowerField = field.toLowerCase()

      let matchKind: CompetitionSuggestionMatchKind | null = null
      let matchField: CompetitionSuggestionMatchField = 'name'

      if (numericQuery !== null && item.id === numericQuery) {
        matchKind = 'exact_id'
        matchField = 'id'
      } else if (lowerName === normalizedQuery) {
        matchKind = 'exact_name'
        matchField = 'name'
      } else if (lowerName.startsWith(normalizedQuery)) {
        matchKind = 'prefix'
        matchField = 'name'
      } else if (lowerField.startsWith(normalizedQuery)) {
        matchKind = 'prefix'
        matchField = 'field'
      } else if (lowerName.includes(normalizedQuery)) {
        matchKind = 'contains'
        matchField = 'name'
      } else if (lowerField.includes(normalizedQuery)) {
        matchKind = 'contains'
        matchField = 'field'
      }

      if (!matchKind) {
        return null
      }

      return {
        id: item.id,
        name,
        field,
        match_kind: matchKind,
        match_field: matchField,
        label: `${name} (#${item.id}) · ${field}`,
      }
    })
    .filter((item): item is CompetitionSuggestion => Boolean(item))
    .sort((left, right) => {
      const kindScore = kindRank(left.match_kind) - kindRank(right.match_kind)
      if (kindScore !== 0) {
        return kindScore
      }
      const fieldScore = fieldRank(left.match_field) - fieldRank(right.match_field)
      if (fieldScore !== 0) {
        return fieldScore
      }
      const nameScore = left.name.length - right.name.length
      if (nameScore !== 0) {
        return nameScore
      }
      return left.id - right.id
    })

  return ranked.slice(0, limit)
}

function buildRecommendationRequest(form: RecommendationSimpleForm): AgentTaskCreateRequest {
  const payload: Record<string, unknown> = {
    profile: {
      direction: form.direction.trim(),
      grade: form.grade,
      ability_tags: splitTags(form.abilities),
      preference_tags: splitTags(form.preference_tags),
    },
  }

  if (form.extra_notes.trim()) {
    ;(payload.profile as Record<string, unknown>).extra_notes = form.extra_notes.trim()
  }
  if (form.attachments.length) {
    payload.attachments = form.attachments
  }

  return {
    task_type: 'competition_recommendation',
    objective: buildRecommendationObjective(form),
    payload,
    dry_run: false,
  }
}

function buildEligibilityRequest(
  form: EligibilitySimpleForm,
  competitions: CompetitionOption[],
): AgentTaskCreateRequest {
  const competitionLabel = getCompetitionLabel(form.competition_id, form.competition_query, competitions)
  const profile: Record<string, unknown> = {
    grade: form.grade,
    ability_tags: Array.from(
      new Set([...splitTags(form.achievements), ...splitTags(form.prerequisites)]),
    ),
    preference_tags: form.team_mode ? [form.team_mode] : [],
  }

  if (form.achievements.trim()) {
    profile.achievements = form.achievements.trim()
  }
  if (form.prerequisites.trim()) {
    profile.prerequisites = form.prerequisites.trim()
  }
  if (form.extra_notes.trim()) {
    profile.extra_notes = form.extra_notes.trim()
  }

  const payload: Record<string, unknown> = {
    competition_id: form.competition_id,
    profile,
  }
  if (form.attachments.length) {
    payload.attachments = form.attachments
  }

  return {
    task_type: 'competition_eligibility_check',
    objective: `判断当前学生画像是否适合参加 ${competitionLabel}，并说明缺失条件、注意事项和结论依据。`,
    payload,
    dry_run: false,
  }
}

function buildTimelineRequest(
  form: TimelineSimpleForm,
  competitions: CompetitionOption[],
): AgentTaskCreateRequest {
  const competitionLabel = getCompetitionLabel(form.competition_id, form.competition_query, competitions)
  const notes = [
    form.current_stage.trim() ? `当前阶段：${form.current_stage.trim()}` : '',
    form.goals_or_constraints.trim() ? `目标/约束：${form.goals_or_constraints.trim()}` : '',
    form.extra_notes.trim() ? `补充备注：${form.extra_notes.trim()}` : '',
  ].filter(Boolean)

  const payload: Record<string, unknown> = {
    competition_id: form.competition_id,
    deadline: form.deadline.trim(),
    constraints: {
      available_hours_per_week: form.weekly_hours,
      notes,
    },
  }
  if (form.attachments.length) {
    payload.attachments = form.attachments
  }

  return {
    task_type: 'competition_timeline_plan',
    objective: `为 ${competitionLabel} 生成截止到 ${form.deadline.trim() || '目标截止日期'} 的倒排时间计划，并结合当前阶段与每周投入给出里程碑。`,
    payload,
    dry_run: false,
  }
}

function buildRecommendationObjective(form: RecommendationSimpleForm): string {
  const direction = form.direction.trim() || '当前方向'
  const notes = form.extra_notes.trim()
  if (notes) {
    return `为 ${gradeLabel(form.grade)}、方向为 ${direction} 的学生推荐适合参加的竞赛，并结合补充说明给出理由和风险：${notes}`
  }
  return `为 ${gradeLabel(form.grade)}、方向为 ${direction} 的学生推荐适合参加的竞赛，并给出理由和风险提示。`
}

function getCompetitionLabel(
  competitionId: number | null,
  competitionQuery: string,
  competitions: CompetitionOption[],
): string {
  if (competitionId) {
    const matched = competitions.find((item) => item.id === competitionId)
    if (matched?.name) {
      return matched.name
    }
    return `竞赛 #${competitionId}`
  }
  return competitionQuery.trim() || '目标竞赛'
}

function gradeLabel(grade: GradeValue): string {
  const labels: Record<GradeValue, string> = {
    freshman: '大一',
    sophomore: '大二',
    junior: '大三',
    senior: '大四',
    graduate: '研究生',
  }
  return labels[grade]
}

function splitTags(value: string): string[] {
  return value
    .split(/[\n,，;；]/)
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean)
}

function inferAttachmentKind(mimeType: string): string {
  if (mimeType.startsWith('image/')) {
    return 'image'
  }
  if (mimeType.startsWith('audio/')) {
    return 'audio'
  }
  if (mimeType.startsWith('video/')) {
    return 'video'
  }
  if (mimeType.includes('zip') || mimeType.includes('rar') || mimeType.includes('tar')) {
    return 'archive'
  }
  return 'document'
}

function kindRank(value: CompetitionSuggestionMatchKind): number {
  const ranks: Record<CompetitionSuggestionMatchKind, number> = {
    exact_id: 0,
    exact_name: 1,
    prefix: 2,
    contains: 3,
  }
  return ranks[value]
}

function fieldRank(value: CompetitionSuggestionMatchField): number {
  const ranks: Record<CompetitionSuggestionMatchField, number> = {
    id: 0,
    name: 1,
    field: 2,
  }
  return ranks[value]
}
