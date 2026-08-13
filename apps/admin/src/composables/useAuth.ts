import { computed, readonly, ref, shallowRef } from 'vue'
import { createApi } from './useApi'

export type AdminRole = 'admin' | 'regional' | 'advisor'

export type AdminUser = {
  id: number
  name: string
  role: AdminRole | string
  org_id?: number | null
}

const TOKEN_KEY = 'admin_token'

const token = ref(localStorage.getItem(TOKEN_KEY) || '')
const me = shallowRef<AdminUser | null>(null)
const status = ref(token.value ? '已恢复本地登录' : '未登录')

const api = createApi(() => token.value)

const loggedIn = computed(() => !!token.value)
const role = computed(() => (me.value?.role || '') as string)

export function useAuth() {
  async function login(loginName: string, password: string) {
    status.value = '登录中…'
    const data = await api('/auth/admin/login', {
      method: 'POST',
      body: JSON.stringify({ login_name: loginName, password }),
    })
    token.value = data.access_token
    localStorage.setItem(TOKEN_KEY, token.value)
    me.value = data.user
    status.value = `已登录：${data.user.name}（${roleLabel(data.user.role)}）`
    return data.user as AdminUser
  }

  async function loadMe() {
    me.value = await api('/auth/me')
    if (me.value) {
      status.value = `已登录：${me.value.name}（${roleLabel(me.value.role)}）`
    }
    return me.value
  }

  function logout() {
    token.value = ''
    me.value = null
    localStorage.removeItem(TOKEN_KEY)
    status.value = '已退出'
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
    hasRole,
  }
}

export function roleLabel(role?: string) {
  if (role === 'admin') return '管理员'
  if (role === 'regional') return '区域主管'
  if (role === 'advisor') return '顾问'
  return role || '—'
}
