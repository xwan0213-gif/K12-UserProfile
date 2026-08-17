/** Shared auth storage across admin (/admin) and sidebar (/) on same origin. */
export const TOKEN_KEY = 'k12_access_token'

export function readToken(): string {
  const current = localStorage.getItem(TOKEN_KEY) || ''
  if (current) return current
  // migrate legacy admin_token once
  const legacy = localStorage.getItem('admin_token') || ''
  if (legacy) {
    localStorage.setItem(TOKEN_KEY, legacy)
    localStorage.removeItem('admin_token')
    return legacy
  }
  return ''
}

export function writeToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

/** Consume one-time token from URL hash (#token=...) for cross-port handoff in dev. */
export function consumeHashToken(): string | null {
  const hash = window.location.hash || ''
  const m = hash.match(/(?:^|#|&)token=([^&]+)/)
  if (!m) return null
  const token = decodeURIComponent(m[1])
  const cleaned = hash
    .replace(/([#&]?token=)[^&]*/g, '')
    .replace(/^&/, '#')
    .replace(/^#&/, '#')
  history.replaceState(
    null,
    '',
    window.location.pathname + window.location.search + (cleaned === '#' ? '' : cleaned),
  )
  return token
}

/**
 * Resolve app home URL.
 * - Same origin (Docker nginx :8080): relative `/` or `/admin/` — localStorage already shared.
 * - Cross origin (Vite 5173↔5174): absolute URL + #token= handoff.
 */
function resolveAppHref(configured: string | undefined, sameOriginPath: string, token: string): string {
  const raw = (configured || '').trim()
  if (!raw || raw === '/' || raw === sameOriginPath) {
    return sameOriginPath
  }
  try {
    const target = new URL(raw, window.location.origin)
    if (target.origin === window.location.origin) {
      let path = target.pathname || sameOriginPath
      if (!path.endsWith('/')) path += '/'
      return path
    }
    const base = target.href.replace(/\/?$/, '/')
    return `${base}#token=${encodeURIComponent(token)}`
  } catch {
    return sameOriginPath
  }
}

export function sidebarUrl(): string {
  return (import.meta.env.VITE_SIDEBAR_URL as string | undefined) || ''
}

export function adminUrl(): string {
  return (import.meta.env.VITE_ADMIN_URL as string | undefined) || ''
}

export function goToSidebarWithToken(token: string) {
  writeToken(token)
  window.location.assign(resolveAppHref(sidebarUrl(), '/', token))
}

export function goToAdminWithToken(token: string) {
  writeToken(token)
  window.location.assign(resolveAppHref(adminUrl(), '/admin/', token))
}
