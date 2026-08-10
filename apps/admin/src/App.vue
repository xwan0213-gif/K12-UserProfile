<script setup lang="ts">
import { ref } from 'vue'

const apiBase = '/api/v1'
const loginName = ref('admin')
const password = ref('admin123')
const status = ref('idle')
const token = ref('')
const me = ref('')

async function login() {
  status.value = 'logging in'
  const res = await fetch(`${apiBase}/auth/admin/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      login_name: loginName.value,
      password: password.value,
    }),
  })
  const json = await res.json()
  if (json.code !== 0) {
    status.value = `failed: ${json.message}`
    return
  }
  token.value = json.data.access_token
  status.value = 'logged in'
}

async function loadMe() {
  if (!token.value) {
    status.value = 'login first'
    return
  }
  const res = await fetch(`${apiBase}/auth/me`, {
    headers: { Authorization: `Bearer ${token.value}` },
  })
  me.value = JSON.stringify(await res.json(), null, 2)
}
</script>

<template>
  <main class="page">
    <h1>擎天学智 · 管理后台壳</h1>
    <p class="sub">Vue 3 + TS scaffold · Stage 2</p>
    <p class="status">状态：{{ status }}</p>
    <form class="form" @submit.prevent="login">
      <label>
        账号
        <input v-model="loginName" autocomplete="username" />
      </label>
      <label>
        密码
        <input v-model="password" type="password" autocomplete="current-password" />
      </label>
      <div class="actions">
        <button type="submit">登录</button>
        <button type="button" @click="loadMe">GET /auth/me</button>
      </div>
    </form>
    <section>
      <h2>Token</h2>
      <pre>{{ token ? token.slice(0, 40) + '…' : '—' }}</pre>
    </section>
    <section>
      <h2>/auth/me</h2>
      <pre>{{ me || '—' }}</pre>
    </section>
    <p class="hint">提示：先调 API `POST /api/v1/mock/seed/demo` 再登录（默认 admin / admin123）。</p>
  </main>
</template>

<style scoped>
.page {
  font-family: "Segoe UI", "PingFang SC", sans-serif;
  max-width: 640px;
  margin: 0 auto;
  padding: 32px 16px 48px;
  color: #1f2a37;
}
h1 {
  margin: 0 0 4px;
  font-size: 1.5rem;
}
.sub,
.status,
.hint {
  color: #667085;
}
.form {
  display: grid;
  gap: 12px;
  margin: 16px 0;
}
label {
  display: grid;
  gap: 4px;
  font-size: 0.9rem;
}
input {
  padding: 8px 10px;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
}
.actions {
  display: flex;
  gap: 8px;
}
button {
  border: 1px solid #d0d5dd;
  background: #fff;
  border-radius: 8px;
  padding: 8px 12px;
  cursor: pointer;
}
button:hover {
  background: #f2f4f7;
}
pre {
  background: #f8fafc;
  border: 1px solid #e4e7ec;
  border-radius: 8px;
  padding: 10px;
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 12px;
}
</style>
