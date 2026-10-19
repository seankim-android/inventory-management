<template>
  <div class="app" :class="{ 'sidebar-collapsed': collapsed, 'drawer-open': drawerOpen }">
    <div class="sidebar-backdrop" aria-hidden="true" @click="closeDrawer"></div>

    <aside class="sidebar" id="app-sidebar" :aria-label="t('nav.companyName')">
      <div class="sidebar-brand">
        <div class="brand-mark" aria-hidden="true">{{ brandInitial }}</div>
        <div class="brand-text">
          <h1 class="brand-name">{{ t('nav.companyName') }}</h1>
          <span class="brand-subtitle">{{ t('nav.subtitle') }}</span>
        </div>
        <button
          ref="closeButtonRef"
          type="button"
          class="sidebar-close"
          :aria-label="t('nav.closeMenu')"
          @click="closeDrawer"
        >
          <NavIcon name="close" />
        </button>
      </div>

      <nav class="sidebar-nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-link"
          :active-class="item.exact ? 'router-link-active' : 'active'"
          exact-active-class="active"
          :title="collapsed ? t(item.label) : null"
        >
          <NavIcon :name="item.icon" />
          <span class="nav-label">{{ t(item.label) }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <LanguageSwitcher />
        <ProfileMenu
          @show-profile-details="showProfileDetails = true"
          @show-tasks="showTasks = true"
        />
        <button
          type="button"
          class="sidebar-toggle"
          :title="collapsed ? t('nav.expandSidebar') : t('nav.collapseSidebar')"
          :aria-label="collapsed ? t('nav.expandSidebar') : t('nav.collapseSidebar')"
          @click="toggleCollapsed"
        >
          <NavIcon name="panel-left" />
          <span class="nav-label">{{ t('nav.collapseSidebar') }}</span>
        </button>
      </div>
    </aside>

    <div class="app-main">
      <header class="app-header">
        <button
          type="button"
          ref="menuButtonRef"
          class="menu-button"
          aria-controls="app-sidebar"
          :aria-expanded="drawerOpen"
          :aria-label="t('nav.openMenu')"
          @click="drawerOpen = true"
        >
          <NavIcon name="menu" size="20" />
        </button>
        <h2 class="app-header-title">{{ pageTitle }}</h2>
      </header>

      <FilterBar />

      <main class="main-content">
        <router-view />
      </main>
    </div>

    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, onMounted, onBeforeUnmount, computed, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import FilterBar from './components/FilterBar.vue'
import ProfileMenu from './components/ProfileMenu.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'
import NavIcon from './components/NavIcon.vue'

export default {
  name: 'App',
  components: {
    FilterBar,
    ProfileMenu,
    ProfileDetailsModal,
    TasksModal,
    LanguageSwitcher,
    NavIcon
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const route = useRoute()

    const navItems = [
      { path: '/', label: 'nav.overview', icon: 'overview', exact: true },
      { path: '/inventory', label: 'nav.inventory', icon: 'inventory' },
      { path: '/orders', label: 'nav.orders', icon: 'orders' },
      { path: '/spending', label: 'nav.finance', icon: 'finance' },
      { path: '/demand', label: 'nav.demandForecast', icon: 'demand' },
      { path: '/restocking', label: 'nav.restocking', icon: 'restocking' },
      { path: '/reports', label: 'nav.reports', icon: 'reports' }
    ]

    const pageTitle = computed(() => {
      const match = navItems.find(item => item.path === route.path)
      return match ? t(match.label) : t('nav.companyName')
    })

    const brandInitial = computed(() => (t('nav.companyName') || '').trim().charAt(0))

    // Sidebar state (collapse persisted; drawer is mobile-only and transient)
    const STORAGE_KEY = 'sidebarCollapsed'
    const readCollapsed = () => {
      try {
        return localStorage.getItem(STORAGE_KEY) === 'true'
      } catch (err) {
        return false
      }
    }
    const collapsed = ref(readCollapsed())
    const drawerOpen = ref(false)

    const toggleCollapsed = () => {
      collapsed.value = !collapsed.value
      try {
        localStorage.setItem(STORAGE_KEY, String(collapsed.value))
      } catch (err) {
        // Storage unavailable; keep in-memory state only
      }
    }
    const closeDrawer = () => {
      drawerOpen.value = false
    }

    const menuButtonRef = ref(null)
    const closeButtonRef = ref(null)

    const onKeydown = (event) => {
      if (event.key === 'Escape' && drawerOpen.value) {
        closeDrawer()
        menuButtonRef.value?.focus()
      }
    }

    watch(() => route.fullPath, closeDrawer)
    watch(drawerOpen, async (open) => {
      if (open) {
        await nextTick()
        closeButtonRef.value?.focus()
      }
    })
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const apiTasks = ref([])

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    onMounted(() => {
      loadTasks()
      document.addEventListener('keydown', onKeydown)
    })
    onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))

    return {
      t,
      navItems,
      pageTitle,
      brandInitial,
      collapsed,
      drawerOpen,
      menuButtonRef,
      closeButtonRef,
      toggleCollapsed,
      closeDrawer,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask
    }
  }
}
</script>

