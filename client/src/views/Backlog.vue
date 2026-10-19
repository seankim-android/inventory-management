<template>
  <div class="backlog">
    <p class="page-subtitle">Track and resolve inventory shortages</p>

    <div v-if="loading" class="loading">Loading backlog...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="stats-grid">
        <div class="stat-card danger">
          <div class="stat-label">High Priority</div>
          <div class="stat-value">{{ getBacklogByPriority('high').length }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">Medium Priority</div>
          <div class="stat-value">{{ getBacklogByPriority('medium').length }}</div>
        </div>
        <div class="stat-card info">
          <div class="stat-label">Low Priority</div>
          <div class="stat-value">{{ getBacklogByPriority('low').length }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Total Backlog Items</div>
          <div class="stat-value">{{ backlogItems.length }}</div>
        </div>
      </div>

      <div class="card table-card">
        <div class="card-header">
          <h3 class="card-title">Backlog Items ({{ backlogItems.length }})</h3>
        </div>
        <div v-if="backlogItems.length === 0" class="empty-state">
          <p>No backlog items - all orders can be fulfilled!</p>
        </div>
        <div v-else class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Order ID</th>
                <th>SKU</th>
                <th>Item Name</th>
                <th class="text-right">Quantity Needed</th>
                <th class="text-right">Quantity Available</th>
                <th>Shortage</th>
                <th>Days Delayed</th>
                <th>Priority</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in backlogItems" :key="item.id">
                <td><strong>{{ item.order_id }}</strong></td>
                <td><strong>{{ item.item_sku }}</strong></td>
                <td>{{ item.item_name }}</td>
                <td class="text-right">{{ item.quantity_needed }}</td>
                <td class="text-right">{{ item.quantity_available }}</td>
                <td>
                  <span class="badge badge-danger">
                    {{ item.quantity_needed - item.quantity_available }} units short
                  </span>
                </td>
                <td>
                  <span :class="['days-delayed', item.days_delayed > 7 ? 'is-late' : 'is-warn']">
                    {{ item.days_delayed }} days
                  </span>
                </td>
                <td>
                  <span :class="['badge', item.priority]">
                    {{ item.priority }}
                  </span>
                </td>
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

export default {
  name: 'Backlog',
  setup() {
    const loading = ref(true)
    const error = ref(null)
    const allBacklogItems = ref([])
    const inventoryItems = ref([])

    // Use shared filters
    const { selectedLocation, selectedCategory, getCurrentFilters } = useFilters()

    // Filter backlog based on inventory filters
    const backlogItems = computed(() => {
      if (selectedLocation.value === 'all' && selectedCategory.value === 'all') {
        return allBacklogItems.value
      }

      // Get SKUs of items that match the filters
      const validSkus = new Set(inventoryItems.value.map(item => item.sku))
      return allBacklogItems.value.filter(b => validSkus.has(b.item_sku))
    })

    const loadBacklog = async () => {
      try {
        loading.value = true
        const filters = getCurrentFilters()

        const [backlogData, inventoryData] = await Promise.all([
          api.getBacklog(),
          api.getInventory({
            warehouse: filters.warehouse,
            category: filters.category
          })
        ])

        allBacklogItems.value = backlogData
        inventoryItems.value = inventoryData
      } catch (err) {
        error.value = 'Failed to load backlog: ' + err.message
      } finally {
        loading.value = false
      }
    }

    const getBacklogByPriority = (priority) => {
      return backlogItems.value.filter(item => item.priority === priority)
    }

    // Watch for filter changes and reload data
    watch([selectedLocation, selectedCategory], () => {
      loadBacklog()
    })

    onMounted(loadBacklog)

    return {
      loading,
      error,
      backlogItems,
      getBacklogByPriority
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

.table-card .card-header {
  margin-bottom: 0;
  padding: var(--space-4) var(--space-5);
}

.days-delayed {
  font-weight: var(--weight-semibold);
}

.days-delayed.is-late {
  color: var(--color-danger);
}

.days-delayed.is-warn {
  color: var(--color-warning);
}

.empty-state {
  padding: var(--space-12) var(--space-5);
  text-align: center;
  color: var(--color-success-text);
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
}
</style>
