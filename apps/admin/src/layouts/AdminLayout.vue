<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { roleLabel, useAuth } from '../composables/useAuth'
import { navForRole } from '../nav'

const route = useRoute()
const router = useRouter()
const { me, status, logout, loadMe, role, loggedIn } = useAuth()
const bootError = ref('')

const items = computed(() => navForRole(role.value || 'advisor'))

onMounted(async () => {
  if (!loggedIn.value) return
  try {
    await loadMe()
  } catch (e: any) {
    bootError.value = e?.message || '会话失效'
    logout()
    await router.replace({ name: 'login' })
  }
})

function onLogout() {
  logout()
  void router.push({ name: 'login' })
}
</script>

<template>
  <div class="layout">
    <header class="top">
      <div class="brand-block">
        <span class="brand">擎天学智</span>
        <h1>管理后台</h1>
        <p class="sub">{{ status }}</p>
      </div>
      <div class="top-right">
        <span v-if="me" class="role-pill">{{ roleLabel(me.role) }}</span>
        <button type="button" @click="onLogout">退出</button>
      </div>
    </header>

    <p v-if="bootError" class="err">{{ bootError }}</p>

    <nav class="nav">
      <RouterLink
        v-for="item in items"
        :key="item.name"
        :to="item.to"
        class="nav-link"
        :class="{ active: route.name === item.name || (item.name === 'customers' && String(route.name || '').startsWith('customer')) }"
      >
        {{ item.label }}
      </RouterLink>
    </nav>

    <main class="main">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.layout {
  max-width: 1100px;
  margin: 0 auto;
  padding: 16px 16px 48px;
}
.top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  flex-wrap: wrap;
}
.brand {
  display: inline-block;
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--accent);
  font-size: 14px;
}
h1 {
  margin: 2px 0 0;
  font-size: 1.25rem;
  font-family: var(--font-display);
}
.sub { margin: 4px 0 0; color: var(--muted); font-size: 13px; }
.top-right {
  display: flex;
  gap: 8px;
  align-items: center;
}
.role-pill {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent);
}
.nav {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin: 14px 0 12px;
}
.nav-link {
  text-decoration: none;
  color: var(--ink);
  border: 1px solid var(--line);
  background: var(--surface);
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 13px;
}
.nav-link.active {
  background: var(--ink);
  border-color: var(--ink);
  color: #fff;
}
.err { color: var(--danger); font-size: 13px; }
.main { min-height: 360px; }
</style>
