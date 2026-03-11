<template>
  <section class="panel-card" data-testid="run-status-card">
    <div class="section-header">
      <div>
        <h3>当前任务</h3>
        <p>查看状态推进、运行语义、降级信息、审核提示和控制入口。</p>
      </div>
      <button v-if="runStatus" class="refresh-btn" data-testid="run-status-refresh" type="button" @click="$emit('refresh')">
        刷新
      </button>
    </div>

    <div v-if="!runStatus" class="empty-state">请选择历史任务，或先创建一个新任务。</div>

    <template v-else>
      <div class="status-grid">
        <div class="status-item">
          <span class="status-label">Run ID</span>
          <code data-testid="run-status-run-id">{{ runStatus.run_id }}</code>
        </div>
        <div class="status-item">
          <span class="status-label">任务类型</span>
          <span>{{ taskTypeLabel }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">状态</span>
          <span class="status-badge" :data-status="runStatus.status" data-testid="run-status-status">{{ statusLabel }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">当前阶段</span>
          <span data-testid="run-status-current-state">{{ currentStateLabel }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">请求模式</span>
          <span data-testid="run-status-requested-runtime-mode">{{ runStatus.requested_runtime_mode || '未记录' }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">实际模式</span>
          <span data-testid="run-status-effective-runtime-mode">{{ runStatus.effective_runtime_mode || '未记录' }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">实际模型</span>
          <span data-testid="run-status-effective-model">{{ runStatus.effective_model || '未记录' }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">Provider 路径</span>
          <span data-testid="run-status-provider-success-path">{{ providerPathLabel }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">事件 / 产物</span>
          <span>{{ runStatus.event_count }} / {{ runStatus.artifact_count }}</span>
        </div>
      </div>

      <div v-if="runStatus.completed_states.length" class="pill-row">
        <span v-for="state in runStatus.completed_states" :key="state" class="state-pill">{{ stateLabel(state) }}</span>
      </div>

      <p v-if="runStatus.result.summary" class="summary-text">{{ runStatus.result.summary }}</p>

      <div v-if="runStatus.available_actions.length" class="actions-row">
        <button
          v-if="runStatus.available_actions.includes('retry')"
          class="action-btn"
          data-testid="run-action-retry"
          type="button"
          :disabled="actionBusy"
          @click="$emit('retry')"
        >
          重试
        </button>
        <button
          v-if="runStatus.available_actions.includes('cancel')"
          class="action-btn warning"
          data-testid="run-action-cancel"
          type="button"
          :disabled="actionBusy"
          @click="$emit('cancel')"
        >
          取消任务
        </button>
        <button
          v-if="runStatus.available_actions.includes('review_accept')"
          class="action-btn success"
          data-testid="run-action-review-accept"
          type="button"
          :disabled="actionBusy"
          @click="$emit('review', 'accept')"
        >
          审核通过
        </button>
        <button
          v-if="runStatus.available_actions.includes('review_reject')"
          class="action-btn danger"
          data-testid="run-action-review-reject"
          type="button"
          :disabled="actionBusy"
          @click="$emit('review', 'reject')"
        >
          审核驳回
        </button>
        <button
          v-if="runStatus.available_actions.includes('review_annotate')"
          class="action-btn secondary"
          data-testid="run-action-review-annotate"
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

      <div
        v-if="executionSemantics"
        :class="['alert-box', executionSemantics.tone]"
        data-testid="run-status-execution-semantics"
      >
        <strong>{{ executionSemantics.title }}</strong>
        <p>{{ executionSemantics.description }}</p>
      </div>

      <div v-if="networkError" class="alert-box error" data-testid="run-status-network-error">
        <strong>请求失败</strong>
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
  if (!props.runStatus?.current_state) return '暂无'
  return STATE_LABELS[props.runStatus.current_state] ?? props.runStatus.current_state
})

const taskTypeLabel = computed(() => {
  if (!props.runStatus?.task_type) return '未知'
  return TASK_TYPE_LABELS[props.runStatus.task_type] ?? props.runStatus.task_type
})

const providerPathLabel = computed(() => {
  const current = props.runStatus
  if (!current?.provider_success_path) return '未记录'
  return current.provider_success_path === 'plain_json_fallback' ? 'plain JSON fallback' : 'structured'
})

const executionSemantics = computed(() => {
  const current = props.runStatus
  if (!current) return null
  if (current.requested_runtime_mode === 'agents_sdk' && current.used_mock_fallback) {
    return {
      tone: 'warning',
      title: '本次结果来自 mock 降级',
      description:
        current.fallback_reason ||
        '本次原本请求 Ark Agents SDK，但真实 provider 路径失败，最终由 mock 补全产物。',
    }
  }
  if (
    current.requested_runtime_mode === 'agents_sdk' &&
    current.effective_runtime_mode === 'agents_sdk' &&
    !current.used_mock_fallback
  ) {
    const providerLabel =
      current.provider_success_path === 'plain_json_fallback' ? 'Ark JSON fallback 收敛成功' : 'Ark structured 直出'
    return {
      tone: current.status === 'awaiting_review' ? 'info' : 'success',
      title: current.status === 'awaiting_review' ? `${providerLabel}，当前待审核` : providerLabel,
      description:
        current.status === 'awaiting_review'
          ? '真实 provider 已返回结果，但当前输出仍需人工审核后再视为最终完成。'
          : current.provider_success_path === 'plain_json_fallback'
            ? '本次请求先尝试 structured 输出，随后由 Ark 的 plain JSON 路径完成收敛，未使用 mock。'
            : '本次请求由 Ark structured 输出直接完成，未使用 JSON fallback 或 mock fallback。',
    }
  }
  if (current.requested_runtime_mode === 'mock') {
    return {
      tone: 'info',
      title: '本次结果来自本地 mock',
      description: '当前运行未请求真实 provider，结果来自本地 mock 路径。',
    }
  }
  return null
})

function stateLabel(state: AgentRunState) {
  return STATE_LABELS[state] ?? state
}
</script>

<style scoped>
.panel-card { background:#fff; border:1px solid #d2d2d7; border-radius:16px; padding:20px; }
.section-header { display:flex; justify-content:space-between; align-items:flex-start; gap:12px; }
.section-header h3 { font-size:18px; color:#1d1d1f; }
.section-header p { margin-top:6px; color:#6e6e73; font-size:14px; }
.refresh-btn { border:none; border-radius:10px; padding:8px 12px; background:#e8e8ed; color:#1d1d1f; cursor:pointer; }
.empty-state { margin-top:16px; color:#6e6e73; }
.status-grid { margin-top:16px; display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:14px; }
.status-item { display:flex; flex-direction:column; gap:6px; }
.status-label { font-size:12px; font-weight:600; color:#6e6e73; text-transform:uppercase; letter-spacing:.05em; }
.status-badge { width:fit-content; border-radius:999px; padding:4px 10px; font-size:12px; font-weight:700; text-transform:uppercase; background:#e8e8ed; color:#1d1d1f; }
.status-badge[data-status='queued'] { background:#fff3cd; color:#7a5a00; }
.status-badge[data-status='running'] { background:#e7f0ff; color:#0055aa; }
.status-badge[data-status='completed'] { background:#e8f5e9; color:#1e7a34; }
.status-badge[data-status='cancelled'] { background:#f4f4f5; color:#4b5563; }
.status-badge[data-status='failed'] { background:#fff1f0; color:#b42318; }
.status-badge[data-status='awaiting_review'] { background:#fff8e1; color:#915f00; }
.pill-row { margin-top:16px; display:flex; flex-wrap:wrap; gap:8px; }
.state-pill { padding:6px 10px; border-radius:999px; background:#f5f5f7; border:1px solid #d2d2d7; font-size:12px; color:#1d1d1f; }
.summary-text { margin-top:16px; line-height:1.6; color:#1d1d1f; }
.actions-row { margin-top:16px; display:flex; flex-wrap:wrap; gap:10px; }
.action-btn { border:none; border-radius:10px; padding:9px 14px; font-size:14px; background:#0071e3; color:#fff; cursor:pointer; }
.action-btn.secondary { background:#e8e8ed; color:#1d1d1f; }
.action-btn.warning { background:#fff3cd; color:#7a5a00; }
.action-btn.success { background:#e8f5e9; color:#1e7a34; }
.action-btn.danger { background:#fff1f0; color:#b42318; }
.action-btn:disabled { opacity:.6; cursor:default; }
.alert-box { margin-top:16px; border-radius:12px; padding:12px 14px; background:#f5f5f7; color:#1d1d1f; }
.alert-box.info { background:#eef6ff; color:#0055aa; }
.alert-box.success { background:#e8f5e9; color:#1e7a34; }
.alert-box.warning { background:#fff8e1; color:#915f00; }
.alert-box.error { background:#fff1f0; color:#b42318; }
.alert-box ul { margin-top:8px; padding-left:18px; }
.alert-box p { margin-top:8px; }
@media (max-width:768px) { .status-grid { grid-template-columns:1fr; } }
</style>
