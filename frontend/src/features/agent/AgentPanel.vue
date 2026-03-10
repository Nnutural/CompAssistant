<template>
  <div class="agent-panel" data-testid="agent-panel-view">
    <TaskForm :submitting="isSubmitting" @submit="handleSubmit" />

    <div class="panel-grid">
      <RunStatus
        :run-status="runStatus"
        :network-error="networkError"
        :notice-message="noticeMessage"
        :action-busy="isActionBusy"
        @refresh="refreshRun"
        @retry="handleRetry"
        @cancel="handleCancel"
        @review="handleReview"
      />
      <EventTimeline :items="eventItems" />
    </div>

    <ArtifactPanel
      :items="artifactItems"
      :loading="isArtifactsLoading"
      :run-status="runStatus"
      @refresh="refreshArtifacts"
    />

    <TaskHistoryList
      :items="historyItems"
      :total="historyTotal"
      :loading="isHistoryLoading"
      :current-run-id="currentRunId"
      :status-filter="historyStatusFilter"
      :task-type-filter="historyTaskTypeFilter"
      :can-load-more="canLoadMore"
      @refresh="refreshHistory"
      @load-more="loadMoreHistory"
      @select="selectRun"
      @change-status="handleStatusFilterChange"
      @change-task-type="handleTaskTypeFilterChange"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import {
  cancelAgentTask,
  createAgentTask,
  getAgentTaskArtifacts,
  getAgentTaskEvents,
  getAgentTaskStatus,
  listAgentTasks,
  retryAgentTask,
  reviewAgentTask,
} from '../../api/agent'
import type {
  AgentTaskArtifactItem,
  AgentTaskCreateRequest,
  AgentTaskEventItem,
  AgentTaskHistoryItem,
  AgentTaskReviewRequest,
  AgentTaskStatusResponse,
} from '../../types/agent'
import { AGENT_HISTORY_PAGE_SIZE, AGENT_POLL_INTERVAL_MS, TERMINAL_RUN_STATUSES } from './config'
import ArtifactPanel from './components/ArtifactPanel.vue'
import EventTimeline from './components/EventTimeline.vue'
import RunStatus from './components/RunStatus.vue'
import TaskForm from './components/TaskForm.vue'
import TaskHistoryList from './components/TaskHistoryList.vue'

const runStatus = ref<AgentTaskStatusResponse | null>(null)
const eventItems = ref<AgentTaskEventItem[]>([])
const artifactItems = ref<AgentTaskArtifactItem[]>([])
const historyItems = ref<AgentTaskHistoryItem[]>([])
const historyTotal = ref(0)
const historyStatusFilter = ref('')
const historyTaskTypeFilter = ref('')
const isSubmitting = ref(false)
const isArtifactsLoading = ref(false)
const isHistoryLoading = ref(false)
const isPolling = ref(false)
const isActionBusy = ref(false)
const networkError = ref('')
const noticeMessage = ref('')

let pollTimer: number | null = null

const currentRunId = computed(() => runStatus.value?.run_id ?? null)
const canLoadMore = computed(() => historyItems.value.length < historyTotal.value)

function isTerminalStatus(status: AgentTaskStatusResponse['status']) {
  return TERMINAL_RUN_STATUSES.includes(status)
}

function stopPolling() {
  if (pollTimer !== null) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}

function startPolling(runId: string) {
  stopPolling()
  pollTimer = window.setInterval(() => void pollRun(runId), AGENT_POLL_INTERVAL_MS)
}

async function handleSubmit(request: AgentTaskCreateRequest) {
  stopPolling()
  isSubmitting.value = true
  isArtifactsLoading.value = false
  networkError.value = ''
  noticeMessage.value = ''
  eventItems.value = []
  artifactItems.value = []

  try {
    const created = await createAgentTask(request)
    runStatus.value = created
    noticeMessage.value = `任务已创建，run_id 为 ${created.run_id}。`
    await refreshEvents(created.run_id)
    await refreshHistory()

    if (isTerminalStatus(created.status)) {
      await refreshArtifacts()
    } else {
      startPolling(created.run_id)
    }
  } catch (error) {
    networkError.value = error instanceof Error ? error.message : '创建任务失败。'
  } finally {
    isSubmitting.value = false
  }
}

async function pollRun(runId: string) {
  if (isPolling.value) return
  isPolling.value = true
  try {
    const status = await getAgentTaskStatus(runId)
    runStatus.value = status
    networkError.value = ''
    await refreshEvents(runId)

    if (isTerminalStatus(status.status)) {
      stopPolling()
      await refreshArtifacts()
      await refreshHistory()
    }
  } catch (error) {
    networkError.value = error instanceof Error ? error.message : '轮询任务状态失败。'
  } finally {
    isPolling.value = false
  }
}

async function refreshEvents(runId: string) {
  eventItems.value = (await getAgentTaskEvents(runId)).items
}

