<template>
  <div class="demand">
    <p class="page-subtitle">{{ t('demand.description') }}</p>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="demand-trend-cards">
        <div class="trend-card increasing-card">
          <div class="trend-header">
            <div class="trend-icon">↑</div>
            <div>
              <div class="trend-label">{{ t('demand.increasingDemand') }}</div>
              <div class="trend-count">{{ t('demand.itemsCount', { count: getForecastsByTrend('increasing').length }) }}</div>
            </div>
          </div>
          <div class="trend-items">
            <div v-for="item in getForecastsByTrend('increasing').slice(0, 5)" :key="item.id" class="trend-item">
              <span class="item-name">{{ item.item_name }}</span>
              <span class="item-change">{{ getChangePercent(item) }}%</span>
            </div>
            <div v-if="getForecastsByTrend('increasing').length > 5" class="more-items">
              +{{ getForecastsByTrend('increasing').length - 5 }} {{ t('demand.more') }}
            </div>
          </div>
        </div>

        <div class="trend-card stable-card">
          <div class="trend-header">
            <div class="trend-icon">→</div>
            <div>
              <div class="trend-label">{{ t('demand.stableDemand') }}</div>
              <div class="trend-count">{{ t('demand.itemsCount', { count: getForecastsByTrend('stable').length }) }}</div>
            </div>
          </div>
          <div class="trend-items">
            <div v-for="item in getForecastsByTrend('stable').slice(0, 5)" :key="item.id" class="trend-item">
              <span class="item-name">{{ item.item_name }}</span>
              <span class="item-change neutral">{{ getChangePercent(item) }}%</span>
            </div>
            <div v-if="getForecastsByTrend('stable').length > 5" class="more-items">
              +{{ getForecastsByTrend('stable').length - 5 }} {{ t('demand.more') }}
            </div>
          </div>
        </div>

        <div class="trend-card decreasing-card">
          <div class="trend-header">
            <div class="trend-icon">↓</div>
            <div>
              <div class="trend-label">{{ t('demand.decreasingDemand') }}</div>
              <div class="trend-count">{{ t('demand.itemsCount', { count: getForecastsByTrend('decreasing').length }) }}</div>
            </div>
          </div>
          <div class="trend-items">
            <div v-for="item in getForecastsByTrend('decreasing').slice(0, 5)" :key="item.id" class="trend-item">
              <span class="item-name">{{ item.item_name }}</span>
              <span class="item-change">{{ getChangePercent(item) }}%</span>
            </div>
            <div v-if="getForecastsByTrend('decreasing').length > 5" class="more-items">
              +{{ getForecastsByTrend('decreasing').length - 5 }} {{ t('demand.more') }}
            </div>
          </div>
        </div>
      </div>

      <div class="card table-card">
        <div class="card-header">
          <h3 class="card-title">{{ t('demand.demandForecasts') }} ({{ forecasts.length }})</h3>
        </div>
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>{{ t('demand.table.sku') }}</th>
                <th>{{ t('demand.table.itemName') }}</th>
                <th class="text-right">{{ t('demand.table.currentDemand') }}</th>
                <th class="text-right">{{ t('demand.table.forecastedDemand') }}</th>
                <th class="text-right">{{ t('demand.table.change') }}</th>
                <th>{{ t('demand.table.trend') }}</th>
                <th>{{ t('demand.table.period') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="forecast in forecasts" :key="forecast.id">
                <td><strong>{{ forecast.item_sku }}</strong></td>
                <td>{{ forecast.item_name }}</td>
                <td class="text-right">{{ forecast.current_demand }}</td>
                <td class="text-right"><strong>{{ forecast.forecasted_demand }}</strong></td>
                <td class="text-right">
                  <span class="change-value" :style="{ color: getChangeColor(forecast) }">
                    {{ getChangePercent(forecast) }}%
                  </span>
                </td>
                <td>
                  <span :class="['badge', forecast.trend]">
                    {{ t(`trends.${forecast.trend}`) }}
                  </span>
                </td>
                <td>{{ translatePeriod(forecast.period) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, watch, computed } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'

export default {
  name: 'Demand',
  setup() {
    const { t } = useI18n()
    const loading = ref(true)
    const error = ref(null)
    const allForecasts = ref([])
    const inventoryItems = ref([])

    // Use shared filters
    const { selectedLocation, selectedCategory, getCurrentFilters } = useFilters()

    // Filter forecasts based on inventory filters
    const forecasts = computed(() => {
      if (selectedLocation.value === 'all' && selectedCategory.value === 'all') {
        return allForecasts.value
      }

      // Get SKUs of items that match the filters
      const validSkus = new Set(inventoryItems.value.map(item => item.sku))
      return allForecasts.value.filter(f => validSkus.has(f.item_sku))
    })

    const loadForecasts = async () => {
      try {
        loading.value = true
        const filters = getCurrentFilters()

        const [forecastsData, inventoryData] = await Promise.all([
          api.getDemandForecasts(),
          api.getInventory({
            warehouse: filters.warehouse,
            category: filters.category
          })
        ])

        allForecasts.value = forecastsData
        inventoryItems.value = inventoryData
      } catch (err) {
        error.value = 'Failed to load demand forecasts: ' + err.message
      } finally {
        loading.value = false
      }
    }

    // Watch for filter changes and reload data
    watch([selectedLocation, selectedCategory], () => {
      loadForecasts()
    })

    const getForecastsByTrend = (trend) => {
      return forecasts.value.filter(f => f.trend === trend)
    }

    const getChangePercent = (forecast) => {
      const change = ((forecast.forecasted_demand - forecast.current_demand) / forecast.current_demand * 100).toFixed(1)
      return change > 0 ? `+${change}` : change
    }

    const getChangeColor = (forecast) => {
      const change = forecast.forecasted_demand - forecast.current_demand
      const changePercent = Math.abs((change / forecast.current_demand) * 100)

      // If change is within ±2%, consider it stable
      if (changePercent <= 2) {
        return 'var(--color-info)'
      }

      if (change > 0) return 'var(--color-success)' // Increasing
      if (change < 0) return 'var(--color-danger)' // Decreasing
      return 'var(--color-info)' // No change
    }

    const translatePeriod = (period) => {
      // Period values like "Next 3 months", "Q1 2025", "30 days", etc.
      const { currentLocale } = useI18n()
      if (currentLocale.value === 'ja') {
        return period
          .replace(/Next\s+/i, '次の')
          .replace(/\s+months/i, 'か月')
          .replace(/\s+month/i, 'か月')
          .replace(/\s+days/i, '日間')
          .replace(/\s+day/i, '日')
          .replace('Q1', '第1四半期')
          .replace('Q2', '第2四半期')
          .replace('Q3', '第3四半期')
          .replace('Q4', '第4四半期')
      }
      return period
    }

    onMounted(loadForecasts)

    return {
      t,
      loading,
      error,
      forecasts,
      getForecastsByTrend,
      getChangePercent,
      getChangeColor,
      translatePeriod
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

.change-value {
  font-weight: var(--weight-semibold);
}

.demand-trend-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-5);
  margin-bottom: var(--space-5);
}

.trend-card {
  min-width: 0;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-top: 3px solid var(--color-border-strong);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--space-5);
  transition: box-shadow var(--transition-base), border-color var(--transition-base);
}

.trend-card:hover {
  box-shadow: var(--shadow-md);
}

.increasing-card {
  border-top-color: var(--color-success);
}

.stable-card {
  border-top-color: var(--color-info);
}

.decreasing-card {
  border-top-color: var(--color-danger);
}

.trend-header {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.trend-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  font-size: var(--text-2xl);
  font-weight: var(--weight-bold);
  flex-shrink: 0;
}

.increasing-card .trend-icon {
  background: var(--color-success-soft);
  color: var(--color-success-text);
}

.stable-card .trend-icon {
  background: var(--color-info-soft);
  color: var(--color-info-text);
}

.decreasing-card .trend-icon {
  background: var(--color-danger-soft);
  color: var(--color-danger-text);
}

.trend-label {
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.trend-count {
  font-size: var(--text-2xl);
  font-weight: var(--weight-bold);
  line-height: var(--leading-tight);
  color: var(--color-text);
  margin-top: var(--space-1);
}

.trend-items {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.trend-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-2) var(--space-3);
  background: var(--color-surface-muted);
  border-radius: var(--radius-sm);
  transition: background var(--transition-fast);
}

.trend-item:hover {
  background: var(--color-surface-hover);
}

.item-name {
  font-size: var(--text-sm);
  color: var(--color-text);
  font-weight: var(--weight-medium);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: var(--space-4);
}

.item-change {
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  flex-shrink: 0;
}

.increasing-card .item-change {
  color: var(--color-success-text);
}

.stable-card .item-change {
  color: var(--color-info);
}

.decreasing-card .item-change {
  color: var(--color-danger-text);
}

.item-change.neutral {
  color: var(--color-text-muted);
}

.more-items {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  text-align: center;
  padding: var(--space-2);
}
</style>
