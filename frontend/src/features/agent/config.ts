import type {
  AgentTaskControlAction,
  AgentTaskCreateRequest,
  AgentTaskRunStatus,
  AgentTaskType,
} from '../../types/agent'
import type {
  GradeValue,
  SupportedAgentTaskType,
  TeamModeValue,
} from './input_adapter'

export const AGENT_POLL_INTERVAL_MS = 1500
export const AGENT_HISTORY_PAGE_SIZE = 8

export const TERMINAL_RUN_STATUSES: AgentTaskRunStatus[] = [
  'completed',
  'cancelled',
  'failed',
  'awaiting_review',
]

export const AGENT_TASK_OPTIONS: Array<{ label: string; value: SupportedAgentTaskType }> = [
  { label: '竞赛推荐', value: 'competition_recommendation' },
  { label: '参赛资格判断', value: 'competition_eligibility_check' },
  { label: '时间线规划', value: 'competition_timeline_plan' },
]

export const INPUT_MODE_OPTIONS = [
  { label: '简洁模式', value: 'simple' },
  { label: '高级模式', value: 'advanced' },
] as const

export const GRADE_OPTIONS: Array<{ label: string; value: GradeValue }> = [
  { label: '大一', value: 'freshman' },
  { label: '大二', value: 'sophomore' },
  { label: '大三', value: 'junior' },
  { label: '大四', value: 'senior' },
  { label: '研究生', value: 'graduate' },
]

export const TEAM_MODE_OPTIONS: Array<{ label: string; value: TeamModeValue }> = [
  { label: '团队协作', value: 'team' },
  { label: '个人参赛', value: 'individual' },
  { label: '灵活/都可', value: 'flexible' },
]

export const STATUS_LABELS: Record<AgentTaskRunStatus, string> = {
  queued: '排队中',
  running: '运行中',
  completed: '已完成',
  cancelled: '已取消',
  failed: '失败',
  awaiting_review: '待审核',
}

export const STATE_LABELS: Record<string, string> = {
  received: '已接收',
  queued: '排队中',
  running: '运行中',
  planning: '规划中',
  retrieving_local_context: '读取本地上下文',
  reasoning: '推理中',
  validating_output: '校验输出',
  persisting_artifacts: '持久化产物',
  completed: '已完成',
  cancelled: '已取消',
  failed: '失败',
  awaiting_review: '待审核',
}

export const TASK_TYPE_LABELS: Record<string, string> = {
  competition_recommendation: '竞赛推荐',
  competition_eligibility_check: '参赛资格判断',
  competition_timeline_plan: '时间线规划',
  research_plan: '兼容研究任务',
}

export const ACTION_LABELS: Record<AgentTaskControlAction, string> = {
  retry: '重试',
  cancel: '取消',
  review_accept: '审核通过',
  review_reject: '审核驳回',
  review_annotate: '添加备注',
}

export const HISTORY_STATUS_OPTIONS: Array<{ label: string; value: '' | AgentTaskRunStatus }> = [
  { label: '全部状态', value: '' },
  { label: '排队中', value: 'queued' },
  { label: '运行中', value: 'running' },
  { label: '待审核', value: 'awaiting_review' },
  { label: '已完成', value: 'completed' },
  { label: '已取消', value: 'cancelled' },
  { label: '失败', value: 'failed' },
]

const DEFAULT_TASK_DRAFTS: Record<
  SupportedAgentTaskType,
  Pick<AgentTaskCreateRequest, 'task_type' | 'objective' | 'payload'>
> = {
  competition_recommendation: {
    task_type: 'competition_recommendation',
    objective: '为算法/编程方向的大一学生生成 grounded 竞赛推荐。',
    payload: {
      profile: {
        direction: '算法/编程',
        grade: 'freshman',
        ability_tags: ['algorithms', 'cpp', 'problem-solving'],
        preference_tags: ['team', 'onsite'],
      },
    },
  },
  competition_eligibility_check: {
    task_type: 'competition_eligibility_check',
    objective: '判断当前学生画像是否适合参加目标竞赛。',
    payload: {
      competition_id: 14,
      profile: {
        grade: 'freshman',
        ability_tags: ['algorithms', 'python', 'problem-solving'],
        preference_tags: ['team'],
      },
    },
  },
  competition_timeline_plan: {
    task_type: 'competition_timeline_plan',
    objective: '为目标竞赛生成截止日期前的倒排时间线计划。',
    payload: {
      competition_id: 24,
      deadline: '2026-06-20T18:00:00+00:00',
      constraints: {
        available_hours_per_week: 6,
        team_size: 2,
      },
    },
  },
}

export function buildDefaultTaskDraft(
  taskType: SupportedAgentTaskType,
): Pick<AgentTaskCreateRequest, 'task_type' | 'objective' | 'payload'> {
  const template = DEFAULT_TASK_DRAFTS[taskType]
  return {
    task_type: template.task_type,
    objective: template.objective,
    payload: JSON.parse(JSON.stringify(template.payload)),
  }
}

export function isSupportedAgentTaskType(value: AgentTaskType): value is SupportedAgentTaskType {
  return value === 'competition_recommendation'
    || value === 'competition_eligibility_check'
    || value === 'competition_timeline_plan'
}
