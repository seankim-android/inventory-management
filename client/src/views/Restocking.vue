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
            <table class="data-table zebra">
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
          <button type="button" class="btn btn-primary place-order" :disabled="!canSubmit" @click="placeOrder">
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
.page-header {
  margin-bottom: var(--space-5);
}

.budget-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

.budget-label {
  font-weight: var(--weight-semibold);
  color: var(--slate-600);
  font-size: var(--text-sm);
}

.budget-value {
  font-size: var(--text-2xl);
  font-weight: var(--weight-bold);
  color: var(--color-text);
  letter-spacing: var(--tracking-tight);
}

.budget-slider {
  width: 100%;
  accent-color: var(--color-primary);
  cursor: pointer;
}

.slider-scale {
  display: flex;
  justify-content: space-between;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  margin-top: var(--space-1);
}

.num {
  text-align: right;
}

.reason {
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  min-width: 200px;
}

.refreshing {
  opacity: 0.6;
  transition: opacity var(--transition-fast);
}

.empty {
  text-align: center;
  padding: var(--space-8);
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3) var(--space-6);
  margin-top: var(--space-4);
  padding: var(--space-4);
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.summary-label {
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.summary-value {
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
  color: var(--color-text);
}

.place-order {
  margin-left: auto;
  padding: var(--space-2) var(--space-5);
}

.success {
  background: var(--color-success-soft);
  border: 1px solid var(--color-success);
  color: var(--color-success-text);
  padding: var(--space-4);
  border-radius: var(--radius-md);
  margin-top: var(--space-4);
  font-size: var(--text-sm);
}

@media (max-width: 639px) {
  .place-order {
    margin-left: 0;
    width: 100%;
  }
}
</style>
