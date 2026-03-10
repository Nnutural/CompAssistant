<template>
  <section class="panel-card">
    <div class="section-header">
      <div>
        <h2>新建任务</h2>
        <p>保留 payload 作为内部 canonical contract，在前端提供简洁模式和高级模式两种输入方式。</p>
      </div>
    </div>

    <div class="mode-switch" role="tablist" aria-label="输入模式">
      <button
        v-for="option in modeOptions"
        :key="option.value"
        type="button"
        :class="['mode-btn', { active: inputMode === option.value }]"
        :disabled="submitting"
        @click="setInputMode(option.value)"
      >
        {{ option.label }}
      </button>
    </div>

    <form class="task-form" @submit.prevent="submitForm">
      <label class="field">
        <span>任务类型</span>
        <select v-model="selectedTaskType" :disabled="submitting">
          <option v-for="option in taskOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </label>

      <p v-if="modeNotice" class="form-alert info">{{ modeNotice }}</p>

      <template v-if="inputMode === 'simple'">
        <p class="mode-note">
          简洁模式面向产品输入层。你填写自然表单后，前端会自动组装 objective 和 payload，再调用现有 task API。
        </p>

        <template v-if="selectedTaskType === 'competition_recommendation'">
          <label class="field">
            <span>方向</span>
            <input
              v-model="simpleDrafts.competition_recommendation.direction"
              :disabled="submitting"
              type="text"
              placeholder="例如：算法/编程、网络安全、数学/建模"
            />
          </label>

          <label class="field">
            <span>年级</span>
            <select v-model="simpleDrafts.competition_recommendation.grade" :disabled="submitting">
              <option v-for="option in gradeOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>

          <label class="field">
            <span>能力标签</span>
            <textarea
              v-model="simpleDrafts.competition_recommendation.abilities"
              :disabled="submitting"
              rows="3"
              placeholder="可用逗号、分号或换行分隔，例如 algorithms, cpp, problem-solving"
            />
          </label>

          <label class="field">
            <span>偏好标签</span>
            <textarea
              v-model="simpleDrafts.competition_recommendation.preference_tags"
              :disabled="submitting"
              rows="2"
              placeholder="例如 team, onsite, flexible"
            />
          </label>

          <label class="field">
            <span>补充说明</span>
            <textarea
              v-model="simpleDrafts.competition_recommendation.extra_notes"
              :disabled="submitting"
              rows="3"
              placeholder="可选，例如希望偏稳妥、希望含团队协作、希望兼顾奖项含金量"
            />
          </label>

          <div class="field">
            <span>附件元数据（可选）</span>
            <input
              :disabled="submitting"
              type="file"
              multiple
              @change="handleAttachmentChange('competition_recommendation', $event)"
            />
            <p class="field-hint">当前仅记录附件元数据到 payload.attachments，不上传文件，也不会被 runtime 消费。</p>
            <ul
              v-if="simpleDrafts.competition_recommendation.attachments.length"
              class="attachment-list"
            >
              <li
                v-for="(item, index) in simpleDrafts.competition_recommendation.attachments"
                :key="item.local_ref"
              >
                <span>{{ item.name }} · {{ item.kind }} · {{ item.mime_type }}</span>
                <button
                  type="button"
                  class="link-btn"
                  :disabled="submitting"
                  @click="removeAttachment('competition_recommendation', index)"
                >
                  移除
                </button>
              </li>
            </ul>
          </div>
        </template>

        <template v-else-if="selectedTaskType === 'competition_eligibility_check'">
          <label class="field">
            <span>竞赛名称或 ID</span>
            <input
              v-model="simpleDrafts.competition_eligibility_check.competition_query"
              :disabled="submitting"
              type="text"
              list="competition-options"
              placeholder="输入竞赛名称搜索，或直接输入 competition_id"
              @change="syncCompetitionQuery('competition_eligibility_check')"
              @blur="syncCompetitionQuery('competition_eligibility_check')"
            />
            <datalist id="competition-options">
              <option v-for="item in competitions" :key="item.id" :value="item.name">
                {{ item.name }}
              </option>
            </datalist>
            <p v-if="competitionsLoading" class="field-hint">正在加载竞赛列表…</p>
            <p v-else-if="competitionsError" class="field-hint warning">
              {{ competitionsError }} 已自动退化为手动输入 competition_id。
            </p>
            <p v-else-if="simpleDrafts.competition_eligibility_check.competition_id" class="field-hint">
              当前将提交 competition_id={{ simpleDrafts.competition_eligibility_check.competition_id }}
            </p>
          </label>

          <label v-if="competitionsError" class="field">
            <span>手动 competition_id</span>
            <input
              :value="simpleDrafts.competition_eligibility_check.competition_id ?? ''"
              :disabled="submitting"
              type="number"
              min="1"
              placeholder="例如 14"
              @input="updateManualCompetitionId('competition_eligibility_check', $event)"
            />
          </label>

          <label class="field">
            <span>年级</span>
            <select v-model="simpleDrafts.competition_eligibility_check.grade" :disabled="submitting">
              <option v-for="option in gradeOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>

          <label class="field">
            <span>已有经历 / 成绩</span>
            <textarea
              v-model="simpleDrafts.competition_eligibility_check.achievements"
              :disabled="submitting"
              rows="3"
              placeholder="例如 蓝桥杯省赛、算法训练、Python 项目经验"
            />
          </label>

          <label class="field">
            <span>前置条件 / 不足项</span>
            <textarea
              v-model="simpleDrafts.competition_eligibility_check.prerequisites"
              :disabled="submitting"
              rows="3"
              placeholder="例如 需要补强数学基础、还没有团队经验"
            />
          </label>

          <label class="field">
            <span>参赛方式偏好</span>
            <select v-model="simpleDrafts.competition_eligibility_check.team_mode" :disabled="submitting">
              <option v-for="option in teamModeOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>

          <label class="field">
            <span>补充说明</span>
            <textarea
              v-model="simpleDrafts.competition_eligibility_check.extra_notes"
              :disabled="submitting"
              rows="3"
              placeholder="可选，例如希望优先评估保守路径，或是否接受高难度 stretch 目标"
            />
          </label>

          <div class="field">
            <span>附件元数据（可选）</span>
            <input
              :disabled="submitting"
              type="file"
              multiple
              @change="handleAttachmentChange('competition_eligibility_check', $event)"
            />
            <p class="field-hint">例如简历、获奖证明、课程成绩单，仅保存元数据。</p>
            <ul v-if="simpleDrafts.competition_eligibility_check.attachments.length" class="attachment-list">
              <li
                v-for="(item, index) in simpleDrafts.competition_eligibility_check.attachments"
                :key="item.local_ref"
              >
                <span>{{ item.name }} · {{ item.kind }} · {{ item.mime_type }}</span>
                <button
                  type="button"
                  class="link-btn"
                  :disabled="submitting"
                  @click="removeAttachment('competition_eligibility_check', index)"
                >
                  移除
                </button>
              </li>
            </ul>
          </div>
        </template>

        <template v-else>
          <label class="field">
            <span>竞赛名称或 ID</span>
            <input
              v-model="simpleDrafts.competition_timeline_plan.competition_query"
              :disabled="submitting"
              type="text"
              list="competition-options"
              placeholder="输入竞赛名称搜索，或直接输入 competition_id"
              @change="syncCompetitionQuery('competition_timeline_plan')"
              @blur="syncCompetitionQuery('competition_timeline_plan')"
            />
            <p v-if="competitionsLoading" class="field-hint">正在加载竞赛列表…</p>
            <p v-else-if="competitionsError" class="field-hint warning">
              {{ competitionsError }} 已自动退化为手动输入 competition_id。
            </p>
            <p v-else-if="simpleDrafts.competition_timeline_plan.competition_id" class="field-hint">
              当前将提交 competition_id={{ simpleDrafts.competition_timeline_plan.competition_id }}
            </p>
          </label>

          <label v-if="competitionsError" class="field">
            <span>手动 competition_id</span>
            <input
              :value="simpleDrafts.competition_timeline_plan.competition_id ?? ''"
              :disabled="submitting"
              type="number"
              min="1"
              placeholder="例如 24"
              @input="updateManualCompetitionId('competition_timeline_plan', $event)"
            />
          </label>

          <label class="field">
            <span>截止日期</span>
            <input
              v-model="simpleDrafts.competition_timeline_plan.deadline"
              :disabled="submitting"
              type="datetime-local"
            />
            <p class="field-hint">会被转换成现有 payload.deadline 字段，作为时间规划的 canonical 输入。</p>
          </label>

          <label class="field">
            <span>每周可投入小时数</span>
            <input
              v-model.number="simpleDrafts.competition_timeline_plan.weekly_hours"
              :disabled="submitting"
              type="number"
              min="1"
              max="80"
            />
          </label>

          <label class="field">
            <span>当前阶段</span>
            <textarea
              v-model="simpleDrafts.competition_timeline_plan.current_stage"
              :disabled="submitting"
              rows="2"
              placeholder="例如 已完成选题、还缺队友、刚开始准备"
            />
          </label>

          <label class="field">
            <span>目标 / 约束</span>
            <textarea
              v-model="simpleDrafts.competition_timeline_plan.goals_or_constraints"
              :disabled="submitting"
              rows="3"
              placeholder="例如 目标是提交 MVP；约束是只有 2 人、希望避免并行任务过多"
            />
          </label>

          <label class="field">
            <span>补充说明</span>
            <textarea
              v-model="simpleDrafts.competition_timeline_plan.extra_notes"
              :disabled="submitting"
              rows="3"
              placeholder="可选，例如是否临近期末、是否需要兼顾实习/考试"
            />
          </label>

          <div class="field">
            <span>附件元数据（可选）</span>
            <input
              :disabled="submitting"
              type="file"
              multiple
              @change="handleAttachmentChange('competition_timeline_plan', $event)"
            />
            <p class="field-hint">例如任务书、往届方案、日历截图，仅记录元数据，不做上传。</p>
            <ul v-if="simpleDrafts.competition_timeline_plan.attachments.length" class="attachment-list">
              <li
                v-for="(item, index) in simpleDrafts.competition_timeline_plan.attachments"
                :key="item.local_ref"
              >
                <span>{{ item.name }} · {{ item.kind }} · {{ item.mime_type }}</span>
                <button
                  type="button"
                  class="link-btn"
                  :disabled="submitting"
                  @click="removeAttachment('competition_timeline_plan', index)"
                >
                  移除
                </button>
              </li>
            </ul>
          </div>
        </template>

        <div class="preview-card">
          <h3>将要提交的 objective</h3>
          <p>{{ simplePreview.objective || '未生成 objective' }}</p>

          <h3>将要提交的 payload 预览</h3>
          <pre>{{ simplePayloadPreview }}</pre>
        </div>
      </template>

      <template v-else>
        <p class="mode-note">
          高级模式保留原始 objective + payload JSON 编辑体验，适合调试、回归测试和精确构造 case。
        </p>

        <label class="field">
          <span>任务目标</span>
          <input
            v-model="activeAdvancedDraft.objective"
            :disabled="submitting"
            type="text"
            placeholder="请输入任务目标"
          />
        </label>

        <label class="field">
          <span>Payload JSON</span>
          <textarea
            v-model="activeAdvancedDraft.payloadText"
            :disabled="submitting"
            rows="14"
            spellcheck="false"
          />
        </label>

        <p class="field-hint">
          payload 仍然是内部 canonical representation。高级模式中可以直接查看和编辑将提交给后端的 JSON。
        </p>

        <p v-if="activeAdvancedDraft.parseError" class="form-alert error">
          {{ activeAdvancedDraft.parseError }}
        </p>
      </template>

      <p v-if="formError" class="form-alert error">{{ formError }}</p>

      <div class="form-actions">
        <button type="button" class="secondary-btn" :disabled="submitting" @click="resetCurrentDraft">
          {{ inputMode === 'simple' ? '重置简洁表单' : '重置高级模板' }}
        </button>
        <button
          v-if="inputMode === 'advanced' && hasAdvancedBackup"
          type="button"
          class="secondary-btn"
          :disabled="submitting"
          @click="restoreAdvancedBackup"
        >
          恢复上次高级草稿
        </button>
        <button type="submit" class="primary-btn" :disabled="submitting">
          {{ submitting ? '提交中…' : '创建任务' }}
        </button>
      </div>
    </form>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { listCompetitions, type CompetitionOption } from '../../../api/competitions'
