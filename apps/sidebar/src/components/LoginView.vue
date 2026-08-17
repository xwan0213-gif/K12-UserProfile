<script setup lang="ts">
import { ref } from 'vue'
import { useAuth } from '../composables/useAuth'

const emit = defineEmits<{
  loggedIn: []
}>()

const { login, redirectManagerToAdmin } = useAuth()

const loginName = ref('advisor')
const password = ref('advisor123')
const error = ref('')
const busy = ref(false)

async function onSubmit() {
  error.value = ''
  busy.value = true
  try {
    const user = await login(loginName.value.trim(), password.value)
    if (user.role === 'admin' || user.role === 'regional') {
      redirectManagerToAdmin()
      return
    }
    emit('loggedIn')
  } catch (e: any) {
    error.value = e?.message || '登录失败'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="relative flex min-h-screen items-center justify-center overflow-hidden bg-stone-50 px-4 py-8">
    <div
      class="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_40%_at_10%_20%,rgba(63,94,107,0.12),transparent_55%)]"
      aria-hidden="true"
    />
    <section
      class="relative w-full max-w-md overflow-hidden rounded-panel border border-line bg-white shadow-soft"
    >
      <div class="absolute bottom-0 left-0 top-0 w-1 bg-fjord" aria-hidden="true" />
      <div class="px-7 py-7 pl-8">
        <p class="font-display text-xl font-semibold tracking-wide text-fjord">擎天学智</p>
        <h1 class="mt-2 font-display text-2xl font-semibold text-ink">登录</h1>
        <p class="mt-2 text-[13px] text-muted">顾问进入工作台 · 管理岗进入后台</p>

        <form class="mt-6 grid gap-3" @submit.prevent="onSubmit">
          <label class="grid gap-1 text-[13px] text-muted">
            账号
            <input
              v-model="loginName"
              autocomplete="username"
              required
              class="rounded-control border border-line bg-white px-3 py-2.5 text-ink"
            />
          </label>
          <label class="grid gap-1 text-[13px] text-muted">
            密码
            <input
              v-model="password"
              type="password"
              autocomplete="current-password"
              required
              class="rounded-control border border-line bg-white px-3 py-2.5 text-ink"
            />
          </label>
          <p v-if="error" class="m-0 text-[13px] text-danger">{{ error }}</p>
          <button
            type="submit"
            class="mt-1 min-h-10 rounded-control bg-fjord px-3 py-2 font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            :disabled="busy"
          >
            {{ busy ? '登录中…' : '登录' }}
          </button>
        </form>

        <p class="mt-4 text-xs leading-relaxed text-muted">
          演示：admin / admin123 · regional / regional123 · advisor / advisor123
        </p>
      </div>
    </section>
  </div>
</template>
