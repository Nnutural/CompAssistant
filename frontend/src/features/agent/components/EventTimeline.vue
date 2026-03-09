<template>
  <section class="panel-card">
    <div class="section-header">
      <div>
        <h3>事件时间线</h3>
        <p>按轮询结果展示任务在 runtime 中的推进过程。</p>
      </div>
    </div>

    <div v-if="!items.length" class="empty-state">
      当前还没有事件记录。
    </div>

    <ol v-else class="timeline">
      <li v-for="item in items" :key="item.event_id" class="timeline-item">
        <div class="timeline-dot" :data-status="item.status"></div>
        <div class="timeline-body">
          <div class="timeline-top">
            <strong>{{ stateLabel(item.state) }}</strong>
            <span>{{ formatDate(item.created_at) }}</span>
          </div>
          <p>{{ item.message }}</p>
          <small v-if="item.actor">执行方：{{ item.actor }}</small>
        </div>
      </li>
    </ol>
  </section>
</template>

<script setup lang="ts">
import type { AgentTaskEventItem } from '../../../types/agent'
import { STATE_LABELS } from '../config'

defineProps<{
  items: AgentTaskEventItem[]
}>()

function formatDate(value: string) {
  return new Date(value).toLocaleString()
}

function stateLabel(state: string) {
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

.section-header h3 {
  font-size: 18px;
  color: #1d1d1f;
}

.section-header p {
  margin-top: 6px;
  color: #6e6e73;
  font-size: 14px;
}

.empty-state {
  margin-top: 16px;
  color: #6e6e73;
}

.timeline {
  list-style: none;
  margin-top: 18px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.timeline-item {
  display: grid;
  grid-template-columns: 20px 1fr;
  gap: 12px;
}

.timeline-dot {
  margin-top: 7px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #86868b;
}

.timeline-dot[data-status='completed'] {
  background: #1e7a34;
}

.timeline-dot[data-status='error'] {
  background: #b42318;
}

.timeline-dot[data-status='warning'] {
  background: #b7791f;
}

.timeline-dot[data-status='fallback'] {
  background: #0055aa;
}

.timeline-body {
  border-left: 1px solid #e8e8ed;
  padding-left: 14px;
}

.timeline-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 14px;
  color: #6e6e73;
}

.timeline-body p {
  margin-top: 6px;
  color: #1d1d1f;
  line-height: 1.5;
}

.timeline-body small {
  display: block;
  margin-top: 6px;
  color: #6e6e73;
}
</style>
