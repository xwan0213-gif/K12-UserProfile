/** 管理后台数据分析展示格式 */

export function formatPercent(rate: number | null | undefined, digits = 0): string {
  if (rate == null || Number.isNaN(Number(rate))) return '暂无'
  return `${(Number(rate) * 100).toFixed(digits)}%`
}

export function formatWowDelta(delta: number | null | undefined): string {
  if (delta == null || Number.isNaN(Number(delta))) return '上期无对比'
  const pct = Number(delta) * 100
  const sign = pct > 0 ? '+' : ''
  return `${sign}${pct.toFixed(0)} 百分点`
}

export function wowTone(delta: number | null | undefined): 'up' | 'down' | 'flat' {
  if (delta == null || Number.isNaN(Number(delta))) return 'flat'
  if (delta > 0.005) return 'up'
  if (delta < -0.005) return 'down'
  return 'flat'
}

export type AdoptionRow = {
  name?: string
  day?: string | null
  impressions?: number
  copy?: number
  adopt?: number
  edit_adopt?: number
  reject?: number
  tag_confirm?: number
  tag_reject?: number
  adoption_rate?: number | null
}

/** 从采纳明细汇总一句话结论 */
export function summarizeAdoption(items: AdoptionRow[]) {
  if (!items.length) {
    return {
      rate: null as number | null,
      useful: 0,
      reject: 0,
      impressions: 0,
      copy: 0,
      topName: null as string | null,
    }
  }
  let useful = 0
  let reject = 0
  let impressions = 0
  let copy = 0
  let topName: string | null = null
  let topScore = -1
  for (const row of items) {
    const u = (row.adopt || 0) + (row.edit_adopt || 0)
    const r = row.reject || 0
    useful += u
    reject += r
    impressions += row.impressions || 0
    copy += row.copy || 0
    const score = u + (row.copy || 0)
    if (score > topScore) {
      topScore = score
      topName = row.name || null
    }
  }
  const denom = useful + reject
  return {
    rate: denom ? useful / denom : null,
    useful,
    reject,
    impressions,
    copy,
    topName,
  }
}
