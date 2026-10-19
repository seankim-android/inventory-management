<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen && backlogItem" class="modal-overlay" @click="close">
        <div class="modal-container" @click.stop>
          <div class="modal-header">
            <h3 class="modal-title">
              {{ mode === 'create' ? t('purchaseOrder.createTitle') : t('purchaseOrder.viewTitle') }}
            </h3>
            <button class="close-button" type="button" :aria-label="t('common.close')" @click="close">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
              </svg>
            </button>
          </div>

          <div class="modal-body">
            <div class="item-summary">
              <div class="item-name">{{ translateProductName(backlogItem.item_name) }}</div>
              <div class="item-meta">
                <span class="item-sku">{{ backlogItem.item_sku }}</span>
                <span>{{ t('purchaseOrder.shortage') }}: {{ shortage }}</span>
              </div>
            </div>

            <!-- Create mode -->
            <form v-if="mode === 'create'" id="po-form" class="po-form" novalidate @submit.prevent="submit">
              <div class="form-field full">
                <label for="po-supplier">{{ t('purchaseOrder.supplierName') }}</label>
                <input id="po-supplier" v-model="form.supplier_name" type="text" maxlength="100" />
                <div v-if="fieldErrors.supplier_name" class="field-error">{{ fieldErrors.supplier_name }}</div>
              </div>

              <div class="form-field">
                <label for="po-quantity">{{ t('purchaseOrder.quantity') }}</label>
                <input id="po-quantity" v-model="form.quantity" type="number" min="1" step="1" />
                <div v-if="fieldErrors.quantity" class="field-error">{{ fieldErrors.quantity }}</div>
              </div>

              <div class="form-field">
                <label for="po-unit-cost">{{ t('purchaseOrder.unitCost') }}</label>
                <input id="po-unit-cost" v-model="form.unit_cost" type="number" min="0" step="0.01" />
                <div v-if="fieldErrors.unit_cost" class="field-error">{{ fieldErrors.unit_cost }}</div>
              </div>

              <div class="form-field">
                <label for="po-date">{{ t('purchaseOrder.expectedDeliveryDate') }}</label>
                <input id="po-date" v-model="form.expected_delivery_date" type="date" />
                <div v-if="fieldErrors.expected_delivery_date" class="field-error">{{ fieldErrors.expected_delivery_date }}</div>
              </div>

              <div class="form-field">
                <label>{{ t('purchaseOrder.totalCost') }}</label>
                <div class="total-value">{{ formattedTotal }}</div>
              </div>

              <div class="form-field full">
                <label for="po-notes">{{ t('purchaseOrder.notes') }}</label>
                <textarea id="po-notes" v-model="form.notes" rows="3" :placeholder="t('purchaseOrder.notesPlaceholder')"></textarea>
              </div>

              <div v-if="submitError" class="error-banner full">{{ submitError }}</div>
            </form>

            <!-- View mode -->
            <template v-else>
              <div v-if="loading" class="state-message">{{ t('purchaseOrder.loadingPO') }}</div>
              <div v-else-if="loadError" class="error-banner">{{ loadError }}</div>
              <div v-else-if="purchaseOrder" class="info-grid">
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.poNumber') }}</div>
                  <div class="info-value mono">{{ purchaseOrder.id }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.status') }}</div>
                  <div class="info-value"><span class="badge badge-warning">{{ purchaseOrder.status }}</span></div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.supplierName') }}</div>
                  <div class="info-value">{{ purchaseOrder.supplier_name }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.quantity') }}</div>
                  <div class="info-value">{{ purchaseOrder.quantity }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.unitCost') }}</div>
                  <div class="info-value">{{ money(purchaseOrder.unit_cost, 2) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.totalCost') }}</div>
                  <div class="info-value">{{ money(purchaseOrder.quantity * purchaseOrder.unit_cost, 2) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.expectedDeliveryDate') }}</div>
                  <div class="info-value">{{ formatDate(purchaseOrder.expected_delivery_date) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.createdDate') }}</div>
                  <div class="info-value">{{ formatDate(purchaseOrder.created_date) }}</div>
                </div>
                <div v-if="purchaseOrder.notes" class="info-item full">
                  <div class="info-label">{{ t('purchaseOrder.notes') }}</div>
                  <div class="info-value">{{ purchaseOrder.notes }}</div>
                </div>
              </div>
            </template>
          </div>

          <div class="modal-footer">
            <button class="btn btn-secondary" type="button" @click="close">{{ t('common.close') }}</button>
            <button
              v-if="mode === 'create'"
              class="btn btn-primary"
              type="submit"
              form="po-form"
              :disabled="submitting"
            >
              {{ submitting ? t('purchaseOrder.submitting') : t('purchaseOrder.submit') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'
import { parseDate } from '../utils/date'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  backlogItem: {
    type: Object,
    default: null
  },
  mode: {
    type: String,
    default: 'create',
    validator: (value) => ['create', 'view'].includes(value)
  }
})

const emit = defineEmits(['close', 'po-created'])

const { t, currentCurrency, translateProductName } = useI18n()

const form = reactive({
  supplier_name: '',
  quantity: '',
  unit_cost: '',
  expected_delivery_date: '',
  notes: ''
})
const fieldErrors = reactive({})
const submitError = ref(null)
const submitting = ref(false)

const purchaseOrder = ref(null)
const loading = ref(false)
const loadError = ref(null)

const money = (amount, decimals = 0) =>
  formatCurrencyWithDecimals(amount, currentCurrency.value, decimals)

const shortage = computed(() => {
  if (!props.backlogItem) return 0
  return Math.max(props.backlogItem.quantity_needed - props.backlogItem.quantity_available, 0)
})

const formattedTotal = computed(() => {
  const quantity = Number(form.quantity)
  const unitCost = Number(form.unit_cost)
  if (!(quantity > 0) || !(unitCost > 0)) return money(0, 2)
  return money(quantity * unitCost, 2)
})

const toDateInputValue = (dateString) => {
  if (!dateString) return ''
  const date = parseDate(dateString)
  if (isNaN(date.getTime())) return ''
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  const date = parseDate(dateString)
  if (isNaN(date.getTime())) return dateString
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
}

const errorMessage = (err, fallback) => {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map(d => d.msg || String(d)).join(' ')
  }
  return fallback
}

const resetForm = () => {
  form.supplier_name = ''
  form.quantity = shortage.value > 0 ? String(shortage.value) : ''
  form.unit_cost = ''
  const expected = toDateInputValue(props.backlogItem?.expected_date)
  form.expected_delivery_date = expected && expected >= toDateInputValue(new Date()) ? expected : ''
  form.notes = ''
  Object.keys(fieldErrors).forEach(key => delete fieldErrors[key])
  submitError.value = null
  submitting.value = false
}

const loadPurchaseOrder = async () => {
  purchaseOrder.value = null
  loadError.value = null
  loading.value = true
  const requestedId = props.backlogItem.id
  try {
    const result = await api.getPurchaseOrderByBacklogItem(requestedId)
    if (props.backlogItem?.id !== requestedId) return
    purchaseOrder.value = result
  } catch (err) {
    if (props.backlogItem?.id !== requestedId) return
    loadError.value = err?.response?.status === 404
      ? t('purchaseOrder.notFound')
      : errorMessage(err, t('purchaseOrder.loadFailed'))
    console.error(err)
  } finally {
    if (props.backlogItem?.id === requestedId) loading.value = false
  }
}

watch(
  () => [props.isOpen, props.backlogItem?.id, props.mode],
  ([isOpen]) => {
    if (!isOpen || !props.backlogItem) return
    if (props.mode === 'create') resetForm()
    else loadPurchaseOrder()
  },
  { immediate: true }
)

const validate = () => {
  Object.keys(fieldErrors).forEach(key => delete fieldErrors[key])

  if (!form.supplier_name.trim()) {
    fieldErrors.supplier_name = t('purchaseOrder.errors.supplierRequired')
  }

  const quantity = Number(form.quantity)
  if (form.quantity === '' || !Number.isInteger(quantity) || quantity <= 0) {
    fieldErrors.quantity = t('purchaseOrder.errors.quantityInvalid')
  }

  const unitCost = Number(form.unit_cost)
  if (form.unit_cost === '' || !(unitCost > 0)) {
    fieldErrors.unit_cost = t('purchaseOrder.errors.unitCostInvalid')
  }

  if (!form.expected_delivery_date) {
    fieldErrors.expected_delivery_date = t('purchaseOrder.errors.dateRequired')
  } else if (isNaN(new Date(form.expected_delivery_date).getTime())) {
    fieldErrors.expected_delivery_date = t('purchaseOrder.errors.dateInvalid')
  }

  return Object.keys(fieldErrors).length === 0
}

const submit = async () => {
  if (submitting.value || !validate()) return

  submitError.value = null
  submitting.value = true
  const payload = {
    backlog_item_id: props.backlogItem.id,
    supplier_name: form.supplier_name.trim(),
    quantity: Number(form.quantity),
    unit_cost: Number(form.unit_cost),
    expected_delivery_date: form.expected_delivery_date
  }
  const notes = form.notes.trim()
  if (notes) payload.notes = notes

  try {
    const created = await api.createPurchaseOrder(payload)
    emit('po-created', created)
  } catch (err) {
    submitError.value = errorMessage(err, t('purchaseOrder.createFailed'))
    console.error(err)
  } finally {
    submitting.value = false
  }
}

const close = () => {
  emit('close')
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4);
  background: var(--color-backdrop);
  -webkit-backdrop-filter: blur(2px);
  backdrop-filter: blur(2px);
  z-index: 1000;
}

.modal-container {
  display: flex;
  flex-direction: column;
  width: min(640px, calc(100% - 32px));
  max-height: calc(100vh - 32px);
  overflow: hidden;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-6);
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.modal-title {
  font-size: var(--text-lg);
  font-weight: var(--weight-semibold);
  line-height: var(--leading-snug);
  letter-spacing: var(--tracking-tight);
  color: var(--color-text);
}

.close-button {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  padding: var(--space-2);
  background: none;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--color-text-muted);
  cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast);
}

.close-button:hover {
  background: var(--color-surface-hover);
  color: var(--color-text);
}

.close-button:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px var(--color-focus-ring);
}

.modal-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: var(--space-6);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-6);
  border-top: 1px solid var(--color-border);
  background: var(--color-surface-muted);
  flex-shrink: 0;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(200px, 100%), 1fr));
  gap: var(--space-5) var(--space-6);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.info-label {
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  color: var(--color-text-muted);
}

.info-value {
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--color-text);
  overflow-wrap: anywhere;
}

