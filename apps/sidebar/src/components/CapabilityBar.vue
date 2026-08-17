<script setup lang="ts">
defineProps<{
  flags: {
    mockWecom?: boolean
    mockLlm?: boolean
    llmProvider?: string
    asr?: string
    calendar?: string
    calendarHint?: string
  }
}>()
</script>

<template>
  <div
    class="mb-2.5 flex flex-wrap items-center gap-x-1.5 gap-y-1 rounded-control bg-stone-100 px-2.5 py-1.5 text-xs text-muted"
    title="当前能力与降级说明（诚实展示）"
  >
    <span
      class="h-[7px] w-[7px] shrink-0 rounded-full"
      :class="flags.mockWecom ? 'bg-fjord' : 'bg-green-600'"
      :title="flags.mockWecom ? '企微 Mock' : '企微实连'"
    />
    <span>企微 {{ flags.mockWecom ? 'Mock' : '实连' }}</span>
    <span class="opacity-45">·</span>
    <span>LLM {{ flags.mockLlm ? 'Fake' : (flags.llmProvider || 'cloud') }}</span>
    <span class="opacity-45">·</span>
    <span>ASR {{ flags.asr || 'Fake' }}</span>
    <span class="opacity-45">·</span>
    <span
      :class="flags.calendar !== '可同步' ? 'text-signal' : ''"
      :title="flags.calendarHint || ''"
    >
      日历 {{ flags.calendar || '降级' }}
    </span>
  </div>
</template>
