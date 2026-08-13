<script setup lang="ts">
import { onMounted, ref } from 'vue'
import EmptyState from '../components/EmptyState.vue'
import { useAuth } from '../composables/useAuth'

const { api } = useAuth()
const tags = ref<any>(null)
const tagStats = ref<any>(null)
const error = ref('')
const loading = ref(true)

onMounted(async () => {
  try {
    tags.value = await api('/admin/tags')
    tagStats.value = await api('/admin/tags/stats')
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section class="card">
    <h2>标签体系</h2>
    <p v-if="loading" class="muted">加载中…</p>
    <EmptyState v-else-if="error" :title="error" />
    <template v-else>
      <EmptyState v-if="!(tags?.items || []).length" title="词表为空" />
      <table v-else class="data">
        <thead>
          <tr><th>名称</th><th>SOP</th><th>客户数</th><th>启用</th></tr>
        </thead>
        <tbody>
          <tr v-for="t in tags.items" :key="t.id">
            <td>{{ t.name }}</td>
            <td>{{ t.sop_text || '—' }}</td>
            <td>{{ t.customer_count ?? '—' }}</td>
            <td>{{ t.enabled ? '是' : '否' }}</td>
          </tr>
        </tbody>
      </table>
      <h3>分布</h3>
      <ul v-if="(tagStats?.items || []).length">
        <li v-for="s in tagStats.items" :key="s.tag_id">
          {{ s.name }}：{{ s.customer_count }}
        </li>
      </ul>
      <EmptyState v-else title="暂无分布统计" />
      <p class="muted tip">标签新建/编辑属阶段 D.5。</p>
    </template>
  </section>
</template>

<style scoped>
h2 { margin: 0 0 10px; font-size: 1.05rem; }
h3 { margin: 14px 0 6px; font-size: 0.95rem; }
.tip { margin-top: 10px; }
</style>
