<template>
  <section class="panel-card">
    <div class="section-header">
      <div>
        <h3>当前任务</h3>
        <p>查看状态推进、降级信息、审核提示和控制入口。</p>
      </div>
      <button v-if="runStatus" class="refresh-btn" type="button" @click="$emit('refresh')">刷新</button>
    </div>

    <div v-if="!runStatus" class="empty-state">
      请选择历史任务，或先创建一个新任务。
    </div>

    <template v-else>
      <div class="status-grid">
        <div class="status-item">
          <span class="status-label">Run ID</span>
          <code>{{ runStatus.run_id }}</code>
        </div>
        <div class="status-item">
          <span class="status-label">任务类型</span>
          <span>{{ taskTypeLabel }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">状态</span>
          <span class="status-badge" :data-status="runStatus.status">
            {{ statusLabel }}
          </span>
        </div>
        <div class="status-item">
          <span class="status-label">当前阶段</span>
          <span>{{ currentStateLabel }}</span>
        </div>
      </div>

      <div v-if="runStatus.completed_states.length" class="pill-row">
        <span v-for="state in runStatus.completed_states" :key="state" class="state-pill">
          {{ stateLabel(state) }}
        </span>
      </div>

      <p v-if="runStatus.result.summary" class="summary-text">{{ runStatus.result.summary }}</p>

      <div v-if="runStatus.available_actions.length" class="actions-row">
        <button
          v-if="runStatus.available_actions.includes('retry')"
          class="action-btn"
          type="button"
          :disabled="actionBusy"
          @click="$emit('retry')"
        >
          重试
        </button>
        <button
          v-if="runStatus.available_actions.includes('cancel')"
          class="action-btn warning"
          type="button"
          :disabled="actionBusy"
          @click="$emit('cancel')"
        >
          取消任务
        </button>
        <button
          v-if="runStatus.available_actions.includes('review_accept')"
          class="action-btn success"
          type="button"
          :disabled="actionBusy"
          @click="$emit('review', 'accept')"
        >
          审核通过
        </button>
        <button
          v-if="runStatus.available_actions.includes('review_reject')"
          class="action-btn danger"
          type="button"
          :disabled="actionBusy"
          @click="$emit('review', 'reject')"
        >
          审核驳回
        </button>
        <button
          v-if="runStatus.available_actions.includes('review_annotate')"
          class="action-btn secondary"
          type="button"
          :disabled="actionBusy"
          @click="$emit('review', 'annotate')"
        >
          添加备注
        </button>
      </div>

      <div v-if="noticeMessage" class="alert-box info">
        <strong>操作反馈</strong>
        <p>{{ noticeMessage }}</p>
      </div>

      <div v-if="runStatus.result.follow_up_items.length" class="alert-box">
        <strong>后续提示</strong>
        <ul>
          <li v-for="item in runStatus.result.follow_up_items" :key="item">{{ item }}</li>
        </ul>
      </div>

      <div v-if="runStatus.result.blockers.length" class="alert-box error">
        <strong>阻塞项</strong>
        <ul>
          <li v-for="item in runStatus.result.blockers" :key="item">{{ item }}</li>
        </ul>
      </div>

      <div v-if="runStatus.used_mock_fallback || runStatus.fallback_reason" class="alert-box warning">
        <strong>降级信息</strong>
        <p>{{ runStatus.fallback_reason || '当前结果使用了 mock 降级路径。' }}</p>
      </div>

      <div v-if="networkError" class="alert-box error">
        <strong>网络错误</strong>
        <p>{{ networkError }}</p>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { AgentRunState, AgentTaskStatusResponse } from '../../../types/agent'
import { STATE_LABELS, STATUS_LABELS, TASK_TYPE_LABELS } from '../config'

const props = defineProps<{
  runStatus: AgentTaskStatusResponse | null
  networkError: string
  noticeMessage: string
  actionBusy: boolean
}>()

defineEmits<{
  (event: 'refresh'): void
  (event: 'retry'): void
  (event: 'cancel'): void
  (event: 'review', decision: 'accept' | 'reject' | 'annotate'): void
}>()

const statusLabel = computed(() =>
  props.runStatus ? STATUS_LABELS[props.runStatus.status] ?? props.runStatus.status : '',
)

const currentStateLabel = computed(() => {
  if (!props.runStatus?.current_state) {
    return '暂无'
  }
  return STATE_LABELS[props.runStatus.current_state] ?? props.runStatus.current_state
})

const taskTypeLabel = computed(() => {
  if (!props.runStatus?.task_type) {
    return '未知'
  }
  return TASK_TYPE_LABELS[props.runStatus.task_type] ?? props.runStatus.task_type
})

function stateLabel(state: AgentRunState) {
  return STATE_LABELS[state] ?? state
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

.refresh-btn {
  border: none;
  border-radius: 10px;
  padding: 8px 12px;
  background: #e8e8ed;
  color: #1d1d1f;
  cursor: pointer;
}

.empty-state {
  margin-top: 16px;
  color: #6e6e73;
}

.status-grid {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.status-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.status-label {
  font-size: 12px;
  font-weight: 600;
  color: #6e6e73;
  text-transform: uppercase;
  letter-spacing: 0.05em;
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

.pill-row {
  margin-top: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.state-pill {
  padding: 6px 10px;
  border-radius: 999px;
  background: #f5f5f7;
  border: 1px solid #d2d2d7;
  font-size: 12px;
  color: #1d1d1f;
}

.summary-text {
  margin-top: 16px;
  line-height: 1.6;
  color: #1d1d1f;
}

.actions-row {
  margin-top: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.action-btn {
  border: none;
  border-radius: 10px;
  padding: 9px 14px;
  font-size: 14px;
  background: #0071e3;
  color: #ffffff;
  cursor: pointer;
}

.action-btn.secondary {
  background: #e8e8ed;
  color: #1d1d1f;
}

.action-btn.warning {
  background: #fff3cd;
  color: #7a5a00;
}

.action-btn.success {
  background: #e8f5e9;
  color: #1e7a34;
}

.action-btn.danger {
  background: #fff1f0;
  color: #b42318;
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.alert-box {
  margin-top: 16px;
  border-radius: 12px;
  padding: 12px 14px;
  background: #f5f5f7;
  color: #1d1d1f;
}

.alert-box.info {
  background: #eef6ff;
  color: #0055aa;
}

.alert-box.warning {
  background: #fff8e1;
  color: #915f00;
}

.alert-box.error {
  background: #fff1f0;
  color: #b42318;
}

.alert-box ul {
  margin-top: 8px;
  padding-left: 18px;
}

.alert-box p {
  margin-top: 8px;
}

@media (max-width: 768px) {
  .status-grid {
    grid-template-columns: 1fr;
  }
}
</style>
