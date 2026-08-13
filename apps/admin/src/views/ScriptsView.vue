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
const filterScene = ref('')
const filterEnabled = ref('')

const scriptForm = ref({
  scene: 'sales',
  stage: 'junior' as string | null,
  title: '',
  content: '',
  enabled: true,
})
const editingId = ref<number | null>(null)
const editForm = ref({
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
    const qs = new URLSearchParams()
    if (filterScene.value) qs.set('scene', filterScene.value)
    if (filterEnabled.value !== '') qs.set('enabled', filterEnabled.value)
    const q = qs.toString()
    scripts.value = await api(`/admin/script-templates${q ? `?${q}` : ''}`)
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

function startEdit(s: any) {
  editingId.value = s.id
  editForm.value = {
    scene: s.scene,
    stage: s.stage ?? null,
    title: s.title || '',
    content: s.content || '',
    enabled: !!s.enabled,
  }
}

async function saveEdit() {
  if (editingId.value == null) return
  try {
    await api(`/admin/script-templates/${editingId.value}`, {
      method: 'PATCH',
      body: JSON.stringify({
        scene: editForm.value.scene,
        stage: editForm.value.stage || null,
        title: editForm.value.title,
        content: editForm.value.content,
        enabled: editForm.value.enabled,
      }),
    })
    editingId.value = null
    status.value = '模板已更新'
    await load()
  } catch (e: any) {
    status.value = e?.message || '更新失败'
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

    <form class="filters" @submit.prevent="load">
      <select v-model="filterScene">
        <option value="">全部场景</option>
        <option value="sales">销售</option>
        <option value="cs">客服</option>
      </select>
      <select v-model="filterEnabled">
        <option value="">全部状态</option>
        <option value="true">启用</option>
        <option value="false">停用</option>
      </select>
      <button type="submit" class="primary">筛选</button>
    </form>

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
      <p v-else class="muted">顾问账号仅可查看模板；新建/编辑/停用需管理员或区域主管。</p>

      <EmptyState v-if="!(scripts?.items || []).length" title="暂无模板" />
      <table v-else class="data">
        <thead>
          <tr><th>场景</th><th>学段</th><th>标题</th><th>启用</th><th></th></tr>
        </thead>
        <tbody>
          <tr v-for="s in scripts.items" :key="s.id">
            <template v-if="editingId === s.id">
              <td>
                <select v-model="editForm.scene">
                  <option value="sales">销售</option>
                  <option value="cs">客服</option>
                </select>
              </td>
              <td>
                <select v-model="editForm.stage">
                  <option value="primary">小学</option>
                  <option value="junior">初中</option>
                  <option value="senior">高中</option>
                  <option :value="null">通用</option>
                </select>
              </td>
              <td colspan="2">
                <input v-model="editForm.title" placeholder="标题" />
                <textarea v-model="editForm.content" rows="2" />
                <label class="check"><input v-model="editForm.enabled" type="checkbox" /> 启用</label>
              </td>
              <td class="actions">
                <button type="button" class="primary" @click="saveEdit">保存</button>
                <button type="button" @click="editingId = null">取消</button>
              </td>
            </template>
            <template v-else>
              <td>{{ s.scene }}</td>
              <td>{{ s.stage || '通用' }}</td>
              <td>{{ s.title }}</td>
              <td>{{ s.enabled ? '是' : '否' }}</td>
              <td class="actions">
                <button v-if="writable" type="button" @click="startEdit(s)">改</button>
                <button v-if="writable && s.enabled" type="button" @click="disableScript(s.id)">
                  停用
                </button>
              </td>
            </template>
          </tr>
        </tbody>
      </table>
    </template>
  </section>
</template>

<style scoped>
h2 { margin: 0 0 10px; font-size: 1.05rem; }
.filters {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.filters select,
.form input,
.form select,
.form textarea,
td input,
td select,
td textarea {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 6px 8px;
  color: var(--ink);
  width: 100%;
}
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
.check {
  display: flex !important;
  flex-direction: row !important;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
}
.actions { display: flex; gap: 6px; flex-wrap: wrap; }
</style>
