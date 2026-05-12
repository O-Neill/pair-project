<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <h2 class="modal-title">New Ticket</h2>
      <div class="edit-form">
        <div class="edit-row edit-row-col">
          <label class="edit-label">Title</label>
          <input v-model="form.title" class="edit-input" type="text" placeholder="Short description" />
        </div>
        <div class="edit-row">
          <label class="edit-label">Risk Level</label>
          <select v-model="form.risk_level" class="edit-select">
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
        <div class="edit-row">
          <label class="edit-label">Customer Tier</label>
          <select v-model="form.customer_tier" class="edit-select">
            <option value="priority">Priority</option>
            <option value="standard">Standard</option>
          </select>
        </div>
        <div class="edit-row edit-row-col">
          <label class="edit-label">Summary</label>
          <textarea v-model="form.summary" class="edit-textarea" rows="3" placeholder="Describe the case…"></textarea>
        </div>
      </div>
      <div class="modal-actions">
        <button
          class="btn btn-primary"
          :disabled="!!loading || !form.title.trim() || !form.summary.trim()"
          @click="submit"
        >
          {{ loading ? 'Creating…' : 'Create Ticket' }}
        </button>
        <button class="btn btn-secondary" @click="$emit('close')">Cancel</button>
      </div>
      <div v-if="error" class="action-feedback error-feedback">{{ error }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const API_BASE = 'http://localhost:8000'

const emit = defineEmits(['created', 'close'])

const form = ref({ title: '', risk_level: 'medium', customer_tier: 'standard', summary: '' })
const loading = ref(false)
const error = ref(null)

async function submit() {
  loading.value = true
  error.value = null
  try {
    const res = await fetch(`${API_BASE}/api/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form.value),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail ?? `Server error: ${res.status}`)
    emit('created', data)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
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
</style>
