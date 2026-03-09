<template>
  <section class="panel-card">
    <div class="section-header">
      <div>
        <h2>新建任务</h2>
        <p>提交后会立即返回 `run_id`，后端在线程池中继续执行。</p>
      </div>
    </div>

    <form class="task-form" @submit.prevent="submitForm">
      <label class="field">
        <span>任务类型</span>
        <select v-model="selectedTaskType" :disabled="submitting" @change="applyTemplate">
          <option v-for="option in taskOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </label>

      <label class="field">
        <span>任务目标</span>
        <input
          v-model="objective"
          :disabled="submitting"
          type="text"
          placeholder="请输入任务目标"
        />
      </label>

      <label class="field">
        <span>Payload JSON</span>
        <textarea
          v-model="payloadText"
          :disabled="submitting"
          rows="12"
          spellcheck="false"
        />
      </label>

      <p v-if="parseError" class="form-alert error">{{ parseError }}</p>

      <div class="form-actions">
        <button type="button" class="secondary-btn" :disabled="submitting" @click="applyTemplate">
          重置模板
        </button>
        <button type="submit" class="primary-btn" :disabled="submitting">
          {{ submitting ? '提交中...' : '创建任务' }}
        </button>
      </div>
    </form>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'

import type { AgentTaskCreateRequest } from '../../../types/agent'
import { AGENT_TASK_OPTIONS, buildDefaultTaskDraft } from '../config'

defineProps<{
  submitting: boolean
}>()

const emit = defineEmits<{
  (event: 'submit', payload: AgentTaskCreateRequest): void
}>()

const taskOptions = AGENT_TASK_OPTIONS
const selectedTaskType = ref<
  'competition_recommendation' | 'competition_eligibility_check' | 'competition_timeline_plan'
>('competition_recommendation')
const objective = ref('')
const payloadText = ref('')
const parseError = ref('')

function applyTemplate() {
  const draft = buildDefaultTaskDraft(selectedTaskType.value)
  objective.value = draft.objective ?? ''
  payloadText.value = JSON.stringify(draft.payload, null, 2)
  parseError.value = ''
}

function submitForm() {
  try {
    const payload = JSON.parse(payloadText.value)
    parseError.value = ''
    emit('submit', {
      task_type: selectedTaskType.value,
      objective: objective.value,
      payload,
      dry_run: false,
    })
  } catch (error) {
    parseError.value = error instanceof Error ? `JSON 解析失败：${error.message}` : 'JSON 格式无效。'
  }
}

applyTemplate()
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
  min-height: 220px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
}

.field input:focus,
.field select:focus,
.field textarea:focus {
  outline: none;
  border-color: #0071e3;
  background: #ffffff;
  box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.12);
}

.form-alert {
  border-radius: 10px;
  padding: 12px 14px;
  font-size: 14px;
}

.form-alert.error {
  background: #fff1f0;
  color: #b42318;
  border: 1px solid #f4c7c3;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
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

.primary-btn:disabled,
.secondary-btn:disabled {
  cursor: default;
  opacity: 0.6;
}

.secondary-btn {
  background: #e8e8ed;
  color: #1d1d1f;
}
</style>
