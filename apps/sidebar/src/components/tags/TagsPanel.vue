<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { ApiFn } from '../../composables/useApi'

export type CatalogTag = {
  id: number
  name: string
  description?: string | null
  sop_text?: string | null
}

const props = defineProps<{
  api: ApiFn
  customerId: number | null
  tags: any
  recommendBusy?: boolean
}>()

const emit = defineEmits<{
  status: [msg: string]
  refreshed: []
  recommend: []
}>()

const recommendations = computed(() => props.tags?.recommendations)
const active = computed(() => props.tags?.active || [])

const catalog = ref<CatalogTag[]>([])
const catalogLoaded = ref(false)
const catalogBusy = ref(false)
const showPicker = ref(false)
const showCreate = ref(false)
const search = ref('')
const selectedIds = ref<number[]>([])
const addBusy = ref(false)

const createName = ref('')
const createDesc = ref('')
const createBusy = ref(false)

const selectedAddNames = ref<Set<string>>(new Set())
const selectedRemoveNames = ref<Set<string>>(new Set())
const confirmBusy = ref(false)

const activeIds = computed(() => new Set(active.value.map((t: any) => t.id as number)))

/** 词表 + 已挂标签名，用于判断推荐是否可直接确认 */
const knownTagNames = computed(() => {
  const names = new Set<string>()
  for (const t of catalog.value) {
    if (t.name) names.add(t.name)
  }
  for (const t of active.value) {
    if (t?.name) names.add(t.name)
  }
  return names
})

function isUnknownAddName(name?: string | null) {
  const n = (name || '').trim()
  if (!n) return false
  return !knownTagNames.value.has(n)
}

const unknownSelectedAdds = computed(() =>
  [...selectedAddNames.value].filter((n) => isUnknownAddName(n)),
)

const filteredCatalog = computed(() => {
  const q = search.value.trim().toLowerCase()
  return catalog.value.filter((t) => {
    if (activeIds.value.has(t.id)) return false
    if (!q) return true
    return (
      t.name.toLowerCase().includes(q) ||
      (t.description || '').toLowerCase().includes(q)
    )
  })
})

watch(
  recommendations,
  async (rec) => {
    if (!rec) {
      selectedAddNames.value = new Set()
      selectedRemoveNames.value = new Set()
      return
    }
    selectedAddNames.value = new Set(
      (rec.add || []).map((a: any) => a.tag_name || a.name).filter(Boolean),
    )
    selectedRemoveNames.value = new Set(
      (rec.remove || []).map((a: any) => a.tag_name || a.name).filter(Boolean),
    )
    if (!catalogLoaded.value) await loadCatalog()
  },
  { immediate: true },
)

async function loadCatalog() {
  catalogBusy.value = true
  try {
    const data = await props.api('/sidebar/tags/catalog')
    catalog.value = data?.items || []
    catalogLoaded.value = true
  } catch (e: any) {
    emit('status', e?.message || '加载词表失败')
  } finally {
    catalogBusy.value = false
  }
}

async function openPicker() {
  showCreate.value = false
  showPicker.value = true
  selectedIds.value = []
  search.value = ''
  if (!catalogLoaded.value) await loadCatalog()
}

function toggleSelect(id: number) {
  const i = selectedIds.value.indexOf(id)
  if (i >= 0) selectedIds.value.splice(i, 1)
  else selectedIds.value.push(id)
}

async function addSelected() {
  if (!props.customerId || !selectedIds.value.length) return
  addBusy.value = true
  try {
    for (const tagId of selectedIds.value) {
      await props.api('/sidebar/tags', {
        method: 'POST',
        body: JSON.stringify({ customer_id: props.customerId, tag_id: tagId }),
      })
    }
    emit('status', `已添加 ${selectedIds.value.length} 个标签`)
    selectedIds.value = []
    showPicker.value = false
    emit('refreshed')
  } catch (e: any) {
    emit('status', e?.message || '添加失败')
  } finally {
    addBusy.value = false
  }
}

async function createAndAttach() {
  if (!props.customerId) return
  const name = createName.value.trim()
  if (!name) {
    emit('status', '请填写标签名')
    return
  }
  createBusy.value = true
  try {
    const data = await props.api('/sidebar/tags/custom', {
      method: 'POST',
      body: JSON.stringify({
        customer_id: props.customerId,
        name,
        description: createDesc.value.trim() || undefined,
      }),
    })
    emit(
      'status',
      data?.created_def
        ? `已新建并添加「${data.name}」`
        : data?.attached
          ? `已添加「${data.name}」`
          : `「${data?.name || name}」已在客户上`,
    )
    createName.value = ''
    createDesc.value = ''
    showCreate.value = false
    catalogLoaded.value = false
    emit('refreshed')
  } catch (e: any) {
    emit('status', e?.message || '新建失败')
  } finally {
    createBusy.value = false
  }
}

