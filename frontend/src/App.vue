<template>
  <div class="app">
    <header class="app-header">
      <div class="header-left">
        <span class="app-title">Review Workspace</span>
      </div>
      <div class="header-right">
        <span class="reviewer-label">Signed in as</span>
        <span class="reviewer-name">{{ REVIEWER }}</span>
        <button class="btn btn-primary btn-sm" @click="openNewTicketModal">+ New Ticket</button>
      </div>
    </header>

    <div class="workspace">
      <!-- Queue Panel -->
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
              <input v-model="showMyInReviewOnly" type="checkbox" />
              <span>Show only my tickets</span>
            </label>
          </div>
        </div>

        <div v-if="queueLoading" class="state-msg loading-msg">
          <span class="spinner"></span> Loading…
        </div>
        <div v-else-if="queueError" class="state-msg error-msg">{{ queueError }}</div>
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
            @click="selectItem(item.id)"
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

      <!-- Detail Panel -->
      <main class="detail-panel">
        <div v-if="!selectedId" class="empty-detail">
          <p>Select an item from the queue to inspect it.</p>
        </div>

        <div v-else-if="detailLoading" class="state-msg loading-msg">
          <span class="spinner"></span> Loading…
        </div>

        <div v-else-if="detailError" class="state-msg error-msg">{{ detailError }}</div>

        <div v-else-if="selectedItem" class="detail-content">
          <!-- Header -->
          <div class="detail-header">
            <div class="detail-id-row">
              <span class="detail-id">{{ selectedItem.id }}</span>
              <span :class="['badge', 'status-' + selectedItem.status, 'badge-lg']">
                {{ formatStatus(selectedItem.status) }}
              </span>
            </div>
            <div class="title-edit-row">
              <template v-if="editingTitle">
                <input
                  v-model="editTitle"
                  class="title-input"
                  type="text"
                  @keyup.enter="saveTitle"
                  @keyup.escape="cancelTitleEdit"
                  ref="titleInputRef"
                />
                <button class="btn btn-primary btn-sm" :disabled="!editTitle.trim() || titleSaving" @click="saveTitle">
                  {{ titleSaving ? 'Saving…' : 'Save' }}
                </button>
                <button class="btn btn-secondary btn-sm" @click="cancelTitleEdit">Cancel</button>
              </template>
              <template v-else>
                <h2 class="detail-title">{{ selectedItem.title }}</h2>
                <button
                  v-if="canEditSelectedItem"
                  class="pencil-btn"
                  title="Edit title"
                  @click="startTitleEdit"
                >✏️</button>
              </template>
            </div>
          </div>

          <!-- Metadata -->
          <div class="detail-meta">
            <div class="meta-item">
              <span class="meta-label">Risk</span>
              <span :class="['badge', 'risk-' + selectedItem.risk_level]">
                {{ selectedItem.risk_level.toUpperCase() }}
              </span>
            </div>
            <div class="meta-item">
              <span class="meta-label">Tier</span>
              <span :class="['badge', selectedItem.customer_tier === 'priority' ? 'tier-priority' : 'tier-standard']">
                {{ selectedItem.customer_tier }}
              </span>
            </div>
            <div class="meta-item">
              <span class="meta-label">Submitted</span>
              <span class="meta-value">{{ formatDateFull(selectedItem.submitted_at) }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">Assigned to</span>
              <span class="meta-value">{{ selectedItem.assigned_reviewer ?? '—' }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">Notes</span>
              <span class="meta-value">{{ selectedItem.notes_count }}</span>
            </div>
          </div>

          <!-- Summary -->
          <div class="detail-section">
            <h3 class="section-title">Summary</h3>
            <p class="summary-text">{{ selectedItem.summary }}</p>
          </div>

          <!-- Actions -->
          <div class="detail-section actions-section">
            <h3 class="section-title">Actions</h3>

            <!-- Terminal state -->
            <div v-if="isTerminal(selectedItem.status)" class="action-buttons">
              <button
                class="btn btn-warn"
                :disabled="!!actionLoading"
                @click="performAction('reopen')"
              >
                {{ actionLoading === 'reopen' ? 'Reopening…' : 'Reopen to In Review' }}
              </button>
            </div>

            <div v-else class="action-buttons">
              <!-- Unassigned: can only be claimed -->
              <template v-if="selectedItem.status === 'unassigned'">
                <button
                  class="btn btn-primary"
                  :disabled="!!actionLoading"
                  @click="performAction('claim')"
                >
                  {{ actionLoading === 'claim' ? 'Claiming…' : 'Claim' }}
                </button>
                <span class="action-hint">Assigns to you and moves to In Review</span>
              </template>

              <!-- In review: approve / reject / escalate / unassign -->
              <template v-if="selectedItem.status === 'in_review'">
                <button
                  class="btn btn-success"
                  :disabled="!!actionLoading"
                  @click="performAction('approve')"
                >
                  {{ actionLoading === 'approve' ? 'Approving…' : 'Approve' }}
                </button>
                <button
                  class="btn btn-danger"
                  :disabled="!!actionLoading"
                  @click="performAction('reject')"
                >
                  {{ actionLoading === 'reject' ? 'Rejecting…' : 'Reject' }}
                </button>
                <button
                  class="btn btn-warn"
                  :disabled="!!actionLoading"
                  @click="performAction('escalate')"
                >
                  {{ actionLoading === 'escalate' ? 'Escalating…' : 'Escalate' }}
                </button>
                <button
                  class="btn btn-secondary"
                  :disabled="!!actionLoading"
                  @click="performAction('unassign')"
                >
                  {{ actionLoading === 'unassign' ? 'Unassigning…' : 'Unassign' }}
                </button>
              </template>
            </div>

            <div v-if="actionSuccess" class="action-feedback success-feedback">{{ actionSuccess }}</div>
            <div v-if="actionError" class="action-feedback error-feedback">{{ actionError }}</div>
          </div>

          <!-- Edit details (in_review only) -->
          <div v-if="canEditSelectedItem" class="detail-section">
            <h3 class="section-title">Edit Details</h3>
            <div class="edit-form">
              <div class="edit-row">
                <label class="edit-label">Risk Level</label>
                <select v-model="editRisk" class="edit-select">
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>
              <div class="edit-row">
                <label class="edit-label">Customer Tier</label>
                <select v-model="editTier" class="edit-select">
                  <option value="priority">Priority</option>
                  <option value="standard">Standard</option>
                </select>
              </div>
              <div class="edit-row edit-row-col">
                <label class="edit-label">Summary</label>
                <textarea v-model="editSummary" class="edit-textarea" rows="3"></textarea>
              </div>
              <div class="edit-actions">
                <button
                  class="btn btn-primary btn-sm"
                  :disabled="!!updateLoading || !editDirty"
                  @click="saveEdits"
                >
                  {{ updateLoading ? 'Saving…' : 'Save Changes' }}
                </button>
                <span v-if="!editDirty" class="action-hint">No changes</span>
              </div>
              <div v-if="updateError" class="action-feedback error-feedback">{{ updateError }}</div>
            </div>
          </div>

          <!-- Notes -->
          <div class="detail-section">
            <h3 class="section-title">Notes ({{ selectedItem.notes ? selectedItem.notes.length : 0 }})</h3>
            <div v-if="selectedItem.notes && selectedItem.notes.length" class="notes-list">
              <div v-for="note in selectedItem.notes" :key="note.id" class="note-item">
                <div class="note-header">
                  <span class="note-author">{{ note.author }}</span>
                  <span class="note-date">{{ formatDateFull(note.created_at) }}</span>
                </div>
                <p class="note-content">{{ note.content }}</p>
              </div>
            </div>
            <p v-else class="notes-empty">No notes yet.</p>

            <div v-if="canEditSelectedItem" class="add-note-form">
              <textarea
                v-model="newNoteContent"
                class="edit-textarea"
                rows="2"
                placeholder="Add a note…"
              ></textarea>
              <button
                class="btn btn-primary btn-sm"
                :disabled="!!noteLoading || !newNoteContent.trim()"
                @click="submitNote"
              >
                {{ noteLoading ? 'Adding…' : 'Add Note' }}
              </button>
              <div v-if="noteError" class="action-feedback error-feedback">{{ noteError }}</div>
            </div>
          </div>
        </div>
      </main>
    </div>

    <!-- New Ticket Modal -->
    <div v-if="showNewTicketModal" class="modal-overlay" @click.self="closeNewTicketModal">
      <div class="modal">
        <h2 class="modal-title">New Ticket</h2>
        <div class="edit-form">
          <div class="edit-row edit-row-col">
            <label class="edit-label">Title</label>
            <input v-model="newTicket.title" class="edit-input" type="text" placeholder="Short description" />
          </div>
          <div class="edit-row">
            <label class="edit-label">Risk Level</label>
            <select v-model="newTicket.risk_level" class="edit-select">
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
          <div class="edit-row">
            <label class="edit-label">Customer Tier</label>
            <select v-model="newTicket.customer_tier" class="edit-select">
              <option value="priority">Priority</option>
              <option value="standard">Standard</option>
            </select>
          </div>
          <div class="edit-row edit-row-col">
            <label class="edit-label">Summary</label>
            <textarea v-model="newTicket.summary" class="edit-textarea" rows="3" placeholder="Describe the case…"></textarea>
          </div>
        </div>
        <div class="modal-actions">
          <button
            class="btn btn-primary"
            :disabled="!!newTicketLoading || !newTicket.title.trim() || !newTicket.summary.trim()"
            @click="submitNewTicket"
          >
            {{ newTicketLoading ? 'Creating…' : 'Create Ticket' }}
          </button>
          <button class="btn btn-secondary" @click="closeNewTicketModal">Cancel</button>
        </div>
        <div v-if="newTicketError" class="action-feedback error-feedback">{{ newTicketError }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, watch } from 'vue'

const API_BASE = 'http://localhost:8000'
const REVIEWER = 'alex'

const TERMINAL_STATES = new Set(['approved', 'rejected', 'escalated'])

const TABS = [
  { key: 'active', label: 'Active' },
  { key: 'in_review', label: 'In Review' },
  { key: 'closed', label: 'Closed' },
]

// Queue state
const allItems = ref([])
const queueLoading = ref(false)
const queueError = ref(null)
const activeTab = ref('active')
const showMyInReviewOnly = ref(false)

// Detail state
const selectedId = ref(null)
const selectedItem = ref(null)
const detailLoading = ref(false)
const detailError = ref(null)

// Action state
const actionLoading = ref(null)
const actionSuccess = ref(null)
const actionError = ref(null)

// Edit state
const editTitle = ref('')
const editingTitle = ref(false)
const titleSaving = ref(false)
const titleInputRef = ref(null)
const editRisk = ref('')
const editTier = ref('')
const editSummary = ref('')
const updateLoading = ref(false)
const updateError = ref(null)

const editDirty = computed(() => {
  if (!selectedItem.value) return false
  return (
    editRisk.value !== selectedItem.value.risk_level ||
    editTier.value !== selectedItem.value.customer_tier ||
    editSummary.value !== selectedItem.value.summary
  )
})

const canEditSelectedItem = computed(() => {
  return selectedItem.value?.status === 'in_review' && selectedItem.value?.assigned_reviewer === REVIEWER
})

function startTitleEdit() {
  if (!canEditSelectedItem.value) return
  editTitle.value = selectedItem.value.title
  editingTitle.value = true
  setTimeout(() => titleInputRef.value?.focus(), 0)
}

function cancelTitleEdit() {
  editingTitle.value = false
}

async function saveTitle() {
  if (!canEditSelectedItem.value || !editTitle.value.trim()) return
  titleSaving.value = true
  updateError.value = null
  try {
    const res = await fetch(`${API_BASE}/api/items/${selectedId.value}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: editTitle.value.trim() }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail ?? `Server error: ${res.status}`)
    selectedItem.value = data
    editTitle.value = data.title
    editingTitle.value = false
    const idx = allItems.value.findIndex(i => i.id === data.id)
    if (idx !== -1) allItems.value[idx] = { ...allItems.value[idx], title: data.title, risk_level: data.risk_level, customer_tier: data.customer_tier }
  } catch (e) {
    updateError.value = e.message
  } finally {
    titleSaving.value = false
  }
}

// Note state
const newNoteContent = ref('')
const noteLoading = ref(false)
const noteError = ref(null)

// New ticket modal
const showNewTicketModal = ref(false)
const newTicket = ref({ title: '', risk_level: 'medium', customer_tier: 'standard', summary: '' })
const newTicketLoading = ref(false)
const newTicketError = ref(null)

// ---------------------------------------------------------------------------
// Computed queue lists per tab
// ---------------------------------------------------------------------------

const filteredQueue = computed(() => {
  if (activeTab.value === 'active') {
    return allItems.value.filter(i => i.status === 'unassigned')
  }
  if (activeTab.value === 'in_review') {
    return allItems.value.filter(i => {
      if (i.status !== 'in_review') return false
      if (!showMyInReviewOnly.value) return true
      return i.assigned_reviewer === REVIEWER
    })
  }
  return allItems.value.filter(i => {
    if (!isTerminal(i.status)) return false
    if (activeTab.value !== 'closed' || !showMyInReviewOnly.value) return true
    return i.assigned_reviewer === REVIEWER
  })
})

function tabCount(tabKey) {
  if (tabKey === 'active') return allItems.value.filter(i => i.status === 'unassigned').length
  if (tabKey === 'in_review') return allItems.value.filter(i => i.status === 'in_review').length
  return allItems.value.filter(i => isTerminal(i.status)).length
}

// ---------------------------------------------------------------------------
// Queue
// ---------------------------------------------------------------------------

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

function switchTab(tabKey) {
  activeTab.value = tabKey
  selectedId.value = null
  selectedItem.value = null
  if (tabKey !== 'in_review' && tabKey !== 'closed') {
    showMyInReviewOnly.value = false
  }
}

// ---------------------------------------------------------------------------
// Detail
// ---------------------------------------------------------------------------

async function selectItem(id) {
  selectedId.value = id
  actionSuccess.value = null
  actionError.value = null
  updateError.value = null
  noteError.value = null
  newNoteContent.value = ''
  editingTitle.value = false
  await loadDetail(id)
}

async function loadDetail(id) {
  detailLoading.value = true
  detailError.value = null
  selectedItem.value = null
  try {
    const res = await fetch(`${API_BASE}/api/items/${id}`)
    if (!res.ok) throw new Error(`Server error: ${res.status}`)
    const data = await res.json()
    selectedItem.value = data
    editTitle.value = data.title
    editRisk.value = data.risk_level
    editTier.value = data.customer_tier
    editSummary.value = data.summary
  } catch (e) {
    detailError.value = e.message
  } finally {
    detailLoading.value = false
  }
}

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

async function performAction(action) {
  actionLoading.value = action
  actionSuccess.value = null
  actionError.value = null

  const url = `${API_BASE}/api/items/${selectedId.value}/${action}`
  const options = {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  }
  if (action === 'claim') {
    options.body = JSON.stringify({ reviewer: REVIEWER })
  }

  try {
    const res = await fetch(url, options)
    const data = await res.json()
    if (!res.ok) {
      throw new Error(data.detail ?? `Server error: ${res.status}`)
    }
    selectedItem.value = data
    editRisk.value = data.risk_level
    editTier.value = data.customer_tier
    editSummary.value = data.summary
    actionSuccess.value = successMessage(action, data)
    await loadQueue()
  } catch (e) {
    actionError.value = e.message
  } finally {
    actionLoading.value = null
  }
}

function successMessage(action, item) {
  const messages = {
    claim: `Claimed — assigned to ${item.assigned_reviewer}`,
    approve: 'Approved — item closed',
    reject: 'Rejected — item closed',
    escalate: 'Escalated — item closed',
    unassign: 'Unassigned — returned to active queue',
    reopen: 'Reopened — moved back to In Review',
  }
  return messages[action] ?? 'Action complete'
}

// ---------------------------------------------------------------------------
// Edit details
// ---------------------------------------------------------------------------

async function saveEdits() {
  if (!canEditSelectedItem.value) return
  updateLoading.value = true
  updateError.value = null
  try {
    const res = await fetch(`${API_BASE}/api/items/${selectedId.value}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        risk_level: editRisk.value,
        customer_tier: editTier.value,
        summary: editSummary.value,
      }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail ?? `Server error: ${res.status}`)
    selectedItem.value = data
    editRisk.value = data.risk_level
    editTier.value = data.customer_tier
    editSummary.value = data.summary
    const idx = allItems.value.findIndex(i => i.id === data.id)
    if (idx !== -1) allItems.value[idx] = data
  } catch (e) {
    updateError.value = e.message
  } finally {
    updateLoading.value = false
  }
}

// ---------------------------------------------------------------------------
// Notes
// ---------------------------------------------------------------------------

async function submitNote() {
  if (!canEditSelectedItem.value) return
  noteLoading.value = true
  noteError.value = null
  try {
    const res = await fetch(`${API_BASE}/api/items/${selectedId.value}/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ author: REVIEWER, content: newNoteContent.value.trim() }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail ?? `Server error: ${res.status}`)
    selectedItem.value = data
    newNoteContent.value = ''
    const idx = allItems.value.findIndex(i => i.id === data.id)
    if (idx !== -1) allItems.value[idx] = { ...allItems.value[idx], notes_count: data.notes_count }
  } catch (e) {
    noteError.value = e.message
  } finally {
    noteLoading.value = false
  }
}

// ---------------------------------------------------------------------------
// New ticket modal
// ---------------------------------------------------------------------------

function openNewTicketModal() {
  newTicket.value = { title: '', risk_level: 'medium', customer_tier: 'standard', summary: '' }
  newTicketError.value = null
  showNewTicketModal.value = true
}

function closeNewTicketModal() {
  showNewTicketModal.value = false
}

async function submitNewTicket() {
  newTicketLoading.value = true
  newTicketError.value = null
  try {
    const res = await fetch(`${API_BASE}/api/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newTicket.value),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail ?? `Server error: ${res.status}`)
    closeNewTicketModal()
    await loadQueue()
    activeTab.value = 'active'
    await selectItem(data.id)
  } catch (e) {
    newTicketError.value = e.message
  } finally {
    newTicketLoading.value = false
  }
}

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

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

