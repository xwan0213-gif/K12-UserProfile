<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import EmptyState from '../components/EmptyState.vue'
import { useAuth } from '../composables/useAuth'
import { canWriteScripts } from '../nav'

const { api, role } = useAuth()
const scripts = ref<any>(null)
const error = ref('')
const loading = ref(true)
const status = ref('')
const writable = computed(() => canWriteScripts(role.value))

const scriptForm = ref({
  scene: 'sales',
  stage: 'junior' as string | null,
  title: '',
  content: '',
  enabled: true,
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    scripts.value = await api('/admin/script-templates')
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function createScript() {
  if (!scriptForm.value.title || !scriptForm.value.content) return
  try {
    await api('/admin/script-templates', {
      method: 'POST',
      body: JSON.stringify({
        ...scriptForm.value,
        stage: scriptForm.value.stage || null,
      }),
    })
    scriptForm.value.title = ''
    scriptForm.value.content = ''
    status.value = '话术模板已创建'
    await load()
  } catch (e: any) {
    status.value = e?.message || '创建失败'
  }
}

async function disableScript(id: number) {
  try {
    await api(`/admin/script-templates/${id}`, { method: 'DELETE' })
    status.value = '已停用'
    await load()
  } catch (e: any) {
    status.value = e?.message || '停用失败'
  }
}

onMounted(() => {
  void load()
})
</script>

<template>
  <section class="card">
    <h2>话术模板</h2>
    <p v-if="status" class="muted">{{ status }}</p>
    <p v-if="loading" class="muted">加载中…</p>
    <EmptyState v-else-if="error" :title="error" />
    <template v-else>
      <form v-if="writable" class="form" @submit.prevent="createScript">
        <label>
          场景
          <select v-model="scriptForm.scene">
            <option value="sales">销售</option>
            <option value="cs">客服</option>
          </select>
        </label>
        <label>
          学段
          <select v-model="scriptForm.stage">
            <option value="primary">小学</option>
            <option value="junior">初中</option>
            <option value="senior">高中</option>
            <option :value="null">通用</option>
          </select>
        </label>
        <label>标题 <input v-model="scriptForm.title" required /></label>
        <label>正文 <textarea v-model="scriptForm.content" rows="3" required /></label>
        <button type="submit" class="primary">新增模板</button>
      </form>
      <p v-else class="muted">顾问账号仅可查看模板；新建/停用需管理员或区域主管。</p>

      <EmptyState v-if="!(scripts?.items || []).length" title="暂无模板" />
      <table v-else class="data">
        <thead>
          <tr><th>场景</th><th>学段</th><th>标题</th><th>启用</th><th></th></tr>
        </thead>
        <tbody>
          <tr v-for="s in scripts.items" :key="s.id">
            <td>{{ s.scene }}</td>
            <td>{{ s.stage || '通用' }}</td>
            <td>{{ s.title }}</td>
            <td>{{ s.enabled ? '是' : '否' }}</td>
            <td>
              <button
                v-if="writable && s.enabled"
                type="button"
                @click="disableScript(s.id)"
              >
                停用
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </template>
  </section>
</template>

<style scoped>
h2 { margin: 0 0 10px; font-size: 1.05rem; }
.form {
  display: grid;
  gap: 8px;
  max-width: 640px;
  margin-bottom: 14px;
}
.form label {
  display: grid;
  gap: 4px;
  font-size: 13px;
  color: var(--muted);
}
.form input,
.form select,
.form textarea {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 8px 10px;
  color: var(--ink);
}
</style>