import type { AgentTaskCreateRequest } from '../../../types/agent'
import {
  AGENT_TASK_OPTIONS,
  GRADE_OPTIONS,
  INPUT_MODE_OPTIONS,
  TEAM_MODE_OPTIONS,
  buildDefaultTaskDraft,
} from '../config'
import {
  buildDefaultSimpleDrafts,
  buildSimpleTaskRequest,
  createAttachmentMetadata,
  resolveCompetitionSelection,
  type SupportedAgentTaskType,
} from '../input_adapter'

interface AdvancedDraft {
  objective: string
  payloadText: string
  parseError: string
}

interface AdvancedBackupDraft {
  objective: string
  payloadText: string
}

defineProps<{
  submitting: boolean
}>()

const emit = defineEmits<{
  (event: 'submit', payload: AgentTaskCreateRequest): void
}>()

const taskOptions = AGENT_TASK_OPTIONS
const modeOptions = INPUT_MODE_OPTIONS
const gradeOptions = GRADE_OPTIONS
const teamModeOptions = TEAM_MODE_OPTIONS

const inputMode = ref<'simple' | 'advanced'>('simple')
const selectedTaskType = ref<SupportedAgentTaskType>('competition_recommendation')
const modeNotice = ref('')
const formError = ref('')

const competitions = ref<CompetitionOption[]>([])
const competitionsLoading = ref(false)
const competitionsError = ref('')