function formatDateFull(iso) {
  return new Date(iso).toLocaleString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
    timeZone: 'UTC', timeZoneName: 'short',
  })
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

onMounted(loadQueue)
</script>

<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --font: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --mono: 'SF Mono', 'Fira Code', monospace;

  --bg: #f3f4f6;
  --surface: #ffffff;
  --border: #e5e7eb;
  --text: #111827;
  --text-muted: #6b7280;

  --risk-high: #dc2626;
  --risk-med: #d97706;
  --risk-low: #16a34a;
  --tier-priority: #7c3aed;
  --tier-standard: #6b7280;

  --status-unassigned-bg: #f3f4f6;
  --status-unassigned-fg: #374151;
  --status-in_review-bg: #dbeafe;
  --status-in_review-fg: #1d4ed8;
  --status-approved-bg: #dcfce7;
  --status-approved-fg: #15803d;
  --status-rejected-bg: #fee2e2;
  --status-rejected-fg: #b91c1c;
  --status-escalated-bg: #ffedd5;
  --status-escalated-fg: #c2410c;

  --header-h: 52px;
}

html, body, #app { height: 100%; }

body { font-family: var(--font); background: var(--bg); color: var(--text); }

/* ── Header ───────────────────────────────────────────────────────────── */
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

.btn-sm { padding: 5px 12px; font-size: .8rem; }

