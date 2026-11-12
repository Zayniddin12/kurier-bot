<script setup lang="ts">
import logo from "@/assets/logo.png"
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { useLiveStore, onLive } from '@/stores/live'
import { useRestaurantsStore } from '@/stores/restaurants'
import { useAlertsStore } from '@/stores/alerts'
import { useDrawer } from '@/utils/drawer'
import { moneyS } from '@/utils/format'
import PeriodPicker from '@/components/PeriodPicker.vue'
import RestaurantPicker from '@/components/RestaurantPicker.vue'
import CourierDrawer from '@/components/drawers/CourierDrawer.vue'
import OrderDrawer from '@/components/drawers/OrderDrawer.vue'

const route = useRoute(), router = useRouter()
const auth = useAuthStore(), ui = useUiStore(), live = useLiveStore(), rs = useRestaurantsStore(), alerts = useAlertsStore()
const drawer = useDrawer()

const nav = computed(() => [
  { to: '/', icon: 'gauge', label: 'Umumiy holat' },
  { to: '/map', icon: 'map', label: 'Jonli xarita' },
  ...(auth.isStaff ? [] : [{ to: '/couriers', icon: 'bike', label: 'Kuryerlar' }]),
  ...(auth.isStaff ? [] : [{ to: '/operator', icon: 'headset', label: 'Operator navbati' }]),
  { to: '/orders', icon: 'orders', label: 'Buyurtmalar' },
  { to: '/restaurants', icon: 'store', label: 'Restoranlar' },
  { to: '/payments', icon: 'dollar', label: "Onlayn to'lovlar" },
  ...(auth.isStaff ? [] : [
    { head: 'Moliya' },
    { to: '/finance/couriers', icon: 'truck', label: 'Deliverlar' },
    { to: '/finance/vendors', icon: 'wallet', label: 'Vendorlar' },
  ]),
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
  live.connect()
  await Promise.allSettled([rs.load(), alerts.load()])
})
onUnmounted(() => { live.disconnect() })

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
const logout = () => { auth.logout(); live.disconnect(); router.replace('/login') }
</script>

<template>
  <div class="shell" :class="{ open: ui.sidebarOpen }">
    <div class="scrim" @click="ui.sidebarOpen = false" />
    <aside class="side">
      <div class="brand">
        <img class="logo" :src="logo" alt="Tez-yetkaz" />
        <span class="sp" />
        <Icon name="pushpin" :size="16" class="pinic" />
      </div>
      <nav>
        <template v-for="(n, i) in nav" :key="i">
          <hr v-if="n.sep" />
          <div v-else-if="n.head" class="nh">{{ n.head }}</div>
          <RouterLink v-else :to="{ path: n.to, query: ui.restaurantId && !auth.isStaff ? { r: ui.restaurantId } : {} }" class="nl" :class="{ act: n.to === '/' ? route.path === '/' : route.path.startsWith(n.to) }">
            <Icon :name="n.icon" :size="19" /><span>{{ n.label }}</span>
            <span class="sp" /><Badge v-if="n.badge" :n="alerts.count" />
          </RouterLink>
        </template>
      </nav>
      <div class="me">
        <div class="mrow">
          <span class="av">{{ (auth.user?.full_name || '?').trim().charAt(0).toUpperCase() }}</span>
          <div class="mi"><b>{{ auth.user?.full_name }}</b><small>{{ auth.roleLabel }}</small></div>
        </div>
        <button class="out" @click="logout">Chiqish</button>
      </div>
    </aside>

    <div class="main">
      <header class="top">
        <IconBtn class="burger" icon="menu" title="Menyu" @click="ui.sidebarOpen = true" />
        <h1>{{ meta.title }}</h1>
        <span class="live" :class="{ off: !live.connected }"><i />{{ live.connected ? 'online' : 'offline' }}</span>
        <div id="hdr-slot" class="slot" />
        <div class="sp" />
        <PeriodPicker v-if="meta.period" />
        <RestaurantPicker />
        <IconBtn :icon="ui.theme === 'dark' ? 'sun' : 'moon'" title="Mavzu" @click="ui.toggleTheme()" />
        <RouterLink to="/alerts" class="bell" title="Ogohlantirishlar"><Icon name="bell" :size="16" /><b v-if="alerts.count">{{ alerts.count }}</b></RouterLink>
      </header>
      <main class="content" :class="{ flush: meta.flush }"><RouterView :key="route.path" /></main>
    </div>

    <CourierDrawer v-if="drawer.current.value?.kind === 'courier'" :id="drawer.current.value.id" @close="drawer.close" />
    <OrderDrawer v-else-if="drawer.current.value?.kind === 'order'" :id="drawer.current.value.id" @close="drawer.close" />
  </div>
