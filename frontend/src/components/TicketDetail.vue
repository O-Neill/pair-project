<template>
  <main class="detail-panel">
    <div v-if="!selectedId" class="empty-detail">
      <p>Select an item from the queue to inspect it.</p>
    </div>

    <div v-else-if="loading" class="state-msg loading-msg">
      <span class="spinner"></span> Loading…
    </div>

    <div v-else-if="error" class="state-msg error-msg">{{ error }}</div>

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
              v-if="canEdit"
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
        <div class="section-heading-row">
          <h3 class="section-title">Summary</h3>
          <button
            v-if="canEdit && !editingSummary"
            class="pencil-btn"
            title="Edit summary"
            @click="startSummaryEdit"
          >✏️</button>
        </div>
        <template v-if="editingSummary">
          <div class="edit-form summary-edit-form">
            <div class="edit-row edit-row-col">
              <textarea v-model="editSummary" class="edit-textarea" rows="4"></textarea>
            </div>
            <div class="edit-actions">
              <button
                class="btn btn-primary btn-sm"
                :disabled="!!updateLoading || !editDirty"
                @click="saveEdits"
              >
                {{ updateLoading ? 'Saving…' : 'Save Changes' }}
              </button>
              <button class="btn btn-secondary btn-sm" @click="cancelSummaryEdit">Cancel</button>
              <span v-if="!editDirty" class="action-hint">No changes</span>
            </div>
            <div v-if="updateError" class="action-feedback error-feedback">{{ updateError }}</div>
          </div>
        </template>
        <p v-else class="summary-text">{{ selectedItem.summary }}</p>
      </div>

      <!-- Actions -->
      <div class="detail-section actions-section">
        <h3 class="section-title">Actions</h3>

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

      <div v-if="canEdit" class="detail-section">
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

        <div v-if="canEdit" class="add-note-form">
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
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const API_BASE = 'http://localhost:8000'
const TERMINAL_STATES = new Set(['approved', 'rejected', 'escalated'])

const props = defineProps({
  selectedId: { type: String, default: null },
  selectedItem: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: String, default: null },
  reviewer: { type: String, required: true },
})

const emit = defineEmits(['item-updated', 'queue-refresh'])

// Title edit state
const editTitle = ref('')
const editingTitle = ref(false)
const titleSaving = ref(false)
const titleInputRef = ref(null)

// Edit form state
const editRisk = ref('')
const editTier = ref('')
const editSummary = ref('')
const updateLoading = ref(false)
const updateError = ref(null)
const editingSummary = ref(false)

// Action state
const actionLoading = ref(null)
const actionSuccess = ref(null)
const actionError = ref(null)

// Note state
const newNoteContent = ref('')
const noteLoading = ref(false)
const noteError = ref(null)

const canEdit = computed(() => {
  return props.selectedItem?.status === 'in_review' && props.selectedItem?.assigned_reviewer === props.reviewer
})

const editDirty = computed(() => {
  if (!props.selectedItem) return false
  return (
    editRisk.value !== props.selectedItem.risk_level ||
    editTier.value !== props.selectedItem.customer_tier ||
    editSummary.value !== props.selectedItem.summary
  )
})

// Sync edit fields when item changes (new selection or updated from parent)
watch(() => props.selectedItem, (item) => {
  if (item) {
    editTitle.value = item.title
    editRisk.value = item.risk_level
    editTier.value = item.customer_tier
    editSummary.value = item.summary
  }
}, { immediate: true })

// Reset transient UI state when selection changes
watch(() => props.selectedId, () => {
  actionSuccess.value = null
  actionError.value = null
  updateError.value = null
  noteError.value = null
  newNoteContent.value = ''
  editingTitle.value = false
  editingSummary.value = false
})

function isTerminal(status) {
  return TERMINAL_STATES.has(status)
}

function startTitleEdit() {
  if (!canEdit.value) return
  editTitle.value = props.selectedItem.title
  editingTitle.value = true
  setTimeout(() => titleInputRef.value?.focus(), 0)
}

function cancelTitleEdit() {
  editingTitle.value = false
}

function startSummaryEdit() {
  if (!canEdit.value) return
  editingSummary.value = true
}

function cancelSummaryEdit() {
  editingSummary.value = false
}

async function saveTitle() {
  if (!canEdit.value || !editTitle.value.trim()) return
  titleSaving.value = true
  updateError.value = null
  try {
    const res = await fetch(`${API_BASE}/api/items/${props.selectedId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: editTitle.value.trim() }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail ?? `Server error: ${res.status}`)
    editingTitle.value = false
    emit('item-updated', data)
  } catch (e) {
    updateError.value = e.message
  } finally {
    titleSaving.value = false
  }
}

async function performAction(action) {
  actionLoading.value = action
  actionSuccess.value = null
  actionError.value = null

  const url = `${API_BASE}/api/items/${props.selectedId}/${action}`
  const options = {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  }
  if (action === 'claim') {
    options.body = JSON.stringify({ reviewer: props.reviewer })
  }

  try {
    const res = await fetch(url, options)
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail ?? `Server error: ${res.status}`)
    actionSuccess.value = successMessage(action, data)
    emit('item-updated', data)
    emit('queue-refresh')
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

async function saveEdits() {
  if (!canEdit.value) return
  updateLoading.value = true
  updateError.value = null
  try {
    const res = await fetch(`${API_BASE}/api/items/${props.selectedId}`, {
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
    editingSummary.value = false
    emit('item-updated', data)
  } catch (e) {
    updateError.value = e.message
  } finally {
    updateLoading.value = false
  }
}

async function submitNote() {
  if (!canEdit.value) return
  noteLoading.value = true
  noteError.value = null
  try {
    const res = await fetch(`${API_BASE}/api/items/${props.selectedId}/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ author: props.reviewer, content: newNoteContent.value.trim() }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail ?? `Server error: ${res.status}`)
    newNoteContent.value = ''
    emit('item-updated', data)
  } catch (e) {
    noteError.value = e.message
  } finally {
    noteLoading.value = false
  }
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

function formatDateFull(iso) {
  return new Date(iso).toLocaleString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
    timeZone: 'UTC', timeZoneName: 'short',
  })
}
</script>

<style scoped>
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

.detail-section { margin-bottom: 24px; }
.section-title { font-size: .82rem; font-weight: 600; text-transform: uppercase; letter-spacing: .05em; color: var(--text-muted); margin-bottom: 10px; }
.section-heading-row { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }

.summary-text { font-size: .95rem; line-height: 1.6; color: #1f2937; }
.summary-edit-form { margin-top: 2px; }

.actions-section { padding: 16px; background: #f9fafb; border: 1px solid var(--border); border-radius: 8px; }

.action-buttons { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

.action-hint { font-size: .8rem; color: var(--text-muted); margin-left: 4px; }

.notes-list { display: flex; flex-direction: column; gap: 10px; margin-bottom: 14px; }
.note-item { background: #f9fafb; border: 1px solid var(--border); border-radius: 6px; padding: 10px 12px; }
.note-header { display: flex; justify-content: space-between; margin-bottom: 4px; }
.note-author { font-size: .78rem; font-weight: 700; color: #1d4ed8; }
.note-date { font-size: .74rem; color: var(--text-muted); }
.note-content { font-size: .88rem; line-height: 1.5; color: var(--text); white-space: pre-wrap; }
.notes-empty { font-size: .88rem; color: var(--text-muted); margin-bottom: 14px; }
.add-note-form { display: flex; flex-direction: column; gap: 8px; }
</style>
