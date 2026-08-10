<script setup lang="ts">
import { onMounted, ref } from 'vue'

const apiBase = '/api/v1'
const status = ref('idle')
const token = ref('')
const customerId = ref<number | null>(null)
const hello = ref('')
const sseLog = ref<string[]>([])
const fakeLlm = ref('')

async function exchange() {
  status.value = 'exchanging'
  const res = await fetch(`${apiBase}/auth/wecom/exchange`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code: 'mock_code', external_userid: 'demo_wang' }),
  })
  const json = await res.json()
  if (json.code !== 0) {
    status.value = `exchange failed: ${json.message}`
    return
  }
  token.value = json.data.access_token
  customerId.value = json.data.customer_id
  status.value = 'token ready'
}

async function loadHello() {
  const res = await fetch(`${apiBase}/hello`)
  hello.value = JSON.stringify(await res.json())
}

async function previewProfile() {
  if (!token.value) await exchange()
  const res = await fetch(`${apiBase}/sidebar/profile/generate`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token.value}` },
  })
  fakeLlm.value = JSON.stringify(await res.json(), null, 2)
}

function connectSse() {
  if (!token.value || !customerId.value) {
    status.value = 'need token + customer first'
    return
  }
  const url = `${apiBase}/sidebar/sse?customer_id=${customerId.value}`
  // EventSource cannot set Authorization; use fetch stream for scaffold
  void (async () => {
    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${token.value}`, Accept: 'text/event-stream' },
    })
    if (!res.body) return
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    status.value = 'sse connected'
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value)
      sseLog.value = [chunk.trim(), ...sseLog.value].slice(0, 8)
      if (sseLog.value.length >= 2) break
    }
  })()
}

onMounted(() => {
  void loadHello()
})
</script>

<template>
  <main class="page">
    <h1>擎天学智 · 侧边栏壳</h1>
    <p class="sub">Vue 3 + TS scaffold · Stage 2</p>
    <p class="status">状态：{{ status }}</p>
    <div class="actions">
      <button type="button" @click="exchange">Mock 换票</button>
      <button type="button" @click="previewProfile">FakeLLM 画像预览</button>
      <button type="button" @click="connectSse">SSE ping</button>
    </div>
    <section>
      <h2>Hello</h2>
      <pre>{{ hello }}</pre>
    </section>
    <section>
      <h2>Token / Customer</h2>
      <pre>customer_id={{ customerId }}
token={{ token ? token.slice(0, 24) + '…' : '' }}</pre>
    </section>
    <section>
      <h2>FakeLLM</h2>
      <pre>{{ fakeLlm }}</pre>
    </section>
    <section>
      <h2>SSE</h2>
      <pre>{{ sseLog.join('\n---\n') }}</pre>
    </section>
  </main>
</template>

<style scoped>
.page {
  font-family: "Segoe UI", "PingFang SC", sans-serif;
  max-width: 720px;
  margin: 0 auto;
  padding: 24px 16px 48px;
  color: #1f2a37;
}
h1 {
  font-size: 1.4rem;
  margin: 0 0 4px;
}
.sub,
.status {
  color: #667085;
  margin: 0 0 12px;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
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
section {
  margin-top: 16px;
}
h2 {
  font-size: 0.95rem;
  margin: 0 0 6px;
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
