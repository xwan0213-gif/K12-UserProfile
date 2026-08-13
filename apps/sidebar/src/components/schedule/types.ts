export type Priority = 'high' | 'medium' | 'low'

export type ScheduleItem = {
  id: number
  title: string
  start_at?: string | null
  end_at?: string | null
  priority?: string
  sync_state?: string
  status?: string
  remark?: string | null
  source?: string
}

export type ScheduleDraft = {
  suggestion_id: number
  title?: string
  time_text?: string
  start_at?: string | null
  priority?: string
  source_quote?: string
  predictive_tip?: string
}

export type ScheduleEdits = {
  title?: string
  start_at?: string | null
  priority?: Priority
  remark?: string | null
}

export type RemindPref = {
  weak_tip?: boolean
  strong_notify?: boolean
  quiet_hours?: string[]
}

/** ISO / API 时间 → datetime-local 值 */
export function toDatetimeLocal(iso?: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) {
    const raw = iso.replace('Z', '').replace(' ', 'T').slice(0, 16)
    return raw
  }
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** datetime-local → 后端 ISO（无时区，与现有 parse 兼容） */
export function fromDatetimeLocal(local: string): string | null {
  const v = local.trim()
  if (!v) return null
  return v.length === 16 ? `${v}:00` : v
}

export function formatWhen(iso?: string | null): string {
  if (!iso) return '时间待定'
  return iso.replace('T', ' ').replace('Z', '').slice(0, 16)
}

export function priorityLabel(p?: string) {
  if (p === 'high') return '高'
  if (p === 'low') return '低'
  return '中'
}

export function syncLabel(s?: string) {
  if (s === 'synced') return '已同步企微日历'
  if (s === 'failed') return '日历同步失败（站内保留）'
  if (s === 'pending') return '同步中'
  return '仅站内'
}
