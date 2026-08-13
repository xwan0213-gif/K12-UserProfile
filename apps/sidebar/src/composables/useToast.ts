import { readonly, shallowRef } from 'vue'

export type ToastKind = 'info' | 'ok' | 'warn' | 'err'

export type ToastItem = {
  id: number
  message: string
  kind: ToastKind
}

const toasts = shallowRef<ToastItem[]>([])
let seq = 0

export function useToast() {
  function dismiss(id: number) {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  function push(message: string, kind: ToastKind = 'info', ms = 3200) {
    const text = (message || '').trim()
    if (!text) return
    const id = ++seq
    toasts.value = [...toasts.value.slice(-4), { id, message: text, kind }]
    window.setTimeout(() => dismiss(id), ms)
  }

  return {
    toasts: readonly(toasts),
    push,
    dismiss,
  }
}