async function removeTag(t: any) {
  if (!window.confirm(`确定移除标签「${t.name}」？`)) return
  try {
    await props.api(`/sidebar/tags/${t.customer_tag_id}`, { method: 'DELETE' })
    emit('status', `已移除「${t.name}」`)
    emit('refreshed')
  } catch (e: any) {
    emit('status', e?.message || '移除失败')
  }
}

function sourceLabel(source?: string) {
  if (source === 'ai') return 'AI'
  return '人工'
}

function toggleAddName(name: string) {
  const next = new Set(selectedAddNames.value)
  if (next.has(name)) next.delete(name)
  else next.add(name)
  selectedAddNames.value = next
}

function toggleRemoveName(name: string) {
  const next = new Set(selectedRemoveNames.value)
  if (next.has(name)) next.delete(name)
  else next.add(name)
  selectedRemoveNames.value = next
}

async function confirmSelected() {
  const rec = recommendations.value
  if (!rec?.suggestion_id) return
  const addNames = [...selectedAddNames.value]
  const removeNames = [...selectedRemoveNames.value]
  if (!addNames.length && !removeNames.length) {
    emit('status', '请至少勾选一项，或点忽略')
    return
  }
  confirmBusy.value = true
  try {
    if (!catalogLoaded.value) await loadCatalog()
    const nameToId = new Map(catalog.value.map((t) => [t.name, t.id]))
    // also map from active tags
    for (const t of active.value) {
      if (t.name && t.id) nameToId.set(t.name, t.id)
    }
    const add_tag_ids = addNames
      .map((n) => nameToId.get(n))
      .filter((id): id is number => typeof id === 'number')
    const skipped = addNames.filter((n) => !nameToId.has(n))

    if (!add_tag_ids.length && !removeNames.length && skipped.length) {
      emit(
        'status',
        `所选添加项均不在词表（${skipped.join('、')}）。请先「新建」词条，或取消勾选后忽略。`,
      )
      return
    }

    await props.api('/sidebar/tags/recommend/confirm', {
      method: 'POST',
      body: JSON.stringify({
        suggestion_id: rec.suggestion_id,
        apply_add: add_tag_ids.length > 0,
        apply_remove: removeNames.length > 0,
        add_tag_ids: add_tag_ids.length ? add_tag_ids : [],
        remove_tag_names: removeNames.length ? removeNames : [],
      }),
    })
    emit(
      'status',
      skipped.length
        ? `已确认可写入项；已跳过不在词表：${skipped.join('、')}（可先新建）`
        : '已确认所选标签推荐',
    )
    emit('refreshed')
  } catch (e: any) {
    emit('status', e?.message || '确认失败')
  } finally {
    confirmBusy.value = false
  }
}

async function ignoreRecommend() {
  const rec = recommendations.value
  if (!rec?.suggestion_id) return
  if (!window.confirm('忽略后推荐草稿将消失，已挂标签不变。确定忽略？')) return
  confirmBusy.value = true
  try {
    await props.api('/sidebar/tags/recommend/confirm', {
      method: 'POST',
      body: JSON.stringify({
        suggestion_id: rec.suggestion_id,
        apply_add: false,
        apply_remove: false,
      }),
    })
    emit('status', '已忽略标签推荐')
    emit('refreshed')
  } catch (e: any) {
    emit('status', e?.message || '忽略失败')
  } finally {
    confirmBusy.value = false
  }
}

watch(
  () => props.customerId,
  () => {
    catalogLoaded.value = false
    showPicker.value = false
    showCreate.value = false
  },
)
</script>

