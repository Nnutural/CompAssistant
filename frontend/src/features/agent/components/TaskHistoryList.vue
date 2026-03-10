<template>
  <section class="panel-card" data-testid="task-history-card">
    <div class="section-header">
      <div>
        <h3>最近任务</h3>
        <p>支持按状态和任务类型筛选，并可切换查看历史运行记录。</p>
      </div>
      <button
        class="refresh-btn"
        data-testid="task-history-refresh"
        type="button"
        :disabled="loading"
        @click="$emit('refresh')"
      >
        {{ loading ? '刷新中…' : '刷新列表' }}
      </button>
    </div>

    <div class="filters-row">
      <label class="filter-field">
        <span>状态</span>
        <select :value="statusFilter" data-testid="history-status-filter" @change="updateStatusFilter">
          <option v-for="option in statusOptions" :key="option.value || 'all'" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </label>

      <label class="filter-field">
        <span>任务类型</span>
        <select
          :value="taskTypeFilter"
          data-testid="history-task-type-filter"
          @change="updateTaskTypeFilter"
        >
          <option value="">全部任务</option>
          <option v-for="option in taskOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </label>
    </div>

    <div v-if="!items.length" class="empty-state">
      当前筛选条件下没有历史任务。
    </div>

    <div v-else class="history-list" data-testid="task-history-list">
      <article
        v-for="item in items"
        :key="item.run_id"
        :class="['history-item', { active: item.run_id === currentRunId }]"
      >
        <div class="history-top">
          <div>
            <strong>{{ taskLabel(item.task_type) }}</strong>
            <p>{{ item.run_id }}</p>
          </div>
          <span class="status-badge" :data-status="item.status">
            {{ statusLabel(item.status) }}
          </span>
        </div>

        <p v-if="item.result_summary" class="history-summary">{{ item.result_summary }}</p>

        <div class="history-meta">
          <span>{{ formatDate(item.updated_at || item.created_at) }}</span>
          <span v-if="item.has_artifacts">有产物</span>
          <span v-if="item.awaiting_review">待审核</span>
          <span v-if="item.used_mock_fallback">已降级</span>
        </div>

        <div class="history-actions">
          <button
            type="button"
            class="secondary-btn"
            :data-testid="`history-select-${item.run_id}`"
            @click="$emit('select', item.run_id)"
          >
            查看
          </button>
        </div>
      </article>
    </div>

    <div v-if="canLoadMore" class="load-more-row">
      <button
        type="button"
        class="secondary-btn"
        data-testid="task-history-load-more"
        :disabled="loading"
        @click="$emit('load-more')"
      >
        加载更多
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { AgentTaskHistoryItem, AgentTaskRunStatus } from '../../../types/agent'
import {
  AGENT_TASK_OPTIONS,
  HISTORY_STATUS_OPTIONS,
  STATUS_LABELS,
  TASK_TYPE_LABELS,
} from '../config'

defineProps<{
  items: AgentTaskHistoryItem[]
  total: number
  loading: boolean
  currentRunId: string | null
  statusFilter: string
  taskTypeFilter: string
  canLoadMore: boolean
}>()

const emit = defineEmits<{
  (event: 'refresh'): void
  (event: 'load-more'): void
  (event: 'select', runId: string): void
  (event: 'change-status', value: string): void
  (event: 'change-task-type', value: string): void
}>()

const statusOptions = HISTORY_STATUS_OPTIONS
const taskOptions = AGENT_TASK_OPTIONS

function updateStatusFilter(event: Event) {
  const target = event.target as HTMLSelectElement
  emit('change-status', target.value)
}

function updateTaskTypeFilter(event: Event) {
  const target = event.target as HTMLSelectElement
  emit('change-task-type', target.value)
}

function statusLabel(status: AgentTaskRunStatus) {
  return STATUS_LABELS[status] ?? status
}

function taskLabel(taskType?: string | null) {
  if (!taskType) {
    return '未知任务'
  }
  return TASK_TYPE_LABELS[taskType] ?? taskType
}

function formatDate(value: string) {
  return new Date(value).toLocaleString('zh-CN')
}
</script>

<style scoped>
.panel-card {
  background: #ffffff;
  border: 1px solid #d2d2d7;
  border-radius: 16px;
  padding: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.section-header h3 {
  font-size: 18px;
  color: #1d1d1f;
}

.section-header p {
  margin-top: 6px;
  color: #6e6e73;
  font-size: 14px;
}

.refresh-btn,
.secondary-btn {
  border: none;
  border-radius: 10px;
  padding: 8px 12px;
  background: #e8e8ed;
  color: #1d1d1f;
  cursor: pointer;
}

.refresh-btn:disabled,
.secondary-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.filters-row {
  margin-top: 18px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.filter-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.filter-field span {
  font-size: 12px;
  font-weight: 600;
  color: #6e6e73;
}

.filter-field select {
  border: 1px solid #d2d2d7;
  border-radius: 10px;
  background: #f5f5f7;
  padding: 10px 12px;
  color: #1d1d1f;
}

.empty-state {
  margin-top: 16px;
  color: #6e6e73;
}

.history-list {
  margin-top: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-item {
  border: 1px solid #e8e8ed;
  border-radius: 12px;
  background: #f8f8fa;
  padding: 14px;
}

.history-item.active {
  border-color: #0071e3;
  box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.12);
}

.history-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.history-top p {
  margin-top: 4px;
  color: #6e6e73;
  font-size: 12px;
}

.history-summary {
  margin-top: 10px;
  color: #1d1d1f;
  line-height: 1.5;
}

.history-meta {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  color: #6e6e73;
  font-size: 12px;
}

.history-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.load-more-row {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}

.status-badge {
  width: fit-content;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  background: #e8e8ed;
  color: #1d1d1f;
}

.status-badge[data-status='queued'] {
  background: #fff3cd;
  color: #7a5a00;
}

.status-badge[data-status='running'] {
  background: #e7f0ff;
  color: #0055aa;
}

.status-badge[data-status='completed'] {
  background: #e8f5e9;
  color: #1e7a34;
}

.status-badge[data-status='cancelled'] {
  background: #f4f4f5;
  color: #4b5563;
}

.status-badge[data-status='failed'] {
  background: #fff1f0;
  color: #b42318;
}

.status-badge[data-status='awaiting_review'] {
  background: #fff8e1;
  color: #915f00;
}

@media (max-width: 768px) {
  .filters-row {
    grid-template-columns: 1fr;
  }
}
</style>
