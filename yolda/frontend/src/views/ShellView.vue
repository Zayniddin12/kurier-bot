<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { useLiveStore, onLive } from '@/stores/live'
import { useRestaurantsStore } from '@/stores/restaurants'
import { useAlertsStore } from '@/stores/alerts'
import { hm } from '@/utils/format'
import { useDrawer } from '@/utils/drawer'
import { moneyS } from '@/utils/format'
import PeriodPicker from '@/components/PeriodPicker.vue'
import RestaurantPicker from '@/components/RestaurantPicker.vue'
import CourierDrawer from '@/components/drawers/CourierDrawer.vue'
import OrderDrawer from '@/components/drawers/OrderDrawer.vue'
import RestaurantDrawer from '@/components/drawers/RestaurantDrawer.vue'

const route = useRoute(), router = useRouter()
const auth = useAuthStore(), ui = useUiStore(), live = useLiveStore(), rs = useRestaurantsStore(), alerts = useAlertsStore()
const drawer = useDrawer()
const now = ref(new Date())
let tick: any
const menu = ref(false)

const nav = computed(() => [
  { to: '/', icon: 'gauge', label: 'Umumiy holat' },
  { to: '/map', icon: 'map', label: 'Jonli xarita' },
  ...(auth.isStaff ? [] : [{ to: '/couriers', icon: 'bike', label: 'Kuryerlar' }]),
  { to: '/orders', icon: 'orders', label: 'Buyurtmalar' },
  { to: '/restaurants', icon: 'store', label: 'Restoranlar' },
  { sep: true },
  { to: '/analytics', icon: 'chart', label: 'Analitika' },
  { to: '/alerts', icon: 'bell', label: 'Ogohlantirishlar', badge: true },
] as any[])

// restoran tanlovi <-> URL ?r=
function syncFromRoute() {
  if (auth.isStaff && auth.user?.restaurant_id) { ui.restaurantId = auth.user.restaurant_id; return }
  const r = route.query.r
  ui.restaurantId = r ? Number(r) : null
}
watch(() => route.query.r, syncFromRoute)
watch(() => ui.restaurantId, (v) => {
  if ((route.query.r ? Number(route.query.r) : null) !== v) {
    const q = { ...route.query }
    if (v) q.r = String(v); else delete q.r
    router.replace({ query: q })
  }
  alerts.load().catch(() => {})
})
watch(() => route.fullPath, () => { ui.sidebarOpen = false })

let alertTimer: any
function reloadAlerts() { clearTimeout(alertTimer); alertTimer = setTimeout(() => alerts.load().catch(() => {}), 300) }

onMounted(async () => {
  syncFromRoute()
  tick = setInterval(() => (now.value = new Date()), 15000)
  live.connect()
  await Promise.allSettled([rs.load(), alerts.load()])
})
onUnmounted(() => { clearInterval(tick); live.disconnect() })

// Global toastlar va store yangilanishlari
onLive('order.created', (o) => {
  ui.toast(`Yangi buyurtma #${o.id} · ${o.restaurant?.name ?? o.restaurant_name ?? ''} · ${moneyS(o.total)} · ${o.pay_method}`, 'var(--brand)')
  ui.beep()
})
onLive('order.updated', (o) => {
  if (o.status === 'cancelled') ui.toast(`Buyurtma #${o.id} bekor qilindi${o.pay_status === 'refunded' ? " · to'lov mijozga qaytarildi" : ''}`, 'var(--red)')
  if (o.pay_status === 'failed') ui.toast(`Buyurtma #${o.id}: to'lov o'tmadi`, 'var(--red)')
})
onLive('issue.opened', (i) => ui.toast(`Muammo${i.order_id ? ' #' + i.order_id : ''}: ${i.text ?? i.kind}`, 'var(--red)'))
onLive('restaurant.updated', (r) => rs.patch(r))
onLive('alerts.changed', reloadAlerts)

const meta = computed(() => route.meta as any)
const periodLabel = computed(() => '')
const logout = () => { auth.logout(); live.disconnect(); router.replace('/login') }
const time = computed(() => hm(now.value))
</script>