<style>
/* ==========================================================================
   Design tokens
   ========================================================================== */
:root {
  /* Font */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;

  /* Slate neutrals */
  --slate-50: #f8fafc;
  --slate-100: #f1f5f9;
  --slate-200: #e2e8f0;
  --slate-300: #cbd5e1;
  --slate-400: #94a3b8;
  --slate-500: #64748b;
  --slate-600: #475569;
  --slate-700: #334155;
  --slate-800: #1e293b;
  --slate-900: #0f172a;

  /* Primary accent (indigo) */
  --primary-50: #eef2ff;
  --primary-100: #e0e7ff;
  --primary-200: #c7d2fe;
  --primary-500: #6366f1;
  --primary-600: #4f46e5;
  --primary-700: #4338ca;
  --color-primary: var(--primary-600);
  --color-primary-hover: var(--primary-700);
  --color-primary-soft: var(--primary-50);
  --color-primary-soft-border: var(--primary-200);
  --color-on-primary: #ffffff;

  /* Status colors: solid, soft background, and strong text */
  --color-success: #059669;
  --color-success-soft: #d1fae5;
  --color-success-text: #065f46;
  --color-info: #2563eb;
  --color-info-soft: #dbeafe;
  --color-info-text: #1e40af;
  --color-warning: #d97706;
  --color-warning-soft: #fef3c7;
  --color-warning-text: #92400e;
  --color-danger: #dc2626;
  --color-danger-soft: #fee2e2;
  --color-danger-text: #991b1b;
  --color-danger-border: #fecaca;

  /* Text */
  --color-text: var(--slate-900);
  --color-text-body: var(--slate-700);
  --color-text-muted: var(--slate-500);
  --color-text-subtle: var(--slate-400);

  /* Surfaces and borders */
  --color-bg: var(--slate-50);
  --color-surface: #ffffff;
  --color-surface-muted: var(--slate-50);
  --color-surface-hover: var(--slate-100);
  --color-border: var(--slate-200);
  --color-border-strong: var(--slate-300);
  --color-focus-ring: rgba(79, 70, 229, 0.25);
  --color-backdrop: rgba(15, 23, 42, 0.45);

  /* Sidebar (dark slate) */
  --sidebar-bg: var(--slate-900);
  --sidebar-text: #cbd5e1;
  --sidebar-text-strong: #ffffff;
  --sidebar-hover-bg: rgba(255, 255, 255, 0.06);
  --sidebar-hover-bg-strong: rgba(255, 255, 255, 0.12);
  --sidebar-active-bg: rgba(99, 102, 241, 0.2);
  --sidebar-active-text: #ffffff;
  --sidebar-border: rgba(255, 255, 255, 0.08);
  --sidebar-width: 240px;
  --sidebar-width-collapsed: 72px;
  --header-height: 56px;
  --content-max-width: 1440px;

  /* Spacing (4px base) */
  --space-0: 0;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --page-padding: var(--space-6);

  /* Radius */
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-full: 9999px;

  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgba(15, 23, 42, 0.05);
  --shadow-md: 0 4px 12px -2px rgba(15, 23, 42, 0.08), 0 2px 4px -2px rgba(15, 23, 42, 0.06);
  --shadow-lg: 0 10px 25px rgba(15, 23, 42, 0.12);

  /* Typography */
  --text-xs: 0.75rem;
  --text-sm: 0.875rem;
  --text-base: 1rem;
  --text-lg: 1.125rem;
  --text-xl: 1.25rem;
  --text-2xl: 1.5rem;
  --text-3xl: 1.875rem;
  --text-4xl: 2.25rem;
  --leading-tight: 1.25;
  --leading-snug: 1.4;
  --leading-normal: 1.5;
  --weight-regular: 400;
  --weight-medium: 500;
  --weight-semibold: 600;
  --weight-bold: 700;
  --tracking-tight: -0.025em;
  --tracking-wide: 0.05em;

  /* Motion */
  --transition-fast: 0.15s ease;
  --transition-base: 0.2s ease;

  /* Z-index */
  --z-sticky: 90;
  --z-header: 100;
  --z-sidebar: 200;
  --z-backdrop: 150;
}

