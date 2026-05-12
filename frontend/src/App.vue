<template>
  <div class="app">
    <header class="app-header">
      <div class="header-left">
        <span class="app-title">Review Workspace</span>
      </div>
      <div class="header-right">
        <span class="reviewer-label">Signed in as</span>
        <span class="reviewer-name">{{ REVIEWER }}</span>
        <button class="btn btn-primary btn-sm" @click="showNewTicketModal = true">+ New Ticket</button>
      </div>
    </header>

    <div class="workspace">
      <QueuePanel
        :items="allItems"
        :selected-id="selectedId"
        :loading="queueLoading"
        :error="queueError"
        :reviewer="REVIEWER"
        :active-tab="activeTab"
        @select="selectItem"
        @deselect="clearSelection"
        @update:activeTab="activeTab = $event"
      />

      <TicketDetail
        :selected-id="selectedId"
        :selected-item="selectedItem"
        :loading="detailLoading"
        :error="detailError"
        :reviewer="REVIEWER"
        @item-updated="onItemUpdated"
        @queue-refresh="loadQueue"
      />
    </div>

    <NewTicketModal
      v-if="showNewTicketModal"
      @created="onTicketCreated"
      @close="showNewTicketModal = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import QueuePanel from './components/QueuePanel.vue'
import TicketDetail from './components/TicketDetail.vue'
import NewTicketModal from './components/NewTicketModal.vue'

const API_BASE = 'http://localhost:8000'
const REVIEWER = 'alex'

// Queue state
const allItems = ref([])
const queueLoading = ref(false)
const queueError = ref(null)
const activeTab = ref('active')

// Detail state
const selectedId = ref(null)
const selectedItem = ref(null)
const detailLoading = ref(false)
const detailError = ref(null)

// Modal state
const showNewTicketModal = ref(false)

async function loadQueue() {
  queueLoading.value = true
  queueError.value = null
  try {
    const res = await fetch(`${API_BASE}/api/items`)
    if (!res.ok) throw new Error(`Server error: ${res.status}`)
    allItems.value = await res.json()
  } catch (e) {
    queueError.value = e.message
  } finally {
    queueLoading.value = false
  }
}

async function selectItem(id) {
  selectedId.value = id
  detailLoading.value = true
  detailError.value = null
  selectedItem.value = null
  try {
    const res = await fetch(`${API_BASE}/api/items/${id}`)
    if (!res.ok) throw new Error(`Server error: ${res.status}`)
    selectedItem.value = await res.json()
  } catch (e) {
    detailError.value = e.message
  } finally {
    detailLoading.value = false
  }
}

function clearSelection() {
  selectedId.value = null
  selectedItem.value = null
}

function onItemUpdated(item) {
  selectedItem.value = item
  const idx = allItems.value.findIndex(i => i.id === item.id)
  if (idx !== -1) allItems.value[idx] = item
  activeTab.value = tabForStatus(item.status)
}

function tabForStatus(status) {
  if (status === 'unassigned') return 'active'
  if (status === 'in_review') return 'in_review'
  return 'closed'
}

async function onTicketCreated(item) {
  showNewTicketModal.value = false
  await loadQueue()
  await selectItem(item.id)
}

onMounted(loadQueue)
</script>

<style>
.app { display: flex; flex-direction: column; height: 100%; }

.app-header {
  height: var(--header-h);
  background: #1e293b;
  color: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  flex-shrink: 0;
  gap: 16px;
}

.app-title { font-size: 1rem; font-weight: 600; letter-spacing: .01em; }

.header-right { display: flex; align-items: center; gap: 12px; font-size: .85rem; }
.reviewer-label { color: #94a3b8; }
.reviewer-name { font-weight: 600; color: #e2e8f0; }
.workspace { display: flex; flex: 1; overflow: hidden; }
</style>
