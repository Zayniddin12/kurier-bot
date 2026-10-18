<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, shallowRef, watch } from 'vue'
import L from 'leaflet'
import { get, errMsg } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { onLive } from '@/stores/live'
import { useDrawer } from '@/utils/drawer'
import { initials } from '@/utils/format'
import { WORK_STATUS, VEHICLES } from '@/constants/statuses'

const ui = useUiStore(), drawer = useDrawer()
const couriers = reactive(new Map<number, any>())
const rests = shallowRef<any[]>([])
const error = ref(''), loaded = ref(false)
const fStatus = ref('all'), fVeh = ref('all'), q = ref('')
const sheetOpen = ref(true)
const selected = computed(() => (drawer.current.value?.kind === 'courier' ? drawer.current.value.id : null))

let map: L.Map
const cMarkers = new Map<number, L.Marker>()
const rMarkers = new Map<number, L.Marker>()
const lines = new Map<number, L.Polyline[]>()
let homePin: L.Marker | null = null
const mapEl = ref<HTMLElement>()

async function load() {
  try {
    const r = await get('/map/state')
    couriers.clear(); (r.couriers as any[]).forEach((c) => couriers.set(c.id, c)); rests.value = r.restaurants; loaded.value = true; error.value = ''
    drawAll()
  } catch (e) { error.value = errMsg(e) }
}
onMounted(() => {
  map = L.map(mapEl.value!, { zoomControl: false, attributionControl: true }).setView([41.3111, 69.2797], 12)
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© OpenStreetMap' }).addTo(map)
  map.on('click', () => { if (drawer.current.value) drawer.close() })
  new ResizeObserver(() => map.invalidateSize()).observe(mapEl.value!)
  setTimeout(() => map.invalidateSize(), 100)
  load()
  consumeFocus()
})
onBeforeUnmount(() => map?.remove())
let reloadT: any
onLive('order.created', () => { clearTimeout(reloadT); reloadT = setTimeout(load, 800) })
onLive('order.updated', () => { clearTimeout(reloadT); reloadT = setTimeout(load, 800) })
onLive('courier.updated', (c) => { couriers.set(c.id, { ...(couriers.get(c.id) || {}), ...c }); drawCourier(c.id); refreshLines(c.id) })
onLive('restaurant.updated', (r) => { rests.value = rests.value.map((x) => (x.id === r.id ? { ...x, ...r } : x)); drawRests() })

const hasProblem = (c: any) => !!c.issue
const visible = (c: any) => c.lat != null && c.work_status !== 'offline' && c.account_status !== 'blocked'
const passes = (c: any) => visible(c) && (fStatus.value === 'all' || c.work_status === fStatus.value) && (fVeh.value === 'all' || c.vehicle === fVeh.value)
  && (!q.value || (c.name + (c.current_order_id || '')).toLowerCase().includes(q.value.toLowerCase()))

function colorOf(c: any) { return WORK_STATUS[c.work_status]?.color || 'var(--grey)' }
function cIcon(c: any) {
  const sel = c.id === selected.value
  const dim = ui.restaurantId && c.order && c.order.restaurant_id !== ui.restaurantId && c.work_status !== 'idle' ? 0.28 : 1
  return L.divIcon({ className: 'cmk-wrap', iconSize: [25, 25], iconAnchor: [12, 12],
    html: `<div class="cmk ${sel ? 'sel' : ''}" style="background:${colorOf(c)};border:${hasProblem(c) || c.late ? '3.5px solid var(--red)' : '2.5px solid #fff'};opacity:${dim}">${initials(c.name)}${sel ? '<i class="ring"></i>' : ''}</div>` })
}
function drawCourier(id: number) {
  const c = couriers.get(id); if (!c) return
  const show = visible(c) && (fStatus.value === 'all' || c.work_status === fStatus.value) && (fVeh.value === 'all' || c.vehicle === fVeh.value)
  let m = cMarkers.get(id)
  if (!show) { if (m) { m.remove(); cMarkers.delete(id) } return }
  if (!m) {
    m = L.marker([c.lat, c.lng], { icon: cIcon(c), zIndexOffset: 500 }).addTo(map)
    m.on('click', (e) => { L.DomEvent.stopPropagation(e); pick(id, false) })
    cMarkers.set(id, m)
  } else { m.setLatLng([c.lat, c.lng]); m.setIcon(cIcon(c)) }
}
function rIcon(r: any) {
  const dim = ui.restaurantId && ui.restaurantId !== r.id ? 0.35 : 1
  const paused = r.status === 'paused' ? 0.55 : 1
  return L.divIcon({ className: 'rmk-wrap', iconSize: [22, 22], iconAnchor: [11, 11],
    html: `<div class="rmk" style="background:${r.color};opacity:${dim * paused}"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round"><path d="M7 3v8M4 3v5a3 3 0 0 0 6 0V3M7 11v10M17 3c-2 2-3 5-3 8h3v10"/></svg></div><span class="mk-label" style="opacity:${dim}">${r.name}</span>` })
}
function drawRests() {
  rests.value.forEach((r) => {
    let m = rMarkers.get(r.id)
    if (!m) { m = L.marker([r.lat, r.lng], { icon: rIcon(r) }).addTo(map); m.on('click', (e) => { L.DomEvent.stopPropagation(e); drawer.open('restaurant', r.id) }); rMarkers.set(r.id, m) }
    else m.setIcon(rIcon(r))
  })
}
function refreshLines(id: number) {
  lines.get(id)?.forEach((l) => l.remove()); lines.delete(id)
  const c = couriers.get(id)
  if (!c || !cMarkers.has(id) || !c.route) return
  const pts: [number, number][] = [[c.lat, c.lng]]
  if (c.route.stage === 'pickup' && c.route.restaurant) pts.push([c.route.restaurant.lat, c.route.restaurant.lng])
  if (c.route.customer) pts.push([c.route.customer.lat, c.route.customer.lng])
  if (pts.length < 2) return
  const sel = id === selected.value
  const col = getComputedStyle(document.documentElement).getPropertyValue(c.work_status === 'pickup' ? '--blue' : '--teal').trim() || '#0D7F68'
  const pl = L.polyline(pts, { color: col, weight: sel ? 3.5 : 2, opacity: sel ? 0.95 : 0.45, dashArray: sel ? undefined : '6 6', interactive: false }).addTo(map)
  lines.set(id, [pl])
}
function drawHome() {
  homePin?.remove(); homePin = null
  const c = selected.value ? couriers.get(selected.value) : null
  if (c?.route?.customer) homePin = L.marker([c.route.customer.lat, c.route.customer.lng], { interactive: false, icon: L.divIcon({ className: 'hm-wrap', iconSize: [26, 26], iconAnchor: [13, 24],
    html: '<div class="hm"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.4" stroke-linejoin="round"><path d="M3 11l9-8 9 8v10H3z"/></svg></div>' }) }).addTo(map)
}
function drawAll() { drawRests(); couriers.forEach((_, id) => { drawCourier(id); refreshLines(id) }); drawHome() }
watch([fStatus, fVeh, selected, () => ui.restaurantId], () => { if (map) drawAll() })

