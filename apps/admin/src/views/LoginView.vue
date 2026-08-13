<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const route = useRoute()
const { login, loggedIn } = useAuth()

const loginName = ref('admin')
const password = ref('admin123')
const error = ref('')
const busy = ref(false)

async function onSubmit() {
  error.value = ''
  busy.value = true
  try {
    await login(loginName.value.trim(), password.value)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await router.replace(redirect || '/')
  } catch (e: any) {
    error.value = e?.message || '登录失败'
  } finally {
    busy.value = false
  }
}

if (loggedIn.value) {
  void router.replace('/')
}
</script>

<template>
  <div class="login-page">
    <div class="hero" aria-hidden="true" />
    <section class="panel card">
      <p class="brand">擎天学智</p>
      <h1>管理后台</h1>
      <p class="muted lead">青墨工作台 · 组织、客户与 AI 运营</p>

      <form class="form" @submit.prevent="onSubmit">
        <label>
          账号
          <input v-model="loginName" autocomplete="username" required />
        </label>
        <label>
          密码
          <input v-model="password" type="password" autocomplete="current-password" required />
        </label>
        <p v-if="error" class="err">{{ error }}</p>
        <button type="submit" class="primary" :disabled="busy">
          {{ busy ? '登录中…' : '登录' }}
        </button>
      </form>

      <p class="muted tip">
        演示账号：admin / admin123 · regional / regional123 · advisor / advisor123（需 seed）
      </p>
      <p class="muted tip">顾问日常作业请用侧栏工作台；本后台面向管理与区域主管。</p>
    </section>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px 16px;
  position: relative;
  overflow: hidden;
}
.hero {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 80% 50% at 20% 20%, rgba(15, 118, 110, 0.18), transparent 55%),
    radial-gradient(ellipse 60% 40% at 80% 10%, rgba(67, 56, 202, 0.1), transparent 50%),
    linear-gradient(165deg, var(--bg-hero) 0%, var(--bg) 55%, #fff 100%);
  z-index: 0;
}
.panel {
  position: relative;
  z-index: 1;
  width: min(400px, 100%);
  padding: 28px 24px 22px;
}
.brand {
  margin: 0;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.15rem;
  color: var(--accent);
  letter-spacing: 0.02em;
}
h1 {
  margin: 6px 0 0;
  font-size: 1.55rem;
  font-family: var(--font-display);
}
.lead { margin: 8px 0 18px; }
.form {
  display: grid;
  gap: 12px;
}
.form label {
  display: grid;
  gap: 4px;
  font-size: 13px;
  color: var(--muted);
}
.form input {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 9px 10px;
  color: var(--ink);
}
.err {
  margin: 0;
  color: var(--danger);
  font-size: 13px;
}
.tip { margin-top: 14px; font-size: 12px; line-height: 1.45; }
</style>
