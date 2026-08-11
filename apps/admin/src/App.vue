<script setup lang="ts">
import { computed, ref } from 'vue'

const apiBase = '/api/v1'
const token = ref(localStorage.getItem('admin_token') || '')
const loginName = ref('admin')
const password = ref('admin123')
const status = ref(token.value ? '已恢复本地 token' : '未登录')
const me = ref<any>(null)
const nav = ref<'dashboard' | 'customers' | 'users' | 'orders' | 'tags' | 'scripts' | 'ai'>('dashboard')
const dashboard = ref<any>(null)
const customers = ref<any>(null)
const customerDetail = ref<any>(null)
const users = ref<any>(null)
const orders = ref<any>(null)
const tags = ref<any>(null)
const tagStats = ref<any>(null)
const scripts = ref<any>(null)
const adoption = ref<any>(null)
const scriptForm = ref({
  scene: 'sales',
  stage: 'junior' as string | null,
  title: '',
  content: '',
  enabled: true,
})

const loggedIn = computed(() => !!token.value)

async function api(path: string, init: RequestInit = {}) {
  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string> | undefined),
  }
  if (token.value) headers.Authorization = `Bearer ${token.value}`
  if (init.body && !headers['Content-Type']) headers['Content-Type'] = 'application/json'
  const res = await fetch(`${apiBase}${path}`, { ...init, headers })
  const json = await res.json()
  if (json.code !== 0) throw new Error(json.message || '请求失败')
  return json.data
}

async function login() {
  status.value = '登录中…'
  const data = await api('/auth/admin/login', {
    method: 'POST',
    body: JSON.stringify({ login_name: loginName.value, password: password.value }),
  })
  token.value = data.access_token
  localStorage.setItem('admin_token', token.value)
  me.value = data.user
  status.value = `已登录：${data.user.name}（${data.user.role}）`
  await loadNav()
}

async function loadMe() {
  me.value = await api('/auth/me')
}

async function loadNav() {
  if (!token.value) return
  await loadMe()
  if (nav.value === 'dashboard') dashboard.value = await api('/admin/dashboard/summary')
  if (nav.value === 'customers') customers.value = await api('/admin/customers?page=1&page_size=20')
  if (nav.value === 'users') users.value = await api('/admin/users?page=1&page_size=20')
  if (nav.value === 'orders') orders.value = await api('/admin/orders?page=1&page_size=20')
  if (nav.value === 'tags') {
    tags.value = await api('/admin/tags')
    tagStats.value = await api('/admin/tags/stats')
  }
  if (nav.value === 'scripts') scripts.value = await api('/admin/script-templates')
  if (nav.value === 'ai') adoption.value = await api('/admin/ai/adoption?group_by=advisor')
}

async function createScript() {
  if (!scriptForm.value.title || !scriptForm.value.content) return
  const body = {
    ...scriptForm.value,
    stage: scriptForm.value.stage || null,
  }
  await api('/admin/script-templates', {
    method: 'POST',
    body: JSON.stringify(body),
  })
  scriptForm.value.title = ''
  scriptForm.value.content = ''
  scripts.value = await api('/admin/script-templates')
  status.value = '话术模板已创建'
}

async function disableScript(id: number) {
  await api(`/admin/script-templates/${id}`, { method: 'DELETE' })
  scripts.value = await api('/admin/script-templates')
}

async function openCustomer(id: number) {
  customerDetail.value = await api(`/admin/customers/${id}`)
}

async function switchNav(key: typeof nav.value) {
  nav.value = key
  customerDetail.value = null
  await loadNav()
}

function logout() {
  token.value = ''
  localStorage.removeItem('admin_token')
  status.value = '已退出'
}
</script>