function pick(id: number, fly = true) {
  const c = couriers.get(id)
  if (fly && c?.lat != null) map.flyTo([c.lat, c.lng], Math.max(map.getZoom(), 14), { duration: 0.6 })
  drawer.open('courier', id)
}
function consumeFocus() {
  const f = ui.mapFocus; if (!f) return
  if (f.filter) fStatus.value = f.filter
  ui.mapFocus = null
  if (f.courierId) { const t = setInterval(() => { if (couriers.has(f.courierId!)) { clearInterval(t); pick(f.courierId!) } }, 200); setTimeout(() => clearInterval(t), 4000) }
}
const zoomIn = () => map.zoomIn(), zoomOut = () => map.zoomOut(), fitAll = () => map.flyTo([41.3111, 69.2797], 12)

const all = computed(() => [...couriers.values()])
const onMapList = computed(() => all.value.filter(visible))
const order = { delivering: 0, pickup: 1, idle: 2, break: 3 } as Record<string, number>
const list = computed(() => all.value.filter(passes).sort((a, b) => order[a.work_status] - order[b.work_status]))
const cnt = (k: string) => onMapList.value.filter((c) => c.work_status === k).length
const cntV = (k: string) => onMapList.value.filter((c) => c.vehicle === k).length
const statusChips = [['all', 'Hammasi', ''], ['delivering', 'Yetkazmoqda', 'var(--teal)'], ['pickup', 'Restoranga', 'var(--blue)'], ['idle', "Bo'sh", 'var(--amber)'], ['break', 'Tanaffus', 'var(--grey)']]
const vehChips = [['all', 'Barcha transport'], ['Skuter', 'Skuter'], ['Avto', 'Avtomobil'], ['Velo', 'Velosiped'], ['Piyoda', 'Piyoda']]
const subTxt = (c: any) => c.order ? `${c.order.restaurant_name} · #${c.order.id} · ${VEHICLES[c.vehicle]?.label}` : WORK_STATUS[c.work_status].label
</script>