</template>

<style scoped>
.shell{display:grid;grid-template-columns:218px 1fr;height:100%;overflow:hidden}
.side{background:var(--side);color:var(--side-ink);display:flex;flex-direction:column;padding-top:env(safe-area-inset-top)}
.brand{height:58px;flex:none;display:flex;align-items:center;gap:8px;padding:0 20px 0 10px;border-bottom:1px solid var(--side-line);box-sizing:border-box}
.logo{width:109px;height:auto;display:block}
.pinic{color:var(--brand);transform:rotate(35deg)}
nav{flex:1;display:flex;flex-direction:column;gap:4px;overflow:auto;padding:8px 8px 8px 4px}
nav .nh{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--side-muted);padding:12px 12px 4px}
nav hr{border:0;border-top:1px solid var(--side-line);margin:6px 0;width:100%}
.nl{position:relative;display:flex;align-items:center;gap:11px;height:40px;padding:0 10px 0 13px;border-radius:8px;font-size:15px;font-weight:500;color:var(--side-ink);flex:none}
.nl:hover{background:rgba(255,255,255,.06)}
.nl.act{background:var(--side-active);color:#fff;font-weight:600}.nl.act::before{content:'';position:absolute;left:-4px;top:2px;bottom:2px;width:4px;border-radius:0 3px 3px 0;background:var(--brand)}
.me{border-top:1px solid var(--side-line);padding:14px 6px 8px;display:flex;flex-direction:column;gap:12px}
.mrow{display:flex;gap:9px;align-items:center;padding:0 2px}
.av{width:32px;height:32px;border-radius:50%;background:var(--brand);color:var(--brand-ink);font-weight:700;font-size:14px;display:flex;align-items:center;justify-content:center;flex:none}
.mi{min-width:0}.mi b{display:block;font-size:14px;color:#fff;font-weight:600;line-height:1.25;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.mi small{font-size:12px;color:var(--side-muted);line-height:1.2}
.out{height:32px;border-radius:8px;border:1px solid rgba(255,255,255,.16);background:rgba(255,255,255,.06);color:#fff;font-size:14px;font-weight:500}.out:hover{background:rgba(255,255,255,.12)}
.main{display:flex;flex-direction:column;min-width:0;min-height:0;height:100%}
.top{height:58px;flex:none;background:var(--surface);border-bottom:1px solid var(--line);display:flex;align-items:center;gap:10px;padding:0 16px;padding-top:env(safe-area-inset-top);box-sizing:content-box}
.top h1{font-size:18px;font-weight:700;line-height:1.2;white-space:nowrap;margin-right:2px}
.live{display:inline-flex;align-items:center;gap:5px;height:20px;padding:0 8px;border-radius:999px;background:var(--primary-soft);color:var(--teal);font-size:12px;font-weight:500}
.live i{width:6px;height:6px;border-radius:50%;background:currentColor}
.live.off{background:var(--red-soft);color:var(--red)}
.slot{display:contents}
.bell{position:relative;width:34px;height:34px;border-radius:8px;border:1px solid color-mix(in srgb,var(--primary) 55%,var(--line));color:var(--teal);display:inline-flex;align-items:center;justify-content:center;flex:none}
.bell:hover{background:var(--primary-soft)}
.bell b{position:absolute;top:-6px;right:-6px;min-width:17px;height:17px;border-radius:9px;background:var(--red);color:#fff;font-size:10.5px;display:flex;align-items:center;justify-content:center;padding:0 4px}
.burger{display:none}
.content{flex:1;min-height:0;overflow:auto;position:relative;z-index:0;padding-bottom:env(safe-area-inset-bottom)}
.content.flush{overflow:hidden;display:flex;flex-direction:column}.content.flush>*{flex:1;min-height:0}
.scrim{display:none}
@media (max-width:860px){
  .shell{grid-template-columns:1fr}
  .side{position:fixed;left:0;top:0;bottom:0;width:240px;z-index:80;transform:translateX(-100%);transition:transform .25s}
  .open .side{transform:none}
  .open .scrim{display:block;position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:70}
  .burger{display:inline-flex}
  .top{padding:0 12px;gap:8px}
}
@media (max-width:520px){.top h1{font-size:16px}.live{display:none}}
</style>
