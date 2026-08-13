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
    let json: any
    try {
      json = await res.json()
    } catch {
      throw new Error(res.status === 401 ? '未登录或登录已过期' : `请求失败（${res.status}）`)
    }
    if (json.code !== 0) {
      const err = new Error(json.message || '请求失败') as Error & { code?: number }
      err.code = json.code
      throw err
    }
    return json.data
  }
}