const simpleDrafts = reactive(buildDefaultSimpleDrafts())
const advancedDrafts = reactive<Record<SupportedAgentTaskType, AdvancedDraft>>({
  competition_recommendation: toAdvancedDraft('competition_recommendation'),
  competition_eligibility_check: toAdvancedDraft('competition_eligibility_check'),
  competition_timeline_plan: toAdvancedDraft('competition_timeline_plan'),
})
const advancedBackups = reactive<Record<SupportedAgentTaskType, AdvancedBackupDraft | null>>({
  competition_recommendation: null,
  competition_eligibility_check: null,
  competition_timeline_plan: null,
})

const activeAdvancedDraft = computed(() => advancedDrafts[selectedTaskType.value])
const hasAdvancedBackup = computed(() => Boolean(advancedBackups[selectedTaskType.value]))
const simplePreview = computed(() =>
  buildSimpleTaskRequest(selectedTaskType.value, simpleDrafts, competitions.value),
)
const simplePayloadPreview = computed(() =>
  JSON.stringify(simplePreview.value.payload, null, 2),
)

function toAdvancedDraft(taskType: SupportedAgentTaskType): AdvancedDraft {
  const draft = buildDefaultTaskDraft(taskType)
  return {
    objective: draft.objective ?? '',
    payloadText: JSON.stringify(draft.payload, null, 2),
    parseError: '',
  }
}

