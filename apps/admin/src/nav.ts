import type { AdminRole } from './composables/useAuth'

export type NavItem = {
  to: string
  name: string
  label: string
  roles: AdminRole[]
}

/** 菜单按角色显隐（与 admin router require_roles 对齐） */
export const NAV_ITEMS: NavItem[] = [
  { to: '/', name: 'dashboard', label: '看板', roles: ['admin', 'regional', 'advisor'] },
  { to: '/customers', name: 'customers', label: '客户', roles: ['admin', 'regional', 'advisor'] },
  { to: '/users', name: 'users', label: '员工', roles: ['admin', 'regional'] },
  { to: '/orders', name: 'orders', label: '订单', roles: ['admin', 'regional', 'advisor'] },
  { to: '/tags', name: 'tags', label: '标签', roles: ['admin', 'regional', 'advisor'] },
  { to: '/scripts', name: 'scripts', label: '话术模板', roles: ['admin', 'regional', 'advisor'] },
  { to: '/ai', name: 'ai', label: 'AI 分析', roles: ['admin', 'regional'] },
]

export function navForRole(role: string): NavItem[] {
  return NAV_ITEMS.filter((item) => item.roles.includes(role as AdminRole))
}

export function canWriteScripts(role: string) {
  return role === 'admin' || role === 'regional'
}
