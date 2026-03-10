<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <h1>CompAssistant</h1>
        <p>大学生竞赛助手与智能体演示面板</p>
      </div>

      <nav class="menu">
        <button
          type="button"
          :class="['menu-item', { active: currentView === 'competitions' }]"
          data-testid="nav-competitions"
          @click="currentView = 'competitions'"
        >
          竞赛列表
        </button>
        <button
          type="button"
          :class="['menu-item', { active: currentView === 'guide' }]"
          data-testid="nav-guide"
          @click="currentView = 'guide'"
        >
          使用说明
        </button>
        <button
          type="button"
          :class="['menu-item', { active: currentView === 'agent' }]"
          data-testid="nav-agent"
          @click="currentView = 'agent'"
        >
          智能体面板
        </button>
      </nav>
    </aside>

    <main class="main-content">
      <div v-if="currentView === 'competitions'" class="view">
        <CompetitionList />
      </div>

      <div v-else-if="currentView === 'guide'" class="view">
        <Guide />
      </div>

      <div v-else class="view">
        <AgentPanel />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'

import CompetitionList from './components/CompetitionList.vue'
import Guide from './components/Guide.vue'
import AgentPanel from './features/agent/AgentPanel.vue'

const currentView = ref('competitions')
</script>

<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; background-color:#fff; color:#1d1d1f; }
button,input,select,textarea { font:inherit; }
.app-shell { display:flex; min-height:100vh; background-color:#fff; }
.sidebar { width:240px; background-color:#f5f5f7; border-right:1px solid #d2d2d7; display:flex; flex-direction:column; padding:24px 16px; gap:28px; }
.brand h1 { font-size:24px; font-weight:700; color:#1d1d1f; }
.brand p { margin-top:8px; color:#6e6e73; font-size:14px; line-height:1.5; }
.menu { display:flex; flex-direction:column; gap:6px; }
.menu-item { border:none; border-radius:10px; background:transparent; color:#1d1d1f; padding:12px 14px; text-align:left; cursor:pointer; transition:background-color .2s ease, box-shadow .2s ease; }
.menu-item:hover { background:#e8e8ed; }
.menu-item.active { background:#fff; box-shadow:inset 0 0 0 1px #d2d2d7; font-weight:600; }
.main-content { flex:1; min-width:0; background:#fff; }
.view { width:100%; min-height:100vh; }
@media (max-width:900px) {
  .app-shell { flex-direction:column; }
  .sidebar { width:100%; border-right:none; border-bottom:1px solid #d2d2d7; }
  .menu { flex-direction:row; flex-wrap:wrap; }
}
</style>
