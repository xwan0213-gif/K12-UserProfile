import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '../composables/useAuth'
import { navForRole } from '../nav'
import AdminLayout from '../layouts/AdminLayout.vue'
import LoginView from '../views/LoginView.vue'
import DashboardView from '../views/DashboardView.vue'
import CustomersView from '../views/CustomersView.vue'
import CustomerDetailView from '../views/CustomerDetailView.vue'
import UsersView from '../views/UsersView.vue'
import OrdersView from '../views/OrdersView.vue'
import TagsView from '../views/TagsView.vue'
import ScriptsView from '../views/ScriptsView.vue'
import AiView from '../views/AiView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { public: true },
    },
    {
      path: '/',
      component: AdminLayout,
      children: [
        { path: '', name: 'dashboard', component: DashboardView },
        { path: 'customers', name: 'customers', component: CustomersView },
        {
          path: 'customers/:id',
          name: 'customer-detail',
          component: CustomerDetailView,
          meta: { roles: ['admin', 'regional', 'advisor'] },
        },
        {
          path: 'users',
          name: 'users',
          component: UsersView,
          meta: { roles: ['admin', 'regional'] },
        },
        { path: 'orders', name: 'orders', component: OrdersView },
        { path: 'tags', name: 'tags', component: TagsView },
        { path: 'scripts', name: 'scripts', component: ScriptsView },
        {
          path: 'ai',
          name: 'ai',
          component: AiView,
          meta: { roles: ['admin', 'regional'] },
        },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  const { loggedIn, loadMe, me, role, logout } = useAuth()

  if (to.meta.public) {
    if (loggedIn.value && to.name === 'login') return { name: 'dashboard' }
    return true
  }

  if (!loggedIn.value) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (!me.value) {
    try {
      await loadMe()
    } catch {
      logout()
      return { name: 'login', query: { redirect: to.fullPath } }
    }
  }

  const allowedRoles = to.meta.roles as string[] | undefined
  if (allowedRoles && !allowedRoles.includes(role.value)) {
    const first = navForRole(role.value)[0]
    return first ? first.to : { name: 'dashboard' }
  }

  return true
})

export default router