<template>
  <main class="page">
    <header class="head">
      <div>
        <h1>擎天学智 · 管理后台</h1>
        <p class="sub">{{ status }}</p>
      </div>
      <button v-if="loggedIn" type="button" @click="logout">退出</button>
    </header>

    <section v-if="!loggedIn" class="card">
      <form class="form" @submit.prevent="login">
        <label>账号 <input v-model="loginName" /></label>
        <label>密码 <input v-model="password" type="password" /></label>
        <button type="submit">登录</button>
      </form>
      <p class="muted">演示：admin/admin123 · regional/regional123 · advisor/advisor123（需重新 seed）</p>
    </section>

    <template v-else>
      <nav class="tabs">
        <button type="button" :class="{ active: nav === 'dashboard' }" @click="switchNav('dashboard')">看板</button>
        <button type="button" :class="{ active: nav === 'customers' }" @click="switchNav('customers')">客户</button>
        <button type="button" :class="{ active: nav === 'users' }" @click="switchNav('users')">员工</button>
        <button type="button" :class="{ active: nav === 'orders' }" @click="switchNav('orders')">订单</button>
        <button type="button" :class="{ active: nav === 'tags' }" @click="switchNav('tags')">标签</button>
        <button type="button" :class="{ active: nav === 'scripts' }" @click="switchNav('scripts')">话术模板</button>
        <button type="button" :class="{ active: nav === 'ai' }" @click="switchNav('ai')">AI 分析</button>
      </nav>

      <section v-if="nav === 'dashboard' && dashboard" class="card">
        <h2>看板</h2>
        <div class="grid">
          <div><span>线索</span><strong>{{ dashboard.funnel.lead }}</strong></div>
          <div><span>意向</span><strong>{{ dashboard.funnel.intent }}</strong></div>
          <div><span>试听</span><strong>{{ dashboard.funnel.trial }}</strong></div>
          <div><span>成交</span><strong>{{ dashboard.funnel.deal }}</strong></div>
        </div>
        <p class="muted">续费率（MVP 口径）：{{ dashboard.renewal_rate }}</p>
        <h3>顾问人效 Top</h3>
        <ul>
          <li v-for="a in dashboard.advisor_top" :key="a.user_id">
            {{ a.name }} · 客户 {{ a.customers }} · score {{ a.score }}
          </li>
        </ul>
      </section>

      <section v-if="nav === 'customers'" class="card">
        <h2>客户</h2>
        <table>
          <thead>
            <tr><th>家长/学员</th><th>年级</th><th>标签</th><th>负责人</th><th>画像</th></tr>
          </thead>
          <tbody>
            <tr v-for="c in customers?.items || []" :key="c.id" @click="openCustomer(c.id)">
              <td>{{ c.parent_name }} / {{ c.student_name }}</td>
              <td>{{ c.grade }}</td>
              <td>{{ (c.tags || []).join('、') }}</td>
              <td>{{ c.owner_name }}</td>
              <td>{{ c.profile_status }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="customerDetail" class="detail">
          <h3>详情 #{{ customerDetail.customer.id }}</h3>
          <pre>{{ JSON.stringify(customerDetail.profile, null, 2) }}</pre>
          <h4>沟通</h4>
          <ul>
            <li v-for="m in customerDetail.recent_messages" :key="m.id">
              [{{ m.direction }}] {{ m.content }}
            </li>
          </ul>
        </div>
      </section>

      <section v-if="nav === 'users'" class="card">
        <h2>员工</h2>
        <table>
          <thead><tr><th>姓名</th><th>角色</th><th>组织</th><th>状态</th></tr></thead>
          <tbody>
            <tr v-for="u in users?.items || []" :key="u.id">
              <td>{{ u.name }}</td>
              <td>{{ u.role }}</td>
              <td>{{ u.org_id }}</td>
              <td>{{ u.status }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section v-if="nav === 'orders'" class="card">
        <h2>订单</h2>
        <table>
          <thead><tr><th>单号</th><th>客户</th><th>课程</th><th>金额</th><th>状态</th></tr></thead>
          <tbody>
            <tr v-for="o in orders?.items || []" :key="o.id">
              <td>{{ o.external_order_no }}</td>
              <td>{{ o.parent_name }}</td>
              <td>{{ o.title }}</td>
              <td>{{ o.amount }}</td>
              <td>{{ o.status }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section v-if="nav === 'tags'" class="card">
        <h2>标签体系</h2>
        <table>
          <thead><tr><th>名称</th><th>SOP</th><th>客户数</th><th>启用</th></tr></thead>
          <tbody>
            <tr v-for="t in tags?.items || []" :key="t.id">
              <td>{{ t.name }}</td>
              <td>{{ t.sop_text }}</td>
              <td>{{ t.customer_count }}</td>
              <td>{{ t.enabled }}</td>
            </tr>
          </tbody>
        </table>
        <h3>分布</h3>
        <ul>
          <li v-for="s in tagStats?.items || []" :key="s.tag_id">
            {{ s.name }}：{{ s.customer_count }}
          </li>
        </ul>
      </section>

      <section v-if="nav === 'scripts'" class="card">
        <h2>话术模板</h2>
        <form class="form wide" @submit.prevent="createScript">
          <label>场景
            <select v-model="scriptForm.scene">
              <option value="sales">sales</option>
              <option value="cs">cs</option>
            </select>
          </label>
          <label>学段
            <select v-model="scriptForm.stage">
              <option value="primary">primary</option>
              <option value="junior">junior</option>
              <option value="senior">senior</option>
              <option :value="null">通用</option>
            </select>
          </label>
          <label>标题 <input v-model="scriptForm.title" /></label>
          <label>正文 <textarea v-model="scriptForm.content" rows="3" /></label>
          <button type="submit">新增模板</button>
        </form>
        <table>
          <thead><tr><th>场景</th><th>学段</th><th>标题</th><th>启用</th><th></th></tr></thead>
          <tbody>
            <tr v-for="s in scripts?.items || []" :key="s.id">
              <td>{{ s.scene }}</td>
              <td>{{ s.stage || '通用' }}</td>
              <td>{{ s.title }}</td>
              <td>{{ s.enabled }}</td>
              <td>
                <button v-if="s.enabled" type="button" @click="disableScript(s.id)">停用</button>
              </td>
            </tr>
          </tbody>
        </table>
        <p class="muted">批量导入：python data/seed/import_seed_data.py --base-url http://localhost:18000/api/v1</p>
      </section>

      <section v-if="nav === 'ai'" class="card">
        <h2>AI 使用分析（采纳率）</h2>
        <table>
          <thead>
            <tr>
              <th>顾问</th><th>曝光</th><th>复制</th><th>采纳</th><th>编辑采纳</th><th>拒绝</th>
              <th>标签确认</th><th>标签拒绝</th><th>采纳率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in adoption?.items || []" :key="i">
              <td>{{ row.name }}</td>
              <td>{{ row.impressions }}</td>
              <td>{{ row.copy }}</td>
              <td>{{ row.adopt }}</td>
              <td>{{ row.edit_adopt }}</td>
              <td>{{ row.reject }}</td>
              <td>{{ row.tag_confirm }}</td>
              <td>{{ row.tag_reject }}</td>
              <td>{{ row.adoption_rate ?? '—' }}</td>
            </tr>
          </tbody>
        </table>
        <p class="muted">口径来自 event_log + suggestion 曝光；二期埋点：reply_* / tag_recommend_*</p>
      </section>
    </template>
  </main>
</template>

<style scoped>
.page {
  max-width: 960px;
  margin: 0 auto;
  padding: 20px 16px 48px;
  font-family: "Segoe UI", "PingFang SC", sans-serif;
  color: #1f2a37;
}
.head { display: flex; justify-content: space-between; align-items: center; }
h1 { margin: 0; font-size: 1.4rem; }
.sub, .muted { color: #667085; }
.card {
  margin-top: 12px;
  background: rgba(255,255,255,0.92);
  border: 1px solid #e4e7ec;
  border-radius: 12px;
  padding: 14px;
}
.form { display: grid; gap: 10px; max-width: 360px; }
.form.wide { max-width: 640px; }
label { display: grid; gap: 4px; }
input, select, textarea {
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  padding: 8px 10px;
  font: inherit;
}
.tabs { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
.tabs button, button {
  border: 1px solid #d0d5dd;
  background: #fff;
  border-radius: 8px;
  padding: 6px 10px;
  cursor: pointer;
}
.tabs button.active { background: #027a48; color: #fff; border-color: #027a48; }
.grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}
.grid div {
  background: #f8fafc;
  border-radius: 8px;
  padding: 10px;
  display: grid;
}
.grid span { color: #667085; font-size: 12px; }
.grid strong { font-size: 1.3rem; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { border-bottom: 1px solid #eef2f6; padding: 8px 6px; text-align: left; }
tbody tr { cursor: pointer; }
tbody tr:hover { background: #f8fafc; }
pre {
  background: #f8fafc;
  border: 1px solid #e4e7ec;
  border-radius: 8px;
  padding: 8px;
  font-size: 12px;
  white-space: pre-wrap;
}
.detail { margin-top: 12px; }
@media (max-width: 700px) {
  .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
