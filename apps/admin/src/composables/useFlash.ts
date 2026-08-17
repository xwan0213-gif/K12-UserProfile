import { onUnmounted, reactive } from 'vue'

export type FlashKind = 'ok' | 'err' | 'info'

export function useFlash(ttlMs = 4000) {
  const state = reactive({
    message: '',
    kind: 'info' as FlashKind,
  })
  let timer: ReturnType<typeof setTimeout> | null = null

  function clear() {
    state.message = ''
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  function show(text: string, next: FlashKind = 'info') {
    state.message = text
    state.kind = next
    if (timer) clearTimeout(timer)
    if (ttlMs > 0 && text) {
      timer = setTimeout(() => {
        state.message = ''
        timer = null
      }, ttlMs)
    }
  }

  function ok(text: string) {
    show(text, 'ok')
  }

  function err(text: string) {
    show(text, 'err')
  }

  onUnmounted(() => {
    if (timer) clearTimeout(timer)
  })

  return {
    get message() {
      return state.message
    },
    get kind() {
      return state.kind
    },
    state,
    show,
    ok,
    err,
    clear,
  }
}
