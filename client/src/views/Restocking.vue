<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'
import { parseDate } from '../utils/date'

const { t, currentCurrency, currentLocale } = useI18n()

const DEFAULT_BUDGET = 2000
const SLIDER_STEP = 50
const MAX_BUDGET_PROBE = 1000000
const DEBOUNCE_MS = 300

const budget = ref(DEFAULT_BUDGET)
const sliderMax = ref(5200)
const recommendation = ref(null)
const loading = ref(true)
const error = ref(null)
const pendingFetch = ref(false)
const submitting = ref(false)
const submitError = ref(null)
const submittedOrder = ref(null)

let debounceTimer = null
let requestId = 0

const items = computed(() => recommendation.value?.items ?? [])
const totalCost = computed(() => recommendation.value?.total_cost ?? 0)
const remaining = computed(() => recommendation.value?.remaining_budget ?? budget.value)
const maxLeadTime = computed(() => items.value.reduce((max, i) => Math.max(max, i.lead_time_days), 0))
const canSubmit = computed(() =>
  items.value.length > 0 && !loading.value && !pendingFetch.value && !submitting.value && !error.value
)

const money = (amount) => formatCurrencyWithDecimals(amount, currentCurrency.value, 2)

const formatDate = (value) => {
  const date = parseDate(value)
  if (isNaN(date.getTime())) return value
  return date.toLocaleDateString(currentLocale.value === 'ja' ? 'ja-JP' : 'en-US', {
    year: 'numeric', month: 'short', day: 'numeric'
  })
}

const loadRecommendations = async () => {
  const id = ++requestId
  loading.value = true
  error.value = null
  try {
    const data = await api.getRestockingRecommendations(budget.value)
    if (id !== requestId) return
    recommendation.value = data
  } catch (err) {
    if (id !== requestId) return
    error.value = t('restocking.error')
    console.error(err)
  } finally {
    if (id === requestId) {
      loading.value = false
      pendingFetch.value = false
    }
  }
}

const loadSliderMax = async () => {
  try {
    const data = await api.getRestockingRecommendations(MAX_BUDGET_PROBE)
    sliderMax.value = Math.max(SLIDER_STEP, Math.ceil(data.total_cost / 100) * 100)
    if (budget.value > sliderMax.value) budget.value = sliderMax.value
  } catch (err) {
    console.error(err)
  }
}

watch(budget, () => {
  submittedOrder.value = null
  submitError.value = null
  pendingFetch.value = true
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(loadRecommendations, DEBOUNCE_MS)
})

const placeOrder = async () => {
  if (!canSubmit.value) return
  submitting.value = true
  submitError.value = null
  submittedOrder.value = null
  try {
    const order = await api.createRestockingOrder({
      budget: budget.value,
      items: items.value.map(i => ({ sku: i.sku, quantity: i.quantity }))
    })
    submittedOrder.value = order
  } catch (err) {
    submitError.value = err.response?.data?.detail || t('restocking.submitError')
    console.error(err)
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  await loadSliderMax()
  await loadRecommendations()
})

onBeforeUnmount(() => clearTimeout(debounceTimer))
</script>

<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div class="card">
      <div class="budget-row">
        <label for="budget-slider" class="budget-label">{{ t('restocking.budget') }}</label>
        <span class="budget-value">{{ money(budget) }}</span>
      </div>
      <input
        id="budget-slider"
        v-model.number="budget"
        type="range"
        min="0"
        :max="sliderMax"
        :step="SLIDER_STEP"
        class="budget-slider"
      />
      <div class="slider-scale">
        <span>{{ money(0) }}</span>
        <span>{{ money(sliderMax) }}</span>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <h3 class="card-title">{{ t('restocking.recommended') }}</h3>
      </div>

      <div v-if="loading && !recommendation" class="loading">{{ t('common.loading') }}</div>
      <div v-else-if="error" class="error">{{ error }}</div>
      <template v-else>
        <div :class="{ refreshing: loading || pendingFetch }">
          <div v-if="items.length === 0" class="empty">{{ t('restocking.empty') }}</div>
          <div v-else class="table-container">
            <table>
              <thead>
                <tr>
                  <th>{{ t('restocking.table.sku') }}</th>
                  <th>{{ t('restocking.table.item') }}</th>
                  <th class="num">{{ t('restocking.table.quantity') }}</th>
                  <th class="num">{{ t('restocking.table.unitCost') }}</th>
                  <th class="num">{{ t('restocking.table.lineTotal') }}</th>
                  <th class="num">{{ t('restocking.table.leadTime') }}</th>
                  <th>{{ t('restocking.table.trend') }}</th>
                  <th>{{ t('restocking.table.reason') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in items" :key="item.sku">
                  <td><strong>{{ item.sku }}</strong></td>
                  <td>{{ item.name }}</td>
                  <td class="num">{{ item.quantity.toLocaleString() }}</td>
                  <td class="num">{{ money(item.unit_cost) }}</td>
                  <td class="num"><strong>{{ money(item.line_total) }}</strong></td>
                  <td class="num">{{ t('restocking.leadTimeDays', { days: item.lead_time_days }) }}</td>
                  <td>
                    <span :class="['badge', item.trend]">{{ t(`trends.${item.trend}`) }}</span>
                  </td>
                  <td class="reason">{{ item.reason }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="summary">
          <div class="summary-item">
            <span class="summary-label">{{ t('restocking.totalCost') }}</span>
            <span class="summary-value">{{ money(totalCost) }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">{{ t('restocking.remaining') }}</span>
            <span class="summary-value">{{ money(remaining) }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">{{ t('restocking.maxLeadTime') }}</span>
            <span class="summary-value">{{ t('restocking.leadTimeDays', { days: maxLeadTime }) }}</span>
          </div>
          <button type="button" class="place-order" :disabled="!canSubmit" @click="placeOrder">
            {{ submitting ? t('restocking.submitting') : t('restocking.placeOrder') }}
          </button>
        </div>

        <div v-if="submittedOrder" class="success" role="status">
          {{ t('restocking.success', { orderNumber: submittedOrder.order_number, date: formatDate(submittedOrder.expected_delivery) }) }}
        </div>
        <div v-if="submitError" class="error" role="alert">{{ submitError }}</div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.budget-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.75rem;
}

.budget-label {
  font-weight: 600;
  color: #475569;
  font-size: 0.875rem;
}

.budget-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
}

.budget-slider {
  width: 100%;
  accent-color: #0f172a;
}

.slider-scale {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #64748b;
  margin-top: 0.25rem;
}

.num {
  text-align: right;
}

.reason {
  color: #64748b;
  font-size: 0.813rem;
}

.refreshing {
  opacity: 0.6;
  transition: opacity 0.15s ease;
}

.empty {
  text-align: center;
  padding: 2rem;
  color: #64748b;
  font-size: 0.938rem;
}

.summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1.5rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.summary-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.summary-value {
  font-size: 1.125rem;
  font-weight: 700;
  color: #0f172a;
}

.place-order {
  margin-left: auto;
  padding: 0.625rem 1.5rem;
  background: #0f172a;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.place-order:hover:not(:disabled) {
  background: #1e293b;
}

.place-order:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.success {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
  padding: 1rem;
  border-radius: 8px;
  margin-top: 1rem;
  font-size: 0.938rem;
}
</style>
