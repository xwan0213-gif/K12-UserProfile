/** SSE observer: subscribe to customer channel, reconnect on drop. */

export type SseHandler = (event: string, data: string) => void | Promise<void>

export function createSseClient(opts: {
  apiBase?: string
  getToken: () => string
  getCustomerId: () => number | null
  onEvent: SseHandler
  onStatus?: (msg: string) => void
}) {
  const apiBase = opts.apiBase ?? '/api/v1'
  let abort: AbortController | null = null
  let reconnectTimer: number | null = null

  function disconnect() {
    abort?.abort()
    abort = null
    if (reconnectTimer != null) {
      window.clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  function connect() {
    const token = opts.getToken()
    const customerId = opts.getCustomerId()
    if (!token || !customerId) return
    disconnect()
    const ctrl = new AbortController()
    abort = ctrl
    void (async () => {
      try {
        const res = await fetch(
          `${apiBase}/sidebar/sse?customer_id=${customerId}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
              Accept: 'text/event-stream',
            },
            signal: ctrl.signal,
          },
        )
        if (!res.body) return
        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buf = ''
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buf += decoder.decode(value, { stream: true })
          const parts = buf.split('\n\n')
          buf = parts.pop() || ''
          for (const part of parts) {
            const ev = /event:\s*(\w+)/.exec(part)?.[1]
            const dataLine = part.split('\n').find((l) => l.startsWith('data:'))
            const data = dataLine ? dataLine.slice(5).trim() : ''
            if (ev) await opts.onEvent(ev, data)
          }
        }
      } catch (e: any) {
        if (e?.name === 'AbortError') return
        opts.onStatus?.('SSE 断开，重连中…')
        reconnectTimer = window.setTimeout(connect, 2000)
      }
    })()
  }

  return { connect, disconnect }
}
