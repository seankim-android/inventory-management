<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen && backlogItem" class="modal-overlay" @click="close">
        <div class="modal-container" @click.stop>
          <div class="modal-header">
            <h3 class="modal-title">
              {{ mode === 'create' ? t('purchaseOrder.createTitle') : t('purchaseOrder.viewTitle') }}
            </h3>
            <button class="close-button" @click="close">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
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
                  <div class="info-value"><span class="badge">{{ purchaseOrder.status }}</span></div>
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
            <button class="btn-secondary" type="button" @click="close">{{ t('common.close') }}</button>
            <button
              v-if="mode === 'create'"
              class="btn-primary"
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
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 1rem;
}

.modal-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.15);
  max-width: 640px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.close-button {
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  padding: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.close-button:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}

.item-summary {
  padding-bottom: 1.25rem;
  border-bottom: 1px solid #e2e8f0;
  margin-bottom: 1.5rem;
}

.item-name {
  font-size: 1.125rem;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 0.375rem;
}

.item-meta {
  display: flex;
  gap: 1rem;
  font-size: 0.875rem;
  color: #64748b;
}

.item-sku {
  font-family: 'Monaco', 'Courier New', monospace;
  color: #2563eb;
}

.po-form,
.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.25rem;
}

.full {
  grid-column: 1 / -1;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-field label,
.info-label {
  font-size: 0.813rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
}

.form-field input,
.form-field textarea {
  padding: 0.625rem 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.938rem;
  font-family: inherit;
  color: #0f172a;
  background: white;
}

.form-field input:focus,
.form-field textarea:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.form-field textarea {
  resize: vertical;
}

.total-value {
  padding: 0.625rem 0;
  font-size: 1.125rem;
  font-weight: 700;
  color: #0f172a;
}

.field-error {
  font-size: 0.813rem;
  color: #dc2626;
}

.error-banner {
  padding: 0.75rem 1rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  color: #991b1b;
  font-size: 0.875rem;
}

.state-message {
  padding: 2rem;
  text-align: center;
  color: #64748b;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.info-value {
  font-size: 0.938rem;
  color: #0f172a;
  font-weight: 500;
}

.info-value.mono {
  font-family: 'Monaco', 'Courier New', monospace;
  color: #2563eb;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  font-size: 0.813rem;
  font-weight: 600;
  background: #fef3c7;
  color: #92400e;
}

.modal-footer {
  padding: 1.5rem;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.btn-secondary,
.btn-primary {
  padding: 0.625rem 1.25rem;
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.btn-secondary {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  color: #334155;
}

.btn-secondary:hover {
  background: #e2e8f0;
  border-color: #cbd5e1;
}

.btn-primary {
  background: #0f172a;
  border: 1px solid #0f172a;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #1e293b;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Modal transition animations */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-container,
.modal-leave-active .modal-container {
  transition: transform 0.2s ease;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: scale(0.95);
}
</style>
