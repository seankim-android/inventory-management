<template>
  <div class="orders">
    <p class="page-subtitle">{{ t('orders.description') }}</p>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="stats-grid">
        <div class="stat-card success">
          <div class="stat-label">{{ t('status.delivered') }}</div>
          <div class="stat-value">{{ getOrdersByStatus('Delivered').length }}</div>
        </div>
        <div class="stat-card info">
          <div class="stat-label">{{ t('status.shipped') }}</div>
          <div class="stat-value">{{ getOrdersByStatus('Shipped').length }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('status.processing') }}</div>
          <div class="stat-value">{{ getOrdersByStatus('Processing').length }}</div>
        </div>
        <div class="stat-card danger">
          <div class="stat-label">{{ t('status.backordered') }}</div>
          <div class="stat-value">{{ getOrdersByStatus('Backordered').length }}</div>
        </div>
      </div>

      <div class="card table-card">
        <div class="card-header">
          <h3 class="card-title">{{ t('orders.allOrders') }} ({{ orders.length }})</h3>
        </div>
        <div class="table-container">
          <table class="data-table orders-table">
            <thead>
              <tr>
                <th class="col-order-number">{{ t('orders.table.orderNumber') }}</th>
                <th class="col-customer">{{ t('orders.table.customer') }}</th>
                <th class="col-items">{{ t('orders.table.items') }}</th>
                <th class="col-status">{{ t('orders.table.status') }}</th>
                <th class="col-date">{{ t('orders.table.orderDate') }}</th>
                <th class="col-date">{{ t('orders.table.expectedDelivery') }}</th>
                <th class="col-value text-right">{{ t('orders.table.totalValue') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="order in orders" :key="order.id">
                <td class="col-order-number"><strong>{{ order.order_number }}</strong></td>
                <td class="col-customer">{{ translateCustomerName(order.customer) }}</td>
                <td class="col-items">
                  <details class="items-details">
                    <summary class="items-summary">
                      {{ t('orders.itemsCount', { count: order.items.length }) }}
                    </summary>
                    <div class="items-dropdown">
                      <div v-for="item in order.items" :key="`${item.sku}-${item.unit_price}-${item.quantity}`" class="item-entry">
                        <span class="item-name">{{ translateProductName(item.name) }}</span>
                        <span class="item-meta">{{ t('orders.quantity') }}: {{ item.quantity }} @ {{ money(item.unit_price, 2) }}</span>
                      </div>
                    </div>
                  </details>
                </td>
                <td class="col-status">
                  <span :class="['badge', getOrderStatusClass(order.status)]">
                    {{ t(`status.${order.status.toLowerCase()}`) }}
                  </span>
                </td>
                <td class="col-date">{{ formatDate(order.order_date) }}</td>
                <td class="col-date">{{ formatDate(order.expected_delivery) }}</td>
                <td class="col-value text-right"><strong>{{ money(order.total_value) }}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div class="card table-card submitted-orders">
      <div class="card-header">
        <h3 class="card-title">{{ t('orders.submitted.title') }} ({{ submittedOrders.length }})</h3>
      </div>
      <div v-if="submittedLoading" class="loading">{{ t('common.loading') }}</div>
      <div v-else-if="submittedError" class="error">{{ submittedError }}</div>
      <div v-else-if="submittedOrders.length === 0" class="empty-state">{{ t('orders.submitted.empty') }}</div>
      <div v-else class="table-container">
        <table class="data-table submitted-table">
          <thead>
            <tr>
              <th>{{ t('orders.submitted.orderNumber') }}</th>
              <th>{{ t('orders.submitted.submittedDate') }}</th>
              <th>{{ t('orders.submitted.items') }}</th>
              <th class="num text-right">{{ t('orders.submitted.totalCost') }}</th>
              <th class="num text-right">{{ t('orders.submitted.leadTime') }}</th>
              <th>{{ t('orders.submitted.expectedDelivery') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="order in submittedOrders" :key="order.id">
              <td><strong>{{ order.order_number }}</strong></td>
              <td>{{ formatDate(order.submitted_date) }}</td>
              <td>
                <div v-for="item in order.items" :key="item.sku" class="submitted-item">
                  {{ item.name }} <span class="item-meta">({{ item.sku }}) x {{ item.quantity.toLocaleString() }}</span>
                </div>
              </td>
              <td class="num text-right"><strong>{{ money(order.total_cost, 2) }}</strong></td>
              <td class="num text-right">{{ t('orders.submitted.leadTimeDays', { days: order.lead_time_days }) }}</td>
              <td>{{ formatDate(order.expected_delivery) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, watch, computed } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'
import { parseDate } from '../utils/date'

export default {
  name: 'Orders',
  setup() {
    const { t, currentCurrency, translateProductName, translateCustomerName } = useI18n()
    const money = (amount, decimals = 0) => formatCurrencyWithDecimals(amount, currentCurrency.value, decimals)
    const loading = ref(true)
    const error = ref(null)
    const orders = ref([])

    // Use shared filters
    const {
      selectedPeriod,
      selectedLocation,
      selectedCategory,
      selectedStatus,
      getCurrentFilters
    } = useFilters()

    const loadOrders = async () => {
      try {
        loading.value = true
        const filters = getCurrentFilters()
        const fetchedOrders = await api.getOrders(filters)

        // Sort orders by order_date (earliest first)
        orders.value = fetchedOrders.sort((a, b) => {
          const dateA = new Date(a.order_date)
          const dateB = new Date(b.order_date)
          return dateA - dateB
        })
      } catch (err) {
        error.value = 'Failed to load orders: ' + err.message
      } finally {
        loading.value = false
      }
    }

    // Watch for filter changes and reload data
    watch([selectedPeriod, selectedLocation, selectedCategory, selectedStatus], () => {
      loadOrders()
    })

    const getOrdersByStatus = (status) => {
      return orders.value.filter(order => order.status === status)
    }

    const getOrderStatusClass = (status) => {
      const statusMap = {
        'Delivered': 'success',
        'Shipped': 'info',
        'Processing': 'warning',
        'Backordered': 'danger'
      }
      return statusMap[status] || 'info'
    }

    const submittedOrders = ref([])
    const submittedLoading = ref(true)
    const submittedError = ref(null)

    const loadSubmittedOrders = async () => {
      try {
        submittedLoading.value = true
        submittedError.value = null
        submittedOrders.value = await api.getRestockingOrders()
      } catch (err) {
        submittedError.value = t('orders.submitted.error')
        console.error(err)
      } finally {
        submittedLoading.value = false
      }
    }

    const formatDate = (dateString) => {
      const { currentLocale } = useI18n()
      const locale = currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'
      const date = parseDate(dateString)
      if (isNaN(date.getTime())) return dateString
      return date.toLocaleDateString(locale, {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }

    onMounted(() => {
      loadOrders()
      loadSubmittedOrders()
    })

    return {
      submittedOrders,
      submittedLoading,
      submittedError,
      t,
      loading,
      error,
      orders,
      getOrdersByStatus,
      getOrderStatusClass,
      formatDate,
      money,
      translateProductName,
      translateCustomerName
    }
  }
}
</script>

<style scoped>
.page-subtitle {
  margin-bottom: var(--space-5);
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.table-card {
  padding: 0;
}

.table-card .loading,
.table-card .error,
.table-card .empty-state {
  padding: var(--space-8) var(--space-5);
}

.table-card .card-header {
  margin-bottom: 0;
  padding: var(--space-4) var(--space-5);
}

/* Fixed table layout to prevent column shifting */
.orders-table {
  table-layout: fixed;
  width: 100%;
}

.orders-table td {
  vertical-align: top;
}

/* Column widths */
.col-order-number {
  width: 160px;
  white-space: nowrap;
}

.col-customer {
  width: 180px;
}

.col-items {
  width: 200px;
}

.col-status {
  width: 130px;
}

.col-date {
  width: 140px;
}

.col-value {
  width: 120px;
}

/* Items details styling */
.items-details {
  min-width: 0;
}

.items-summary {
  cursor: pointer;
  color: var(--color-primary);
  font-weight: var(--weight-medium);
  list-style: none;
  user-select: none;
  display: inline-block;
}

.items-summary::-webkit-details-marker {
  display: none;
}

.items-summary::before {
  content: '';
  display: inline-block;
  margin-right: var(--space-2);
  border-style: solid;
  border-width: 4px 0 4px 6px;
  border-color: transparent transparent transparent currentColor;
  transition: transform var(--transition-base);
}

.items-details[open] .items-summary::before {
  transform: rotate(90deg);
}

.items-summary:hover {
  color: var(--color-primary-hover);
  text-decoration: underline;
}

/* Expands inline within the cell so the scrollable table container never clips it */
.items-dropdown {
  margin-top: var(--space-2);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  padding: var(--space-2);
  min-width: 0;
}

.item-entry {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-2);
  border-bottom: 1px solid var(--slate-100);
}

.item-entry:last-child {
  border-bottom: none;
}

.item-name {
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--color-text);
}

.item-meta {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.submitted-item {
  font-size: var(--text-sm);
  color: var(--color-text);
}

.empty-state {
  text-align: center;
  padding: var(--space-8);
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}
</style>