/* ==========================================================================
   Base
   ========================================================================== */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: var(--font-sans);
  font-size: var(--text-base);
  line-height: var(--leading-normal);
  background: var(--color-bg);
  color: var(--slate-800);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

button,
input,
select,
textarea {
  font-family: inherit;
}

:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* ==========================================================================
   App shell
   ========================================================================== */
.app {
  min-height: 100vh;
}

.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: var(--sidebar-width);
  display: flex;
  flex-direction: column;
  background: var(--sidebar-bg);
  color: var(--sidebar-text);
  z-index: var(--z-sidebar);
  transition: width var(--transition-base), transform var(--transition-base);
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 64px;
  padding: 0 var(--space-4);
  border-bottom: 1px solid var(--sidebar-border);
  flex-shrink: 0;
}

.brand-mark {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: var(--color-primary);
  color: var(--color-on-primary);
  font-weight: var(--weight-bold);
  font-size: var(--text-base);
}

.brand-text {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.brand-name {
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--sidebar-text-strong);
  line-height: var(--leading-tight);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.brand-subtitle {
  font-size: var(--text-xs);
  color: var(--slate-400);
  line-height: var(--leading-snug);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-4) var(--space-3);
  overflow-y: auto;
}

.sidebar-close {
  display: none;
  margin-left: auto;
}

.nav-link,
.sidebar-toggle {
  display: flex;
}

.nav-link,
.sidebar-toggle,
.sidebar-close {
  align-items: center;
  gap: var(--space-3);
  padding: 10px var(--space-3);
  border: none;
  background: transparent;
  border-radius: var(--radius-md);
  color: var(--sidebar-text);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  text-decoration: none;
  cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast);
}

.nav-link:hover,
.sidebar-toggle:hover,
.sidebar-close:hover {
  background: var(--sidebar-hover-bg);
  color: var(--sidebar-text-strong);
}

.nav-link.active {
  background: var(--sidebar-active-bg);
  color: var(--sidebar-active-text);
}

.nav-link:focus-visible,
.sidebar-toggle:focus-visible,
.sidebar-close:focus-visible {
  outline-color: var(--primary-200);
  outline-offset: -2px;
}

.nav-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-footer {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  border-top: 1px solid var(--sidebar-border);
  flex-shrink: 0;
}

.app .sidebar .sidebar-footer .language-switcher,
.app .sidebar .sidebar-footer .profile-menu {
  width: 100%;
}

.app .sidebar .sidebar-footer .language-button,
.app .sidebar .sidebar-footer .profile-button {
  width: 100%;
  background: var(--sidebar-hover-bg);
  border-color: var(--sidebar-border);
  color: var(--sidebar-text);
}

.app .sidebar .sidebar-footer .language-button:hover,
.app .sidebar .sidebar-footer .profile-button:hover {
  background: var(--sidebar-hover-bg-strong);
  border-color: var(--sidebar-border);
}

.app .sidebar .sidebar-footer .profile-name,
.app .sidebar .sidebar-footer .language-label {
  color: var(--sidebar-text-strong);
  flex: 1;
  text-align: left;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.app .sidebar .sidebar-footer .chevron,
.app .sidebar .sidebar-footer .globe-icon {
  color: var(--slate-400);
}

/* Dropdowns open upward from the sidebar footer and stay inside the viewport */
.app .sidebar .sidebar-footer .dropdown-menu {
  top: auto;
  bottom: calc(100% + var(--space-2));
  left: 0;
  right: auto;
  max-width: calc(100vw - var(--space-6));
  max-height: calc(100vh - var(--space-6));
  overflow-y: auto;
}

.app-main {
  margin-left: var(--sidebar-width);
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  transition: margin-left var(--transition-base);
}

.app-header {
  position: sticky;
  top: 0;
  z-index: var(--z-header);
  height: var(--header-height);
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 0 var(--page-padding);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}

.app-header-title {
  font-size: var(--text-lg);
  font-weight: var(--weight-semibold);
  color: var(--color-text);
  letter-spacing: var(--tracking-tight);
}

.menu-button {
  display: none;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--slate-700);
  cursor: pointer;
}