<template>
  <section class="panel">
    <div class="title-row">
      <h2>标签 <em class="ai-badge">AI 建议</em></h2>
      <button type="button" :disabled="!customerId" @click="openPicker">添加标签</button>
      <button
        type="button"
        :disabled="!customerId"
        @click="showCreate = !showCreate; showPicker = false"
      >
        新建
      </button>
      <button
        type="button"
        class="primary"
        :disabled="!customerId || recommendBusy"
        @click="emit('recommend')"
      >
        {{ recommendBusy ? '推荐中…' : '生成推荐' }}
      </button>
    </div>

    <!-- 已挂 -->
    <h3>已挂标签</h3>
    <ul v-if="active.length" class="list">
      <li v-for="t in active" :key="t.customer_tag_id">
        <div class="tag-main">
          <div class="name-row">
            <strong>{{ t.name }}</strong>
            <span class="src" :class="t.source === 'ai' ? 'ai' : 'manual'">
              {{ sourceLabel(t.source) }}
            </span>
          </div>
          <details v-if="t.sop_text || t.description" class="sop">
            <summary>说明 / SOP</summary>
            <p class="muted">{{ t.description }}</p>
            <p class="muted">{{ t.sop_text }}</p>
          </details>
        </div>
        <button type="button" @click="removeTag(t)">移除</button>
      </li>
    </ul>
    <p v-else class="empty-hint">暂无已挂标签。可从词表添加，或生成 AI 推荐后确认。</p>

    <!-- 点选添加 -->
    <div v-if="showPicker" class="field-card picker">
      <div class="title-row">
        <strong>从词表添加</strong>
        <button type="button" class="ghost" @click="showPicker = false">关闭</button>
      </div>
      <input v-model="search" class="search" placeholder="搜索标签名…" />
      <p v-if="catalogBusy" class="muted">加载词表中…</p>
      <p v-else-if="!filteredCatalog.length" class="empty-hint">
        {{ catalog.length ? '没有可添加的标签（可能都已挂上）' : '词表为空，可点「新建」自定义。' }}
      </p>
      <ul v-else class="pick-list">
        <li v-for="t in filteredCatalog" :key="t.id">
          <label>
            <input
              type="checkbox"
              :checked="selectedIds.includes(t.id)"
              @change="toggleSelect(t.id)"
            />
            <span>{{ t.name }}</span>
          </label>
          <span v-if="t.description" class="muted tiny">{{ t.description }}</span>
        </li>
      </ul>
      <div class="actions">
        <button
          type="button"
          class="primary"
          :disabled="!selectedIds.length || addBusy"
          @click="addSelected"
        >
          {{ addBusy ? '添加中…' : `添加所选（${selectedIds.length}）` }}
        </button>
      </div>
    </div>

    <!-- 自定义新建 -->
    <div v-if="showCreate" class="field-card create">
      <div class="title-row">
        <strong>新建并添加</strong>
        <button type="button" class="ghost" @click="showCreate = false">关闭</button>
      </div>
      <p class="muted">同名已存在则直接挂到客户；全局 SOP 请在后台完善。</p>
      <label class="field">
        标签名
        <input v-model="createName" maxlength="64" placeholder="例如：价格敏感" />
      </label>
      <label class="field">
        说明（可选）
        <input v-model="createDesc" maxlength="255" placeholder="简短说明" />
      </label>
      <div class="actions">
        <button
          type="button"
          class="primary"
          :disabled="createBusy || !createName.trim()"
          @click="createAndAttach"
        >
          {{ createBusy ? '提交中…' : '新建并添加' }}
        </button>
      </div>
    </div>

    <!-- AI 推荐 -->
    <h3>AI 推荐草稿</h3>
    <div v-if="recommendations" class="field-card">
      <p class="muted">确认前不会写入正式标签；可勾选部分条目。</p>
      <div v-if="(recommendations.add || []).length" class="block">
        <strong>建议添加</strong>
        <label
          v-for="(a, i) in recommendations.add"
          :key="'a' + i"
          class="check-row"
        >
          <input
            type="checkbox"
            :checked="selectedAddNames.has(a.tag_name || a.name)"
            @change="toggleAddName(a.tag_name || a.name)"
          />
          <span class="chip">+ {{ a.tag_name || a.name }}</span>
          <span
            v-if="isUnknownAddName(a.tag_name || a.name)"
            class="warn-chip"
            title="确认时会跳过；可先点「新建」写入词表"
          >
            不在词表 · 需先新建或跳过
          </span>
          <span class="muted">{{ a.reason }}</span>
        </label>
        <p v-if="unknownSelectedAdds.length" class="warn-note">
          已勾选但不在词表：{{ unknownSelectedAdds.join('、') }}。确认时将跳过这些项；可先「新建」再确认。
        </p>
      </div>
      <div v-if="(recommendations.remove || []).length" class="block">
        <strong>建议移除</strong>
        <label
          v-for="(a, i) in recommendations.remove"
          :key="'r' + i"
          class="check-row"
        >
          <input
            type="checkbox"
            :checked="selectedRemoveNames.has(a.tag_name || a.name)"
            @change="toggleRemoveName(a.tag_name || a.name)"
          />
          <span class="chip danger">- {{ a.tag_name || a.name }}</span>
          <span class="muted">{{ a.reason }}</span>
        </label>
      </div>
      <p
        v-if="!(recommendations.add || []).length && !(recommendations.remove || []).length"
        class="muted"
      >
        推荐结果为空。
      </p>
      <div class="actions">
        <button
          type="button"
          class="primary"
          :disabled="confirmBusy"
          @click="confirmSelected"
        >
          {{ confirmBusy ? '处理中…' : '确认所选' }}
        </button>
        <button type="button" :disabled="confirmBusy" @click="ignoreRecommend">忽略</button>
      </div>
    </div>
    <p v-else class="empty-hint">暂无 AI 标签推荐。可点「生成推荐」。</p>
  </section>
</template>
