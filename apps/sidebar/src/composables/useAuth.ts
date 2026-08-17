import { computed, readonly, ref, shallowRef } from 'vue'
import { createApi } from './useApi'
import {
  clearToken,
  consumeHashToken,
  goToAdminWithToken,
  readToken,
  writeToken,
} from '../lib/authStorage'

export type SidebarRole = 'admin' | 'regional' | 'advisor'

export type SidebarUser = {
  id: number
  name: string
  role: SidebarRole | string
  org_id?: number | null
}

const hashTok = typeof window !== 'undefined' ? consumeHashToken() : null
if (hashTok) writeToken(hashTok)

const token = ref(readToken())
const me = shallowRef<SidebarUser | null>(null)
const status = ref(token.value ? '已恢复本地登录' : '未登录')

const api = createApi(() => token.value)

const loggedIn = computed(() => !!token.value)
const role = computed(() => (me.value?.role || '') as string)

function isManager(r?: string) {
  return r === 'admin' || r === 'regional'
}

export function roleLabel(role?: string) {
  if (role === 'admin') return '管理员'
  if (role === 'regional') return '区域主管'
  if (role === 'advisor') return '顾问'
  return role || '—'
}

export function useAuth() {
  async function login(loginName: string, password: string) {
    status.value = '登录中…'
    const data = await api('/auth/admin/login', {
      method: 'POST',
      body: JSON.stringify({ login_name: loginName, password }),
    })
    token.value = data.access_token
    writeToken(token.value)
    me.value = data.user
    status.value = `已登录：${data.user.name}（${roleLabel(data.user.role)}）`
    return data.user as SidebarUser
  }

  async function loadMe() {
    me.value = await api('/auth/me')
    if (me.value) {
      status.value = `已登录：${me.value.name}（${roleLabel(me.value.role)}）`
    }
    return me.value
  }

  /** Returns true if redirected away (non-advisor). */
  function redirectManagerToAdmin(): boolean {
    if (token.value && isManager(me.value?.role)) {
      goToAdminWithToken(token.value)
      return true
    }
    return false
  }

  async function bootSession(): Promise<'login' | 'redirect' | 'workbench'> {
    if (!token.value) return 'login'
    try {
      const u = me.value || (await loadMe())
      if (isManager(u?.role)) {
        redirectManagerToAdmin()
        return 'redirect'
      }
      return 'workbench'
    } catch {
      token.value = ''
      clearToken()
      me.value = null
      status.value = '登录已失效'
      return 'login'
    }
  }

  function logout() {
    token.value = ''
    me.value = null
    clearToken()
    status.value = '已退出'
  }

  function setToken(next: string) {
    token.value = next
    writeToken(next)
  }

  function hasRole(...roles: string[]) {
    return roles.includes(role.value)
  }

  return {
    api,
    token: readonly(token),
    me,
    status,
    loggedIn,
    role,
    login,
    loadMe,
    logout,
    setToken,
    hasRole,
    bootSession,
    redirectManagerToAdmin,
  }
}