function setInputMode(mode: 'simple' | 'advanced') {
  formError.value = ''
  if (mode === inputMode.value) {
    return
  }

  if (mode === 'advanced') {
    syncAdvancedFromSimple(true)
    modeNotice.value = '已将当前简洁表单同步到高级模式，你可以继续微调 objective 和 payload JSON。'
  } else {
    modeNotice.value = '已返回简洁模式。高级模式中的自定义 JSON 会保留，切回高级模式后仍可继续编辑。'
  }

  inputMode.value = mode
}

function syncAdvancedFromSimple(preserveExisting: boolean) {
  const currentTaskType = selectedTaskType.value
  const nextDraft = simplePreview.value
  const activeDraft = advancedDrafts[currentTaskType]

  if (
    preserveExisting
    && (activeDraft.objective.trim() || activeDraft.payloadText.trim())
    && (
      activeDraft.objective !== (nextDraft.objective ?? '')
      || activeDraft.payloadText !== JSON.stringify(nextDraft.payload, null, 2)
    )
  ) {
    advancedBackups[currentTaskType] = {
      objective: activeDraft.objective,
      payloadText: activeDraft.payloadText,
    }
  }

  activeDraft.objective = nextDraft.objective ?? ''
  activeDraft.payloadText = JSON.stringify(nextDraft.payload, null, 2)
  activeDraft.parseError = ''
}