.mono,
.info-value.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity var(--transition-base);
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-container,
.modal-leave-active .modal-container {
  transition: transform var(--transition-base);
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: translateY(8px) scale(0.98);
}

.item-summary {
  padding-bottom: var(--space-4);
  margin-bottom: var(--space-5);
  border-bottom: 1px solid var(--color-border);
}

.item-name {
  font-size: var(--text-lg);
  font-weight: var(--weight-semibold);
  color: var(--color-text);
  margin-bottom: var(--space-1);
}

.item-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

.item-sku {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  color: var(--color-primary);
}

.po-form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(240px, 100%), 1fr));
  gap: var(--space-4) var(--space-5);
}

.full {
  grid-column: 1 / -1;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.form-field label {
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  color: var(--color-text-muted);
}

.form-field input,
.form-field textarea {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.form-field input::placeholder,
.form-field textarea::placeholder {
  color: var(--color-text-subtle);
}

.form-field input:focus,
.form-field textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-focus-ring);
}

.form-field textarea {
  resize: vertical;
}

.total-value {
  padding: var(--space-2) 0;
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
  color: var(--color-text);
}

.field-error {
  font-size: var(--text-xs);
  color: var(--color-danger);
}

.error-banner {
  padding: var(--space-3) var(--space-4);
  background: var(--color-danger-soft);
  border: 1px solid var(--color-danger);
  border-radius: var(--radius-md);
  color: var(--color-danger-text);
  font-size: var(--text-sm);
}

.state-message {
  padding: var(--space-8);
  text-align: center;
  color: var(--color-text-muted);
}

.info-item.full {
  grid-column: 1 / -1;
}

.info-value.mono {
  color: var(--color-primary);
}
</style>