.menu-button:hover {
  background: var(--color-surface-hover);
}

.sidebar-backdrop {
  display: none;
}

.main-content {
  flex: 1;
  width: 100%;
  max-width: var(--content-max-width);
  margin: 0 auto;
  padding: var(--page-padding);
}

/* Collapsed sidebar (desktop only) */
@media (min-width: 1024px) {
  .sidebar-collapsed .sidebar {
    width: var(--sidebar-width-collapsed);
  }

  .sidebar-collapsed .app-main {
    margin-left: var(--sidebar-width-collapsed);
  }

  .sidebar-collapsed .brand-text,
  .sidebar-collapsed .nav-label,
  .sidebar-collapsed .sidebar-footer .profile-name,
  .sidebar-collapsed .sidebar-footer .language-label,
  .sidebar-collapsed .sidebar-footer .chevron {
    display: none;
  }

  .sidebar-collapsed .sidebar-brand {
    justify-content: center;
    padding: 0;
  }

  .sidebar-collapsed .nav-link,
  .sidebar-collapsed .sidebar-toggle,
  .sidebar-collapsed .sidebar-footer .language-button,
  .sidebar-collapsed .sidebar-footer .profile-button {
    justify-content: center;
    padding-left: 0;
    padding-right: 0;
  }

  .sidebar-collapsed .sidebar-toggle svg {
    transform: scaleX(-1);
  }
}

/* Tablet and mobile: off-canvas drawer */
@media (max-width: 1023px) {
  :root {
    --page-padding: var(--space-4);
  }

  .sidebar {
    transform: translateX(-100%);
    visibility: hidden;
    transition: width var(--transition-base), transform var(--transition-base),
      visibility 0s linear 0.2s;
    width: min(var(--sidebar-width), 85vw);
    box-shadow: var(--shadow-lg);
  }

  .drawer-open .sidebar {
    transform: translateX(0);
    visibility: visible;
    transition: width var(--transition-base), transform var(--transition-base),
      visibility 0s;
  }

  .sidebar .sidebar-close {
    display: flex;
    padding: var(--space-2);
    width: auto;
  }

  .sidebar-toggle {
    display: none;
  }

  .app-main {
    margin-left: 0;
  }

  .menu-button {
    display: inline-flex;
  }

  .drawer-open .sidebar-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    background: var(--color-backdrop);
    z-index: var(--z-backdrop);
  }
}

/* ==========================================================================
   Page layout helpers
   ========================================================================== */
.page-header {
  margin-bottom: var(--space-6);
}

.page-header h2 {
  font-size: var(--text-3xl);
  font-weight: var(--weight-bold);
  color: var(--color-text);
  margin-bottom: 6px;
  letter-spacing: var(--tracking-tight);
}

.page-header p {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.page-grid {
  display: grid;
  gap: var(--space-5);
  margin-bottom: var(--space-5);
}

.page-grid-2 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.page-grid-3 {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.page-grid-4 {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.page-grid-auto {
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
}

@media (max-width: 1023px) {
  .page-grid-3,
  .page-grid-4 {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 639px) {
  .page-grid-2,
  .page-grid-3,
  .page-grid-4 {
    grid-template-columns: minmax(0, 1fr);
  }
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-5);
  margin-bottom: var(--space-6);
}

/* ==========================================================================
   Cards
   ========================================================================== */
.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--space-5);
  margin-bottom: var(--space-5);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border);
}

.card-title {
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  color: var(--color-text);
  letter-spacing: var(--tracking-tight);
}

.card-body {
  color: var(--color-text-body);
  font-size: var(--text-sm);
}

/* Inside a page-grid the grid gap handles spacing */
.page-grid > .card,
.page-grid > .stat-card {
  margin-bottom: 0;
}

/* ==========================================================================
   Stat cards: .stat-card > .stat-label + .stat-value + .stat-trend
   ========================================================================== */
.stat-card {
  background: var(--color-surface);
  padding: var(--space-5);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
  transition: border-color var(--transition-base), box-shadow var(--transition-base);
}