<template>
  <div class="shell" :class="{ open: ui.sidebarOpen }">
    <div class="scrim" @click="ui.sidebarOpen = false" />
    <aside class="side">
      <div class="brand">
        <span class="logo"><Icon name="bike" :size="20" /></span>
        <div><b>Yo'lda</b><small>Operator paneli</small></div>
      </div>
      <nav>
        <template v-for="(n, i) in nav" :key="i">
          <hr v-if="n.sep" />
          <RouterLink v-else :to="{ path: n.to, query: ui.restaurantId && !auth.isStaff ? { r: ui.restaurantId } : {} }" class="nl" :class="{ act: n.to === '/' ? route.path === '/' : route.path.startsWith(n.to) }">
            <Icon :name="n.icon" /><span>{{ n.label }}</span>
            <span class="sp" /><Badge v-if="n.badge" :n="alerts.count" />
          </RouterLink>
        </template>
      </nav>
      <div class="me" @click="menu = !menu">
        <Avatar :seed="auth.user?.id || 3" :size="34" />
        <div class="mi"><b>{{ auth.user?.full_name }}</b><small>{{ auth.roleLabel }}</small></div>
        <div v-if="menu" class="menu"><button @click.stop="logout"><Icon name="logout" :size="16" /> Chiqish</button></div>
      </div>
    </aside>

    <div class="main">
      <header class="top">
        <IconBtn class="burger" icon="menu" title="Menyu" @click="ui.sidebarOpen = true" />
        <div class="ttl"><h1>{{ meta.title }}</h1><p>{{ meta.sub }}</p></div>
        <div class="sp" />
        <PeriodPicker v-if="meta.period" />
        <RestaurantPicker />
        <span class="clock"><i :class="{ off: !live.connected }" /><span class="ct">{{ live.connected ? time + ' · jonli' : 'ulanish yo\'q' }}</span></span>
        <IconBtn :icon="ui.theme === 'dark' ? 'sun' : 'moon'" title="Mavzu" @click="ui.toggleTheme()" />
      </header>
      <main class="content" :class="{ flush: meta.flush }"><RouterView :key="route.path" /></main>
    </div>

    <CourierDrawer v-if="drawer.current.value?.kind === 'courier'" :id="drawer.current.value.id" @close="drawer.close" />
    <OrderDrawer v-else-if="drawer.current.value?.kind === 'order'" :id="drawer.current.value.id" @close="drawer.close" />
    <RestaurantDrawer v-else-if="drawer.current.value?.kind === 'restaurant'" :id="drawer.current.value.id" @close="drawer.close" />
  </div>
</template>

<style scoped>
.shell{display:grid;grid-template-columns:236px 1fr;height:100%;overflow:hidden}
.side{background:var(--side);color:var(--side-ink);padding:18px 12px 14px;display:flex;flex-direction:column;gap:18px;padding-top:max(18px,env(safe-area-inset-top))}
.brand{display:flex;align-items:center;gap:10px;padding:0 6px}
.logo{width:34px;height:34px;border-radius:10px;background:var(--brand);color:#16201A;display:flex;align-items:center;justify-content:center}
.brand b{display:block;font-size:19px;font-weight:800;color:#fff;line-height:1.1}.brand small{font-size:11px;color:var(--side-muted)}
nav{flex:1;display:flex;flex-direction:column;gap:2px;overflow:auto}
nav hr{border:0;border-top:1px solid var(--side-active);margin:8px 0;width:100%}
.nl{position:relative;display:flex;align-items:center;gap:10px;padding:9px 10px;border-radius:9px;font-size:14px;font-weight:500;color:var(--side-ink)}
.nl:hover,.nl.act{background:var(--side-active)}
.nl.act{color:#fff}.nl.act::before{content:'';position:absolute;left:-12px;top:8px;bottom:8px;width:3px;border-radius:0 3px 3px 0;background:var(--brand)}
.me{position:relative;border-top:1px solid var(--side-active);padding-top:12px;display:flex;gap:10px;align-items:center;cursor:pointer}
.mi b{display:block;font-size:13px;color:#fff;font-weight:600}.mi small{font-size:11.5px;color:var(--side-muted)}
.menu{position:absolute;bottom:56px;left:0;right:0;background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:4px;box-shadow:var(--shadow)}
.menu button{width:100%;border:0;background:transparent;display:flex;gap:8px;align-items:center;padding:8px 10px;border-radius:7px;color:var(--ink);font-weight:600}
.menu button:hover{background:var(--surface-2)}
.main{display:flex;flex-direction:column;min-width:0;height:100%}
.top{height:64px;flex:none;background:var(--surface);border-bottom:1px solid var(--line);display:flex;align-items:center;gap:10px;padding:0 20px;padding-top:env(safe-area-inset-top);box-sizing:content-box}
.ttl h1{font-size:19px;font-weight:700;line-height:1.2}.ttl p{font-size:12.5px;color:var(--muted)}
.burger{display:none}
.clock{display:flex;align-items:center;gap:8px;font-size:12.5px;color:var(--muted);white-space:nowrap}
.clock i{width:8px;height:8px;border-radius:50%;background:var(--teal);animation:pulse 2s infinite}.clock i.off{background:var(--red);animation:none}
.content{flex:1;overflow:auto;position:relative;z-index:0;padding-bottom:env(safe-area-inset-bottom)}
.content.flush{overflow:hidden}
.scrim{display:none}
@media (max-width:860px){
  .shell{grid-template-columns:1fr}
  .side{position:fixed;left:0;top:0;bottom:0;width:250px;z-index:80;transform:translateX(-100%);transition:transform .25s}
  .open .side{transform:none}
  .open .scrim{display:block;position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:70}
  .burger{display:inline-flex}.ttl p,.ct{display:none}
  .top{padding:0 12px;gap:8px}
}
@media (max-width:520px){.ttl h1{font-size:16px}.clock{display:none}}
</style>
