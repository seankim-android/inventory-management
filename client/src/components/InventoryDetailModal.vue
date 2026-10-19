<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen && inventoryItem" class="modal-overlay" @click="close">
        <div class="modal-container" @click.stop>
          <div class="modal-header">
            <h3 class="modal-title">Inventory Item Details</h3>
            <button class="close-button" type="button" :aria-label="t('common.close')" @click="close">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
              </svg>
            </button>
          </div>

          <div class="modal-body">
            <div class="item-header">
              <div class="item-icon" :class="getStockIconClass()">
                <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                  <rect x="8" y="12" width="32" height="28" rx="2" stroke="currentColor" stroke-width="2.5"/>
                  <path d="M16 8V16M32 8V16M8 20H40" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
                  <path d="M16 28H32M16 34H24" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
                </svg>
              </div>
              <div class="item-title-section">
                <h4 class="item-name">{{ translateProductName(inventoryItem.name) }}</h4>
                <div class="item-sku">SKU: {{ inventoryItem.sku }}</div>
              </div>
              <span class="badge" :class="getStockStatusClass()">
                {{ getStockStatus() }}
              </span>
            </div>

            <div class="stock-summary">
              <div class="summary-card primary">
                <div class="summary-label">Quantity on Hand</div>
                <div class="summary-value">{{ inventoryItem.quantity_on_hand }} units</div>
              </div>
              <div class="summary-card" :class="getSummaryCardClass()">
                <div class="summary-label">Stock Level</div>
                <div class="summary-value">{{ stockPercentage }}%</div>
                <div class="summary-subtitle">vs. reorder point</div>
              </div>
            </div>

            <div class="info-grid">
              <div class="info-item">
                <div class="info-label">Category</div>
                <div class="info-value">{{ inventoryItem.category }}</div>
              </div>

              <div class="info-item">
                <div class="info-label">Location</div>
                <div class="info-value">{{ inventoryItem.location }}</div>
              </div>

              <div class="info-item">
                <div class="info-label">Reorder Point</div>
                <div class="info-value">{{ inventoryItem.reorder_point }} units</div>
              </div>

              <div class="info-item">
                <div class="info-label">Units Remaining</div>
                <div class="info-value">
                  <span :style="{ color: inventoryItem.quantity_on_hand <= inventoryItem.reorder_point ? 'var(--color-danger)' : 'var(--color-success)' }">
                    {{ inventoryItem.quantity_on_hand - inventoryItem.reorder_point }} units
                  </span>
                </div>
              </div>

              <div class="info-item">
                <div class="info-label">Unit Cost</div>
                <div class="info-value">{{ money(inventoryItem.unit_cost, 2) }}</div>
              </div>

              <div class="info-item">
                <div class="info-label">Total Value</div>
                <div class="info-value total-value">
                  {{ money(totalValue, 2) }}
                </div>
              </div>

              <div class="info-item">
                <div class="info-label">Warehouse</div>
                <div class="info-value">{{ translateWarehouse(inventoryItem.location) }}</div>
              </div>

              <div class="info-item">
                <div class="info-label">Status</div>
                <div class="info-value">
                  <span :class="['badge', getStockStatusClass()]">
                    {{ getStockStatus() }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn btn-secondary" type="button" @click="close">Close</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

const { t, currentCurrency, translateProductName, translateWarehouse } = useI18n()
const money = (amount, decimals = 0) => formatCurrencyWithDecimals(amount, currentCurrency.value, decimals)

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  inventoryItem: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close'])

const totalValue = computed(() => {
  if (!props.inventoryItem) return 0
  return props.inventoryItem.quantity_on_hand * props.inventoryItem.unit_cost
})

const stockPercentage = computed(() => {
  if (!props.inventoryItem || props.inventoryItem.reorder_point === 0) return 0
  return Math.round((props.inventoryItem.quantity_on_hand / props.inventoryItem.reorder_point) * 100)
})

const close = () => {
  emit('close')
}

const getStockStatus = () => {
  if (!props.inventoryItem) return 'Unknown'
  if (props.inventoryItem.quantity_on_hand <= props.inventoryItem.reorder_point) {
    return 'Low Stock'
  } else if (props.inventoryItem.quantity_on_hand <= props.inventoryItem.reorder_point * 1.5) {
    return 'Adequate'
  } else {
    return 'In Stock'
  }
}

const getStockStatusClass = () => {
  const status = getStockStatus()
  if (status === 'Low Stock') return 'danger'
  if (status === 'Adequate') return 'warning'
  return 'success'
}

const getStockIconClass = () => {
  const status = getStockStatus()
  if (status === 'Low Stock') return 'danger-icon'
  if (status === 'Adequate') return 'warning-icon'
  return 'success-icon'
}

const getSummaryCardClass = () => {
  const status = getStockStatus()
  if (status === 'Low Stock') return 'danger-card'
  if (status === 'Adequate') return 'warning-card'
  return 'success-card'
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

.item-header {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding-bottom: var(--space-5);
  margin-bottom: var(--space-6);
  border-bottom: 1px solid var(--color-border);
}

.item-title-section {
  flex: 1;
  min-width: 0;
}

.item-name {
  font-size: var(--text-xl);
  font-weight: var(--weight-semibold);
  line-height: var(--leading-tight);
  color: var(--color-text);
  margin-bottom: var(--space-1);
}

.item-sku {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.item-icon.success-icon { background: var(--color-success-soft); color: var(--color-success); }
.item-icon.warning-icon { background: var(--color-warning-soft); color: var(--color-warning); }
.item-icon.danger-icon { background: var(--color-danger-soft); color: var(--color-danger); }
.item-icon {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: var(--radius-md);
}

.stock-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(200px, 100%), 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.summary-card {
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-muted);
}

.summary-label {
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  color: var(--color-text-muted);
  margin-bottom: var(--space-1);
}

.summary-value {
  font-size: var(--text-2xl);
  font-weight: var(--weight-bold);
  line-height: var(--leading-tight);
  color: var(--color-text);
}

.summary-card.primary { background: var(--color-primary-soft); }
.summary-card.primary .summary-value { color: var(--color-primary); }

.summary-card.success-card {
  background: var(--color-success-soft);
  border-color: transparent;
}

.summary-card.success-card .summary-value {
  color: var(--color-success-text);
}

.summary-card.warning-card {
  background: var(--color-warning-soft);
  border-color: transparent;
}

.summary-card.warning-card .summary-value {
  color: var(--color-warning-text);
}

.summary-card.danger-card {
  background: var(--color-danger-soft);
  border-color: transparent;
}

.summary-card.danger-card .summary-value {
  color: var(--color-danger-text);
}

.summary-subtitle {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  margin-top: var(--space-1);
}

.info-value.total-value {
  font-size: var(--text-lg);
  color: var(--color-primary);
  font-weight: var(--weight-bold);
}
</style>