function resetCurrentDraft() {
  formError.value = ''
  modeNotice.value = ''
  if (inputMode.value === 'simple') {
    const defaults = buildDefaultSimpleDrafts()[selectedTaskType.value]
    Object.assign(simpleDrafts[selectedTaskType.value], defaults)
    return
  }

  const defaults = toAdvancedDraft(selectedTaskType.value)
  advancedDrafts[selectedTaskType.value] = defaults
}

function restoreAdvancedBackup() {
  const backup = advancedBackups[selectedTaskType.value]
  if (!backup) {
    return
  }
  advancedDrafts[selectedTaskType.value].objective = backup.objective
  advancedDrafts[selectedTaskType.value].payloadText = backup.payloadText
  advancedDrafts[selectedTaskType.value].parseError = ''
  modeNotice.value = '已恢复上次高级模式草稿。'
}

function validateSimpleForm(): string {
  if (selectedTaskType.value === 'competition_recommendation') {
    if (!simpleDrafts.competition_recommendation.direction.trim()) {
      return '请先填写推荐任务的方向。'
    }
    return ''
  }

  if (selectedTaskType.value === 'competition_eligibility_check') {
    if (!simpleDrafts.competition_eligibility_check.competition_id) {
      return '请先选择竞赛名称，或手动输入 competition_id。'
    }
    return ''
  }

  if (!simpleDrafts.competition_timeline_plan.competition_id) {
    return '请先选择竞赛名称，或手动输入 competition_id。'
  }
  if (!simpleDrafts.competition_timeline_plan.deadline.trim()) {
    return '请先填写时间线任务的截止日期。'
  }
  return ''
}

function submitForm() {
  formError.value = ''
  if (inputMode.value === 'simple') {
    const validationError = validateSimpleForm()
    if (validationError) {
      formError.value = validationError
      return
    }

    syncAdvancedFromSimple(false)
    emit('submit', simplePreview.value)
    return
  }

  try {
    const payload = JSON.parse(activeAdvancedDraft.value.payloadText)
    activeAdvancedDraft.value.parseError = ''
    emit('submit', {
      task_type: selectedTaskType.value,
      objective: activeAdvancedDraft.value.objective,
      payload,
      dry_run: false,
    })
  } catch (error) {
    activeAdvancedDraft.value.parseError =
      error instanceof Error ? `JSON 解析失败：${error.message}` : 'JSON 格式无效。'
  }
}

function syncCompetitionQuery(
  taskType: 'competition_eligibility_check' | 'competition_timeline_plan',
) {
  const draft = simpleDrafts[taskType]
  const resolved = resolveCompetitionSelection(draft.competition_query, competitions.value)
  draft.competition_query = resolved.normalizedQuery
  draft.competition_id = resolved.competitionId
}

function updateManualCompetitionId(
  taskType: 'competition_eligibility_check' | 'competition_timeline_plan',
  event: Event,
) {
  const target = event.target as HTMLInputElement
  const nextValue = Number.parseInt(target.value, 10)
  simpleDrafts[taskType].competition_id = Number.isFinite(nextValue) ? nextValue : null
}

function handleAttachmentChange(taskType: SupportedAgentTaskType, event: Event) {
  const target = event.target as HTMLInputElement
  const fileList = target.files
  if (!fileList?.length) {
    return
  }
  const attachments = Array.from(fileList).map(createAttachmentMetadata)
  simpleDrafts[taskType].attachments = simpleDrafts[taskType].attachments.concat(attachments)
  target.value = ''
}

function removeAttachment(taskType: SupportedAgentTaskType, index: number) {
  simpleDrafts[taskType].attachments.splice(index, 1)
}