async function refreshArtifacts() {
  if (!currentRunId.value) return
  isArtifactsLoading.value = true
  try {
    artifactItems.value = (await getAgentTaskArtifacts(currentRunId.value)).items
    networkError.value = ''
  } catch (error) {
    networkError.value = error instanceof Error ? error.message : '读取产物失败。'
  } finally {
    isArtifactsLoading.value = false
  }
}

async function refreshRun() {
  if (currentRunId.value) {
    await pollRun(currentRunId.value)
  }
}

async function refreshHistory() {
  isHistoryLoading.value = true
  try {
    const response = await listAgentTasks({
      status: historyStatusFilter.value || undefined,
      task_type: historyTaskTypeFilter.value || undefined,
      limit: AGENT_HISTORY_PAGE_SIZE,
      offset: 0,
    })
    historyItems.value = response.items
    historyTotal.value = response.total
  } catch (error) {
    networkError.value = error instanceof Error ? error.message : '读取历史任务失败。'
  } finally {
    isHistoryLoading.value = false
  }
}

async function loadMoreHistory() {
  isHistoryLoading.value = true
  try {
    const response = await listAgentTasks({
      status: historyStatusFilter.value || undefined,
      task_type: historyTaskTypeFilter.value || undefined,
      limit: AGENT_HISTORY_PAGE_SIZE,
      offset: historyItems.value.length,
    })
    historyItems.value = historyItems.value.concat(response.items)
    historyTotal.value = response.total
  } catch (error) {
    networkError.value = error instanceof Error ? error.message : '加载更多历史任务失败。'
  } finally {
    isHistoryLoading.value = false
  }
}

async function selectRun(runId: string) {
  stopPolling()
  noticeMessage.value = ''
  networkError.value = ''
  try {
    const status = await getAgentTaskStatus(runId)
    runStatus.value = status
    await refreshEvents(runId)
    if (isTerminalStatus(status.status)) {
      await refreshArtifacts()
    } else {
      artifactItems.value = []
      startPolling(runId)
    }
  } catch (error) {
    networkError.value = error instanceof Error ? error.message : '读取任务详情失败。'
  }
}

async function handleRetry() {
  if (!currentRunId.value) return
  isActionBusy.value = true
  noticeMessage.value = ''
  networkError.value = ''
  try {
    const response = await retryAgentTask(currentRunId.value)
    runStatus.value = response.new_run
    eventItems.value = []
    artifactItems.value = []
    noticeMessage.value = `已从 ${response.source_run_id} 创建重试任务 ${response.new_run.run_id}。`
    await refreshEvents(response.new_run.run_id)
    await refreshHistory()
    if (isTerminalStatus(response.new_run.status)) {
      await refreshArtifacts()
    } else {
      startPolling(response.new_run.run_id)
    }
  } catch (error) {
    networkError.value = error instanceof Error ? error.message : '重试任务失败。'
  } finally {
    isActionBusy.value = false
  }
}

async function handleCancel() {
  if (!currentRunId.value) return
  const note = window.prompt('请输入取消说明（可选）', '操作员取消任务')
  if (note === null) return
  isActionBusy.value = true
  noticeMessage.value = ''
  networkError.value = ''
  try {
    const response = await cancelAgentTask(currentRunId.value, { note })
    stopPolling()
    runStatus.value = response.task
    noticeMessage.value = response.message
    await refreshEvents(currentRunId.value)
    await refreshArtifacts()
    await refreshHistory()
  } catch (error) {
    networkError.value = error instanceof Error ? error.message : '取消任务失败。'
  } finally {
    isActionBusy.value = false
  }
}

async function handleReview(decision: AgentTaskReviewRequest['decision']) {
  if (!currentRunId.value) return
  const placeholder =
    decision === 'accept'
      ? '人工审核通过'
      : decision === 'reject'
        ? '人工审核驳回'
        : '请填写审核备注'
  const note = window.prompt('请输入审核说明', placeholder)
  if (note === null) return
  isActionBusy.value = true
  noticeMessage.value = ''
  networkError.value = ''
  try {
    const response = await reviewAgentTask(currentRunId.value, { decision, note })
    runStatus.value = response.task
    noticeMessage.value = response.message
    await refreshEvents(currentRunId.value)
    await refreshArtifacts()
    await refreshHistory()
    if (!isTerminalStatus(response.task.status)) {
      startPolling(currentRunId.value)
    } else {
      stopPolling()
    }
  } catch (error) {
    networkError.value = error instanceof Error ? error.message : '审核操作失败。'
  } finally {
    isActionBusy.value = false
  }
}

async function handleStatusFilterChange(value: string) {
  historyStatusFilter.value = value
  await refreshHistory()
}

async function handleTaskTypeFilterChange(value: string) {
  historyTaskTypeFilter.value = value
  await refreshHistory()
}

onMounted(() => {
  void refreshHistory()
})

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<style scoped>
.agent-panel { display:flex; flex-direction:column; gap:20px; padding:24px; background:#fff; min-height:100%; }
.panel-grid { display:grid; grid-template-columns:minmax(0,1.1fr) minmax(0,1fr); gap:20px; }
@media (max-width:960px) { .panel-grid { grid-template-columns:1fr; } }
</style>
