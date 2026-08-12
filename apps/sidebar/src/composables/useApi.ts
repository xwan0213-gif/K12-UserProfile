/** Thin API facade — auth header + unified `{code,data}` unwrap. */

export type ApiFn = (path: string, init?: RequestInit) => Promise<any>

export function createApi(getToken: () => string, base = '/api/v1'): ApiFn {
  return async (path: string, init: RequestInit = {}) => {
    const headers: Record<string, string> = {
      ...(init.headers as Record<string, string> | undefined),
    }
    const token = getToken()
    if (token) headers.Authorization = `Bearer ${token}`
    if (init.body && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json'
    }
    const res = await fetch(`${base}${path}`, { ...init, headers })
    const json = await res.json()
    if (json.code !== 0) throw new Error(json.message || '请求失败')
    return json.data
  }
}