.stat-card:hover {
  border-color: var(--color-border-strong);
  box-shadow: var(--shadow-md);
}

.stat-label {
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  margin-bottom: var(--space-2);
}

.stat-value {
  font-size: var(--text-3xl);
  font-weight: var(--weight-bold);
  line-height: var(--leading-tight);
  color: var(--color-text);
  letter-spacing: var(--tracking-tight);
}

.stat-trend {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  margin-top: var(--space-2);
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  color: var(--color-text-muted);
}

.stat-trend.up,
.stat-trend.positive {
  color: var(--color-success);
}

.stat-trend.down,
.stat-trend.negative {
  color: var(--color-danger);
}

.stat-card.warning .stat-value {
  color: var(--color-warning);
}

.stat-card.success .stat-value {
  color: var(--color-success);
}

.stat-card.danger .stat-value {
  color: var(--color-danger);
}

.stat-card.info .stat-value {
  color: var(--color-info);
}

/* ==========================================================================
   Tables. Bare table/thead/th/td are styled for legacy views;
   add .data-table for sticky header, and .zebra for striped rows.
   ========================================================================== */
.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: var(--color-surface-muted);
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
}

th {
  text-align: left;
  padding: var(--space-2) var(--space-3);
  font-weight: var(--weight-semibold);
  color: var(--slate-600);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

td {
  padding: var(--space-2) var(--space-3);
  border-top: 1px solid var(--slate-100);
  color: var(--color-text-body);
  font-size: var(--text-sm);
}

tbody tr {
  transition: background-color var(--transition-fast);
}

tbody tr:hover {
  background: var(--color-surface-muted);
}

.data-table th,
.data-table td {
  padding: 10px var(--space-4);
}

.data-table thead {
  background: transparent;
  border: none;
}

.data-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--color-surface-muted);
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}

.data-table tbody tr:hover {
  background: var(--color-primary-soft);
}

.data-table.zebra tbody tr:nth-child(even) {
  background: var(--color-surface-muted);
}

.data-table.zebra tbody tr:nth-child(even):hover {
  background: var(--color-primary-soft);
}

.data-table .text-right,
.text-right {
  text-align: right;
}

/* ==========================================================================
   Badges: .badge + .badge-<status>. Legacy .badge.<status> still works.
   ========================================================================== */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  line-height: var(--leading-snug);
  text-transform: uppercase;
  letter-spacing: 0.025em;
  white-space: nowrap;
  background: var(--slate-100);
  color: var(--slate-600);
}

.badge-success,
.badge.success,
.badge.increasing {
  background: var(--color-success-soft);
  color: var(--color-success-text);
}

.badge-info,
.badge.info,
.badge.low {
  background: var(--color-info-soft);
  color: var(--color-info-text);
}

.badge-warning,
.badge.warning,
.badge.medium {
  background: var(--color-warning-soft);
  color: var(--color-warning-text);
}

.badge-danger,
.badge.danger,
.badge.decreasing,
.badge.high {
  background: var(--color-danger-soft);
  color: var(--color-danger-text);
}

.badge-neutral {
  background: var(--slate-100);
  color: var(--slate-600);
}

.badge-primary,
.badge.stable {
  background: var(--primary-100);
  color: var(--primary-700);
}

/* ==========================================================================
   Buttons
   ========================================================================== */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  line-height: var(--leading-normal);
  cursor: pointer;
  text-decoration: none;
  transition: background var(--transition-fast), border-color var(--transition-fast), color var(--transition-fast);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--color-primary);
  color: var(--color-on-primary);
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn-secondary {
  background: var(--color-surface);
  color: var(--slate-700);
  border-color: var(--color-border-strong);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--color-surface-hover);
  border-color: var(--slate-400);
}

.btn-danger {
  background: var(--color-danger);
  color: var(--color-on-primary);
}

.btn-danger:hover:not(:disabled) {
  background: var(--color-danger-text);
}

.btn-sm {
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-xs);
}

/* ==========================================================================
   States
   ========================================================================== */
.loading {
  text-align: center;
  padding: var(--space-12);
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.error {
  background: var(--color-danger-soft);
  border: 1px solid var(--color-danger-border);
  color: var(--color-danger-text);
  padding: var(--space-4);
  border-radius: var(--radius-md);
  margin: var(--space-4) 0;
  font-size: var(--text-sm);
}
</style>
