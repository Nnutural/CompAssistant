<template>
  <section class="panel-card">
    <div class="section-header">
      <div>
        <h3>结果产物</h3>
        <p>任务终态后展示结构化 artifacts，便于前端卡片化接入。</p>
      </div>
      <button
        v-if="runStatus"
        class="refresh-btn"
        type="button"
        :disabled="loading"
        @click="$emit('refresh')"
      >
        {{ loading ? '加载中...' : '刷新产物' }}
      </button>
    </div>

    <div v-if="!runStatus" class="empty-state">
      请先选择或创建任务。
    </div>

    <div
      v-else-if="!items.length && runStatus.status !== 'completed' && runStatus.status !== 'awaiting_review' && runStatus.status !== 'cancelled'"
      class="empty-state"
    >
      任务结束后会在这里显示结构化结果。
    </div>

    <div v-else-if="!items.length" class="warning-state">
      当前终态任务没有可展示的结构化产物。
    </div>

    <div v-else class="artifact-list">
      <article v-for="item in items" :key="item.artifact_id" class="artifact-card">
        <header class="artifact-header">
          <div>
            <h4>{{ item.title }}</h4>
            <span>{{ item.artifact_type }}</span>
          </div>
        </header>
        <pre>{{ formatPayload(item.payload ?? item.ref ?? null) }}</pre>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { AgentTaskArtifactItem, AgentTaskStatusResponse } from '../../../types/agent'

defineProps<{
  items: AgentTaskArtifactItem[]
  loading: boolean
  runStatus: AgentTaskStatusResponse | null
}>()

defineEmits<{
  (event: 'refresh'): void
}>()

function formatPayload(value: unknown) {
  return JSON.stringify(value, null, 2)
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

.refresh-btn:disabled {
  cursor: default;
  opacity: 0.6;
}

.empty-state,
.warning-state {
  margin-top: 16px;
  color: #6e6e73;
}

.warning-state {
  color: #915f00;
}

.artifact-list {
  margin-top: 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.artifact-card {
  border: 1px solid #e8e8ed;
  border-radius: 12px;
  padding: 16px;
  background: #f5f5f7;
}

.artifact-header h4 {
  font-size: 16px;
  color: #1d1d1f;
}

.artifact-header span {
  display: inline-block;
  margin-top: 4px;
  font-size: 12px;
  color: #6e6e73;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.artifact-card pre {
  margin-top: 12px;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.5;
  color: #1d1d1f;
}
</style>