/* ── Workspace split ──────────────────────────────────────────────────── */
.workspace { display: flex; flex: 1; overflow: hidden; }

/* ── Queue panel ──────────────────────────────────────────────────────── */
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

/* ── Detail panel ─────────────────────────────────────────────────────── */
.detail-panel { flex: 1; overflow-y: auto; padding: 28px 32px; }

.empty-detail {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: .95rem;
}

.detail-content { max-width: 680px; }

.detail-header { margin-bottom: 20px; }

.detail-id-row { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }

.detail-id { font-family: var(--mono); font-size: .82rem; color: var(--text-muted); }

.detail-title { font-size: 1.4rem; font-weight: 700; line-height: 1.3; }

.title-edit-row { display: flex; align-items: center; gap: 8px; }

.pencil-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  opacity: 0.4;
  padding: 2px 4px;
  border-radius: 4px;
  transition: opacity .15s;
  flex-shrink: 0;
}
.pencil-btn:hover { opacity: 1; }

.title-input {
  font-size: 1.25rem;
  font-weight: 700;
  padding: 4px 8px;
  border: 2px solid #2563eb;
  border-radius: 6px;
  flex: 1;
  font-family: var(--font);
  color: var(--text);
}

/* ── Metadata grid ────────────────────────────────────────────────────── */
.detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 24px;
  padding: 16px;
  background: #f9fafb;
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 24px;
}

