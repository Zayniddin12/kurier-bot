import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('@/views/LoginView.vue'), meta: { public: true } },
    {
      path: '/',
      component: () => import('@/views/ShellView.vue'),
      children: [
        { path: '', name: 'overview', component: () => import('@/views/OverviewView.vue'), meta: { title: 'Umumiy holat', sub: 'Bugungi ish jarayoni bir qarashda', period: true } },
        { path: 'map', component: () => import('@/views/MapView.vue'), meta: { title: 'Jonli xarita', sub: "Kuryerlarning hozirgi joylashuvi", flush: true } },
        { path: 'couriers', component: () => import('@/views/CouriersView.vue'), meta: { title: 'Kuryerlar', sub: "Ro'yxat, balans va ish holati", noStaff: true } },
        { path: 'orders', component: () => import('@/views/OrdersView.vue'), meta: { title: 'Buyurtmalar', sub: 'Kunlik, haftalik va oylik tarix' } },
        { path: 'restaurants', component: () => import('@/views/RestaurantsView.vue'), meta: { title: 'Restoranlar', sub: 'Ulangan hamkorlar' } },
        { path: 'analytics', component: () => import('@/views/AnalyticsView.vue'), meta: { title: 'Analitika', sub: "Ko'rsatkichlar dinamikasi" } },
        { path: 'alerts', component: () => import('@/views/AlertsView.vue'), meta: { title: 'Ogohlantirishlar', sub: "Operator e'tiborini talab qiladigan holatlar" } },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.public) return true
  if (!auth.token) return '/login'
  if (!auth.user) {
    try { await auth.fetchMe() } catch { auth.logout(); return '/login' }
  }
  if (to.meta.noStaff && auth.isStaff) return '/'
  return true
})
export default router
