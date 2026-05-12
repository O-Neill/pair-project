<template>
  <aside class="queue-panel">
    <div class="panel-header">
      <div class="tab-bar">
        <button
          v-for="tab in TABS"
          :key="tab.key"
          :class="['tab-btn', { active: activeTab === tab.key }]"
          @click="switchTab(tab.key)"
        >
          {{ tab.label }}
          <span class="count-badge">{{ tabCount(tab.key) }}</span>
        </button>
      </div>
      <div v-if="activeTab === 'in_review' || activeTab === 'closed'" class="tab-filter-row">
        <label class="filter-checkbox">
          <input v-model="showMyOnly" type="checkbox" />
          <span>Show only my tickets</span>
        </label>
      </div>
    </div>

    <div v-if="loading" class="state-msg loading-msg">
      <span class="spinner"></span> Loading…
    </div>
    <div v-else-if="error" class="state-msg error-msg">{{ error }}</div>
    <div v-else-if="filteredQueue.length === 0" class="state-msg empty-msg">No items found.</div>

    <ul v-else class="queue-list">
      <li
        v-for="(item, index) in filteredQueue"
        :key="item.id"
        class="queue-item"
        :class="{
          selected: selectedId === item.id,
          terminal: isTerminal(item.status),
        }"
        @click="$emit('select', item.id)"
      >
        <div :class="['rank-bar', 'risk-bar-' + item.risk_level]"></div>
        <div class="queue-item-body">
          <div class="queue-item-top">
            <span class="queue-rank">#{{ index + 1 }}</span>
            <span :class="['badge', 'risk-' + item.risk_level]">
              {{ item.risk_level.toUpperCase() }}
            </span>
            <span v-if="item.customer_tier === 'priority'" class="badge tier-priority">PRIORITY</span>
            <span :class="['badge', 'status-' + item.status]">{{ formatStatus(item.status) }}</span>
          </div>
          <div class="queue-item-title">{{ item.title }}</div>
          <div class="queue-item-footer">
            <span class="item-id">{{ item.id }}</span>
            <span class="item-date">{{ formatDateShort(item.submitted_at) }}</span>
            <span v-if="item.assigned_reviewer" class="item-assignee">→ {{ item.assigned_reviewer }}</span>
          </div>
        </div>
      </li>
    </ul>
  </aside>
</template>

<script setup>
import { computed, ref } from 'vue'

const TERMINAL_STATES = new Set(['approved', 'rejected', 'escalated'])

const TABS = [
  { key: 'active', label: 'Active' },
  { key: 'in_review', label: 'In Review' },
  { key: 'closed', label: 'Closed' },
]

const props = defineProps({
  items: { type: Array, default: () => [] },
  selectedId: { type: String, default: null },
  loading: { type: Boolean, default: false },
  error: { type: String, default: null },
  reviewer: { type: String, required: true },
  activeTab: { type: String, default: 'active' },
})

const emit = defineEmits(['select', 'deselect', 'update:activeTab'])

const showMyOnly = ref(false)

const filteredQueue = computed(() => {
  if (props.activeTab === 'active') {
    return props.items.filter(i => i.status === 'unassigned')
  }
  if (props.activeTab === 'in_review') {
    return props.items.filter(i => {
      if (i.status !== 'in_review') return false
      if (!showMyOnly.value) return true
      return i.assigned_reviewer === props.reviewer
    })
  }
  return props.items.filter(i => {
    if (!isTerminal(i.status)) return false
    if (!showMyOnly.value) return true
    return i.assigned_reviewer === props.reviewer
  })
})

function tabCount(tabKey) {
  if (tabKey === 'active') return props.items.filter(i => i.status === 'unassigned').length
  if (tabKey === 'in_review') return props.items.filter(i => i.status === 'in_review').length
  return props.items.filter(i => isTerminal(i.status)).length
}

function switchTab(tabKey) {
  emit('update:activeTab', tabKey)
  if (tabKey !== 'in_review' && tabKey !== 'closed') {
    showMyOnly.value = false
  }
  emit('deselect')
}

function isTerminal(status) {
  return TERMINAL_STATES.has(status)
}

function formatStatus(status) {
  const labels = {
    unassigned: 'Unassigned',
    in_review: 'In Review',
    approved: 'Approved',
    rejected: 'Rejected',
    escalated: 'Escalated',
  }
  return labels[status] ?? status
}

function formatDateShort(iso) {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}
</script>

<style scoped>
.queue-panel {
  width: 340px;
  flex-shrink: 0;
  background: var(--surface);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.tab-filter-row {
  padding: 10px 12px 12px;
  border-top: 1px solid #eef2f7;
  background: #fbfdff;
}

.filter-checkbox {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: .82rem;
  color: var(--text-muted);
  cursor: pointer;
  user-select: none;
}

.filter-checkbox input {
  width: 15px;
  height: 15px;
  margin: 0;
  accent-color: #2563eb;
}

.tab-bar {
  display: flex;
}

.tab-btn {
  flex: 1;
  padding: 10px 8px;
  font-size: .8rem;
  font-weight: 600;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  transition: color .15s, border-color .15s;
}

.tab-btn:hover { color: var(--text); }
.tab-btn.active { color: #2563eb; border-bottom-color: #2563eb; }
.tab-btn.active .count-badge { background: #dbeafe; color: #1d4ed8; }

.count-badge {
  background: #e5e7eb;
  color: #374151;
  font-size: .75rem;
  font-weight: 600;
  padding: 1px 7px;
  border-radius: 99px;
}

.queue-list { list-style: none; overflow-y: auto; flex: 1; }

.queue-item {
  display: flex;
  cursor: pointer;
  border-bottom: 1px solid var(--border);
  transition: background .1s;
}

.queue-item:hover { background: #f9fafb; }
.queue-item.selected { background: #eff6ff; }
.queue-item.terminal { opacity: .65; }

.rank-bar { width: 4px; flex-shrink: 0; }
.risk-bar-high { background: var(--risk-high); }
.risk-bar-medium { background: var(--risk-med); }
.risk-bar-low { background: var(--risk-low); }

.queue-item-body { flex: 1; padding: 10px 12px; min-width: 0; }

.queue-item-top { display: flex; align-items: center; gap: 5px; margin-bottom: 4px; }

.queue-rank { font-size: .72rem; font-weight: 700; color: var(--text-muted); margin-right: 2px; }

.queue-item-title {
  font-size: .88rem;
  font-weight: 500;
  line-height: 1.35;
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.queue-item-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: .74rem;
  color: var(--text-muted);
}

.item-id { font-family: var(--mono); }
.item-assignee { color: #2563eb; }
</style>