.meta-item { display: flex; flex-direction: column; gap: 4px; }
.meta-label { font-size: .72rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: .04em; }
.meta-value { font-size: .88rem; }

/* ── Sections ─────────────────────────────────────────────────────────── */
.detail-section { margin-bottom: 24px; }
.section-title { font-size: .82rem; font-weight: 600; text-transform: uppercase; letter-spacing: .05em; color: var(--text-muted); margin-bottom: 10px; }

.summary-text { font-size: .95rem; line-height: 1.6; color: #1f2937; }

/* ── Actions ──────────────────────────────────────────────────────────── */
.actions-section { padding: 16px; background: #f9fafb; border: 1px solid var(--border); border-radius: 8px; }

.terminal-notice {
  font-size: .9rem;
  color: var(--text-muted);
  padding: 8px 0;
}

.action-buttons { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

.action-hint { font-size: .8rem; color: var(--text-muted); margin-left: 4px; }

.btn {
  padding: 8px 18px;
  font-size: .9rem;
  font-weight: 600;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: opacity .15s, filter .15s;
}
.btn:disabled { opacity: .55; cursor: not-allowed; }
.btn:not(:disabled):hover { filter: brightness(.92); }

.btn-primary { background: #2563eb; color: #fff; }
.btn-success { background: #16a34a; color: #fff; }
.btn-danger  { background: #dc2626; color: #fff; }
.btn-warn    { background: #d97706; color: #fff; }
.btn-secondary { background: #e5e7eb; color: #374151; }

.action-feedback { margin-top: 12px; font-size: .88rem; padding: 8px 12px; border-radius: 6px; }
.success-feedback { background: #dcfce7; color: #15803d; }
.error-feedback   { background: #fee2e2; color: #b91c1c; }

/* ── Edit form ────────────────────────────────────────────────────────── */
.edit-form { display: flex; flex-direction: column; gap: 12px; }
.edit-row { display: flex; align-items: center; gap: 12px; }
.edit-row-col { flex-direction: column; align-items: flex-start; gap: 4px; }
.edit-label { font-size: .75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: .04em; min-width: 100px; }
.edit-select, .edit-input {
  font-size: .88rem;
  padding: 6px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text);
  width: 160px;
}
.edit-input { width: 100%; }
.edit-textarea {
  width: 100%;
  font-size: .88rem;
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text);
  resize: vertical;
  font-family: var(--font);
  line-height: 1.5;
}
.edit-actions { display: flex; align-items: center; gap: 10px; }

/* ── Notes ────────────────────────────────────────────────────────────── */
.notes-list { display: flex; flex-direction: column; gap: 10px; margin-bottom: 14px; }
.note-item { background: #f9fafb; border: 1px solid var(--border); border-radius: 6px; padding: 10px 12px; }
.note-header { display: flex; justify-content: space-between; margin-bottom: 4px; }
.note-author { font-size: .78rem; font-weight: 700; color: #1d4ed8; }
.note-date { font-size: .74rem; color: var(--text-muted); }
.note-content { font-size: .88rem; line-height: 1.5; color: var(--text); white-space: pre-wrap; }
.notes-empty { font-size: .88rem; color: var(--text-muted); margin-bottom: 14px; }
.add-note-form { display: flex; flex-direction: column; gap: 8px; }

/* ── Modal ────────────────────────────────────────────────────────────── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.modal {
  background: var(--surface);
  border-radius: 10px;
  padding: 28px 32px;
  width: 520px;
  max-width: calc(100vw - 40px);
  box-shadow: 0 8px 32px rgba(0,0,0,.18);
}
.modal-title { font-size: 1.1rem; font-weight: 700; margin-bottom: 20px; }
.modal-actions { display: flex; gap: 10px; margin-top: 20px; }

/* ── Badges ───────────────────────────────────────────────────────────── */
.badge {
  font-size: .7rem;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 4px;
  white-space: nowrap;
  letter-spacing: .03em;
}

.badge-lg { font-size: .8rem; padding: 3px 10px; }

.risk-high     { background: #fee2e2; color: var(--risk-high); }
.risk-medium   { background: #fef3c7; color: var(--risk-med); }
.risk-low      { background: #dcfce7; color: var(--risk-low); }

.tier-priority { background: #ede9fe; color: var(--tier-priority); }
.tier-standard { background: #f3f4f6; color: var(--tier-standard); }

.status-unassigned { background: var(--status-unassigned-bg); color: var(--status-unassigned-fg); }
.status-in_review  { background: var(--status-in_review-bg);  color: var(--status-in_review-fg); }
.status-approved   { background: var(--status-approved-bg);   color: var(--status-approved-fg); }
.status-rejected   { background: var(--status-rejected-bg);   color: var(--status-rejected-fg); }
.status-escalated  { background: var(--status-escalated-bg);  color: var(--status-escalated-fg); }

/* ── Shared state messages ────────────────────────────────────────────── */
.state-msg {
  padding: 24px;
  font-size: .9rem;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 8px;
}
.loading-msg { color: #374151; }
.error-msg   { color: #b91c1c; }
.empty-msg   { justify-content: center; }

/* ── Spinner ──────────────────────────────────────────────────────────── */
.spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid #d1d5db;
  border-top-color: #6b7280;
  border-radius: 50%;
  animation: spin .7s linear infinite;
  flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