<template>
  <div class="mapwrap" :class="{ dopen: !!drawer.current.value }">
    <div ref="mapEl" class="map" />
    <div v-if="error" class="err"><ErrorBox :message="error" @retry="load" /></div>
    <aside class="panel" :class="{ closed: !sheetOpen }">
      <button class="sheet-h" @click="sheetOpen = !sheetOpen"><b>Kuryerlar xaritada</b><span class="num">{{ onMapList.length }}</span><span class="sp" /><Icon class="chv" name="chevron" :size="16" /></button>
      <div class="chips"><Chip v-for="s in statusChips" :key="s[0]" :on="fStatus === s[0]" :dot="s[2] || undefined" :n="s[0] === 'all' ? onMapList.length : cnt(s[0])" @click="fStatus = s[0]">{{ s[1] }}</Chip></div>
      <div class="chips"><Chip v-for="v in vehChips" :key="v[0]" :on="fVeh === v[0]" :n="v[0] === 'all' ? onMapList.length : cntV(v[0])" @click="fVeh = v[0]">{{ v[1] }}</Chip></div>
      <div style="padding:0 12px 8px"><SearchInput v-model="q" placeholder="Ism yoki buyurtma raqami" /></div>
      <div class="list">
        <div v-for="c in list" :key="c.id" class="it" :class="{ on: selected === c.id }" @click="pick(c.id)">
          <Avatar :seed="c.avatar_seed" :female="c.is_female" :size="34" />
          <div class="im">
            <div class="row" style="gap:6px"><b>{{ c.name }}</b><span v-if="c.issue" class="mini-t red">Muammo</span><span v-else-if="c.late" class="mini-t amber">Kechikish</span></div>
            <div class="sub row" style="gap:6px"><i class="dot" :style="{ background: colorOf(c) }" />{{ subTxt(c) }}</div>
            <div v-if="c.order" class="sub row" style="gap:5px"><Icon name="phone" :size="12" /><a :href="`tel:${c.order.customer_phone}`" @click.stop>{{ c.order.customer_phone }}</a> · {{ c.order.customer_name }}</div>
          </div>
          <div v-if="c.eta" class="eta num"><b :class="{ red: c.eta.late }">{{ c.eta.eta_min }} daq</b><small>{{ c.eta.remaining_km.toFixed(1) }} km</small></div>
        </div>
        <Empty v-if="loaded && !list.length" title="Kuryer yo'q" text="Filtrni o'zgartiring" />
      </div>
    </aside>
    <div class="zoom"><IconBtn icon="plus" title="Yaqinlashtirish" @click="zoomIn" /><IconBtn icon="minus" title="Uzoqlashtirish" @click="zoomOut" /><IconBtn icon="scan" title="Butun shahar" @click="fitAll" /></div>
  </div>
</template>

<style>
.cmk-wrap,.rmk-wrap,.hm-wrap{background:none!important;border:0!important}
.cmk{position:relative;width:25px;height:25px;border-radius:50%;color:#fff;font-size:8.5px;font-weight:700;display:flex;align-items:center;justify-content:center;box-sizing:border-box;box-shadow:0 1px 4px rgba(0,0,0,.35);transition:opacity .2s}
.cmk-wrap{transition:transform 1s linear}
.leaflet-zoom-anim .cmk-wrap{transition:none}
.cmk .ring{position:absolute;inset:-2px;border-radius:50%;border:2px solid var(--brand);animation:ring 1.6s infinite;pointer-events:none}
@keyframes ring{0%{transform:scale(1);opacity:.9}100%{transform:scale(2.2);opacity:0}}
.rmk{width:22px;height:22px;border-radius:6px;border:2.5px solid #fff;box-sizing:border-box;display:flex;align-items:center;justify-content:center;box-shadow:0 1px 4px rgba(0,0,0,.3)}
.hm{width:26px;height:26px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);background:#16201A;display:flex;align-items:center;justify-content:center;border:2px solid #fff}
.hm svg{transform:rotate(45deg)}
</style>
<style scoped>
.mapwrap{position:absolute;inset:0}.map{position:absolute;inset:0}
.err{position:absolute;top:16px;left:50%;transform:translateX(-50%);z-index:500;background:var(--surface);border-radius:12px}
.panel{position:absolute;left:16px;top:16px;bottom:16px;width:290px;z-index:500;background:var(--surface);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow);display:flex;flex-direction:column;overflow:hidden}
.sheet-h{display:flex;align-items:center;gap:8px;border:0;background:transparent;padding:14px 14px 8px;font-size:15px;cursor:default}.sheet-h .chv{display:none}
.chips{display:flex;flex-wrap:wrap;gap:5px;padding:0 12px 8px}
.list{flex:1;overflow:auto;border-top:1px solid var(--line-2)}
.it{display:flex;gap:9px;padding:9px 12px;border-bottom:1px solid var(--line-2);cursor:pointer;align-items:flex-start}.it:hover{background:var(--surface-2)}.it.on{background:var(--brand-soft)}
.im{flex:1;min-width:0}.im b{font-size:13px}.dot{width:7px;height:7px;border-radius:50%;flex:none}
.mini-t{font-size:10.5px;font-weight:700;padding:0 5px;border-radius:5px;background:var(--surface-2)}
.eta{text-align:right}.eta b{display:block;font-size:12.5px}.eta small{font-size:11px;color:var(--muted)}
.zoom{position:absolute;right:16px;bottom:24px;z-index:500;display:flex;flex-direction:column;gap:6px;transition:transform .28s}
.dopen .zoom{transform:translateX(-436px)}
@media (max-width:860px){
  .panel{left:12px;right:12px;top:auto;bottom:12px;width:auto;height:46%;transition:height .25s}.panel.closed{height:112px}
  .sheet-h{cursor:pointer}.sheet-h .chv{display:block;transition:transform .2s}.closed .chv{transform:rotate(180deg)}
  .zoom{bottom:auto;top:12px}.dopen .zoom{transform:none}
}
</style>