async function loadCompetitionOptions() {
  competitionsLoading.value = true
  competitionsError.value = ''
  try {
    competitions.value = await listCompetitions()
  } catch (error) {
    competitionsError.value =
      error instanceof Error
        ? `竞赛列表加载失败：${error.message}`
        : '竞赛列表加载失败。'
  } finally {
    competitionsLoading.value = false
  }
}

onMounted(() => {
  void loadCompetitionOptions()
})
</script>

<style scoped>
.panel-card {
  background: #ffffff;
  border: 1px solid #d2d2d7;
  border-radius: 16px;
  padding: 20px;
}

.section-header h2 {
  font-size: 20px;
  color: #1d1d1f;
}

.section-header p {
  margin-top: 6px;
  color: #6e6e73;
  font-size: 14px;
  line-height: 1.5;
}

.mode-switch {
  margin-top: 18px;
  display: inline-flex;
  gap: 8px;
  padding: 4px;
  border-radius: 999px;
  background: #f5f5f7;
}

.mode-btn {
  border: none;
  border-radius: 999px;
  padding: 9px 16px;
  background: transparent;
  color: #1d1d1f;
  cursor: pointer;
}

.mode-btn.active {
  background: #ffffff;
  box-shadow: inset 0 0 0 1px #d2d2d7;
  font-weight: 600;
}

.task-form {
  margin-top: 18px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field span {
  font-size: 13px;
  font-weight: 600;
  color: #6e6e73;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.field input,
.field select,
.field textarea {
  width: 100%;
  border: 1px solid #d2d2d7;
  border-radius: 10px;
  background: #f5f5f7;
  color: #1d1d1f;
  padding: 12px 14px;
  font-size: 14px;
  font-family: inherit;
}

.field textarea {
  resize: vertical;
  min-height: 112px;
}

.field input:focus,
.field select:focus,
.field textarea:focus {
  outline: none;
  border-color: #0071e3;
  background: #ffffff;
  box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.12);
}

.field-hint {
  font-size: 13px;
  color: #6e6e73;
  line-height: 1.5;
}

.field-hint.warning {
  color: #915f00;
}

.mode-note {
  border-radius: 12px;
  padding: 12px 14px;
  background: #f5f5f7;
  color: #1d1d1f;
  line-height: 1.6;
}

.preview-card {
  border: 1px solid #d2d2d7;
  border-radius: 14px;
  padding: 16px;
  background: #fafafc;
}

.preview-card h3 {
  font-size: 15px;
  color: #1d1d1f;
}

.preview-card h3 + p,
.preview-card h3 + pre {
  margin-top: 10px;
}

.preview-card h3:not(:first-child) {
  margin-top: 18px;
}

.preview-card p,
.preview-card pre {
  color: #1d1d1f;
  line-height: 1.6;
}

.preview-card pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
}

.attachment-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.attachment-list li {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  border: 1px solid #e8e8ed;
  border-radius: 10px;
  padding: 10px 12px;
  background: #fafafc;
}

.link-btn {
  border: none;
  background: transparent;
  color: #0071e3;
  cursor: pointer;
}

.form-alert {
  border-radius: 10px;
  padding: 12px 14px;
  font-size: 14px;
  line-height: 1.5;
}

.form-alert.info {
  background: #eef6ff;
  color: #0055aa;
  border: 1px solid #c7defd;
}

.form-alert.error {
  background: #fff1f0;
  color: #b42318;
  border: 1px solid #f4c7c3;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 12px;
}

.primary-btn,
.secondary-btn {
  border: none;
  border-radius: 10px;
  padding: 10px 16px;
  font-size: 14px;
  cursor: pointer;
}

.primary-btn {
  background: #0071e3;
  color: #ffffff;
}

.secondary-btn {
  background: #e8e8ed;
  color: #1d1d1f;
}

.primary-btn:disabled,
.secondary-btn:disabled,
.link-btn:disabled,
.mode-btn:disabled {
  cursor: default;
  opacity: 0.6;
}

@media (max-width: 768px) {
  .mode-switch {
    width: 100%;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .attachment-list li {
    flex-direction: column;
    align-items: flex-start;
  }

  .form-actions {
    justify-content: stretch;
  }

  .form-actions button {
    width: 100%;
  }
}
</style>
