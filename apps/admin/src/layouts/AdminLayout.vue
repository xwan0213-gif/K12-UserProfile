<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import {
  LayoutDashboard,
  Users,
  Building2,
  UserRound,
  ShoppingBag,
  Tags,
  MessageSquareText,
  Sparkles,
  LogOut,
  Menu,
  X,
} from '@lucide/vue'
import UiIcon from '../components/UiIcon.vue'
import { roleLabel, useAuth } from '../composables/useAuth'
import { navForRole } from '../nav'

const route = useRoute()
const router = useRouter()
const { me, status, logout, loadMe, role, loggedIn, redirectAdvisorAway } = useAuth()
const bootError = ref('')
const navOpen = ref(false)

const iconMap: Record<string, typeof LayoutDashboard> = {
  dashboard: LayoutDashboard,
  customers: Users,
  orgs: Building2,
  users: UserRound,
  orders: ShoppingBag,
  tags: Tags,
  scripts: MessageSquareText,
  ai: Sparkles,
}

const items = computed(() => navForRole(role.value || 'advisor'))

onMounted(async () => {
  if (!loggedIn.value) return
  try {
    const u = await loadMe()
    if (u?.role === 'advisor') {
      redirectAdvisorAway()
    }
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

function isActive(name: string) {
  if (route.name === name) return true
  if (name === 'customers' && String(route.name || '').startsWith('customer')) return true
  return false
}
</script>

<template>
  <div class="relative min-h-screen bg-stone-50 lg:grid lg:grid-cols-[220px_minmax(0,1fr)]">
    <aside
      class="z-40 flex max-h-screen flex-col border-r border-line bg-white lg:sticky lg:top-0"
      :class="
        navOpen
          ? 'fixed inset-y-0 left-0 w-[min(220px,86vw)] translate-x-0 shadow-soft'
          : 'fixed inset-y-0 left-0 w-[min(220px,86vw)] -translate-x-[105%] lg:static lg:translate-x-0'
      "
    >
      <div class="border-b border-line px-4 py-5">
        <span class="block font-display text-[1.05rem] font-semibold tracking-wide text-fjord"
          >擎天学智</span
        >
        <span class="mt-1 block text-xs text-muted">管理后台</span>
      </div>
      <nav class="flex flex-1 flex-col gap-0.5 p-2.5">
        <RouterLink
          v-for="item in items"
          :key="item.name"
          :to="item.to"
          class="flex items-center gap-2 rounded-control px-3 py-2.5 text-sm text-muted transition-colors hover:bg-stone-50 hover:text-ink"
          :class="isActive(item.name) ? 'bg-fjord-soft font-semibold text-fjord' : ''"
          @click="navOpen = false"
        >
          <UiIcon :icon="iconMap[item.name] || LayoutDashboard" :size="18" />
          {{ item.label }}
        </RouterLink>
      </nav>
      <div class="border-t border-line px-4 py-4">
        <p v-if="me" class="m-0 flex flex-wrap items-center gap-2 text-[13px]">
          {{ me.name }}
          <span class="rounded bg-fjord-soft px-1.5 py-0.5 text-[11px] text-fjord">{{
            roleLabel(me.role)
          }}</span>
        </p>
        <p class="mb-2.5 mt-1.5 text-[11px] text-muted">{{ status }}</p>
        <button
          type="button"
          class="inline-flex items-center gap-1.5 rounded-control border border-line bg-white px-2.5 py-1.5 text-[13px] text-ink hover:bg-stone-50"
          @click="onLogout"
        >
          <UiIcon :icon="LogOut" :size="16" />
          退出
        </button>
      </div>
    </aside>

    <div class="flex min-w-0 flex-col">
      <header
        class="sticky top-0 z-30 flex items-center justify-between gap-2 border-b border-line bg-white px-3 py-2.5 lg:hidden"
      >
        <button
          type="button"
          class="rounded-control border border-line bg-white p-2"
          :aria-label="navOpen ? '关闭菜单' : '打开菜单'"
          @click="navOpen = !navOpen"
        >
          <UiIcon :icon="navOpen ? X : Menu" :size="18" />
        </button>
        <span class="font-display text-sm font-semibold text-fjord">擎天学智</span>
        <button
          type="button"
          class="rounded-control border border-line bg-white p-2"
          aria-label="退出登录"
          @click="onLogout"
        >
          <UiIcon :icon="LogOut" :size="18" />
        </button>
      </header>

      <p v-if="bootError" class="mx-5 mt-3 text-danger">{{ bootError }}</p>

      <main class="mx-auto w-full max-w-[1280px] px-3 py-4 pb-12 sm:px-5 sm:py-5">
        <RouterView v-slot="{ Component }">
          <Transition name="fade" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
      </main>
    </div>

    <button
      v-if="navOpen"
      type="button"
      class="fixed inset-0 z-[35] border-0 bg-ink/35 p-0 lg:hidden"
      aria-label="关闭导航"
      @click="navOpen = false"
    />
  </div>
</template>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 150ms ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
