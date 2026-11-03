<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch, computed } from 'vue'
import L from 'leaflet'
import { get } from '@/api/client'
const p = defineProps<{ order: any }>()
const mapEl = ref<HTMLElement>()
const route = ref<any>(null)
let map: L.Map, layers: L.Layer[] = [], seq = 0, last = 0, fitted = false

const dot = (bg: string, round = true) => L.divIcon({ className: 'hm-wrap', iconSize: [22, 22], iconAnchor: [11, 11],
  html: `<div style="width:20px;height:20px;border-radius:${round ? '50%' : '6px'};background:${bg};border:3px solid #fff;box-shadow:0 1px 5px rgba(0,0,0,.45)"></div>` })
const pin = L.divIcon({ className: 'hm-wrap', iconSize: [30, 30], iconAnchor: [15, 28],
  html: '<div class="hm big"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke-width="2.4" stroke-linejoin="round"><path d="M3 11l9-8 9 8v10H3z"/></svg></div>' })

function draw(fit: boolean) {
  layers.forEach((l) => l.remove()); layers = []
  const o = p.order, r = o.restaurant, c = o.courier
  const css = getComputedStyle(document.documentElement)
  const col = (v: string, d: string) => css.getPropertyValue(v).trim() || d
  const pts: L.LatLngExpression[] = []
  ;(route.value?.legs || []).forEach((g: any) => {
    layers.push(L.polyline(g.geometry, { color: col(g.to === 'restaurant' ? '--blue' : '--teal', '#0D7F68'), weight: 5, opacity: 0.9, dashArray: g.approx ? '8 8' : undefined, interactive: false }).addTo(map))
    g.geometry.forEach((x: any) => pts.push(x))
  })
  layers.push(L.marker([r.lat, r.lng], { icon: dot('#F5B301', false) }).bindTooltip(r.name).addTo(map)); pts.push([r.lat, r.lng])
  if (o.lat != null) { layers.push(L.marker([o.lat, o.lng], { icon: pin }).bindTooltip(o.customer_name).addTo(map)); pts.push([o.lat, o.lng]) }
  if (c?.lat != null && ['assigned', 'onway'].includes(o.status)) { layers.push(L.marker([c.lat, c.lng], { icon: dot('#2E6BD8'), zIndexOffset: 500 }).bindTooltip(c.name).addTo(map)); pts.push([c.lat, c.lng]) }
  if ((fit || !fitted) && pts.length) { map.fitBounds(L.latLngBounds(pts), { padding: [40, 40], maxZoom: 16 }); fitted = true }
}
async function loadRoute(fit = false) {
  const my = ++seq
  try {
    const r = await get(`/operator/orders/${p.order.id}/route`)
    if (my !== seq) return
    route.value = r.legs?.length ? r : null; last = Date.now()
  } catch { /* marshrut bo'lmasa — faqat nuqtalar */ }
  if (map) draw(fit)
}
onMounted(() => {
  map = L.map(mapEl.value!, { zoomControl: true }).setView([p.order.restaurant.lat, p.order.restaurant.lng], 13)
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© OpenStreetMap' }).addTo(map)
  new ResizeObserver(() => map.invalidateSize()).observe(mapEl.value!)
  setTimeout(() => map.invalidateSize(), 100)
  draw(true); loadRoute(true)
})
onBeforeUnmount(() => map?.remove())
// buyurtma/kuryer joyi o'zgarganda: marshrutni (8 soniyadan tez emas) yangilaymiz
const key = computed(() => [p.order.id, p.order.status, p.order.courier?.id, p.order.lat, p.order.lng, Math.round((p.order.courier?.lat ?? 0) * 2000), Math.round((p.order.courier?.lng ?? 0) * 2000)].join('|'))
watch(key, (n, o) => { if (!map) return; draw(false); if (n.split('|')[0] !== o.split('|')[0] || Date.now() - last > 8000) loadRoute(n.split('|')[0] !== o.split('|')[0]) })
const dist = (m: number) => (m < 1000 ? `${Math.round(m / 10) * 10} m` : `${(m / 1000).toFixed(1)} km`)
const q = computed(() => `${p.order.lat},${p.order.lng}`)
</script>
<template>
  <div>
    <div class="head">
      <span v-if="route">Yo'l: <b class="num">{{ dist(route.distance_m) }}</b> · ~<b class="num">{{ Math.max(1, Math.round(route.duration_s / 60)) }} daq</b><i v-if="route.approx" class="faint"> (taxminiy)</i></span>
      <span v-else class="faint">Marshrut mavjud emas</span>
      <span class="sp" />
      <template v-if="order.lat != null">
        <a :href="`https://yandex.uz/maps/?pt=${order.lng},${order.lat}&z=16&l=map`" target="_blank" rel="noopener">Yandex</a>
        <a :href="`https://www.google.com/maps/search/?api=1&query=${q}`" target="_blank" rel="noopener">Google</a>
      </template>
    </div>
    <div ref="mapEl" class="m" />
    <div class="lg"><span><i style="background:#F5B301;border-radius:3px" />Restoran</span><span><i style="background:var(--teal)" />Mijoz</span><span><i style="background:#2E6BD8" />Kuryer</span><span><i class="ln" />Marshrut</span></div>
  </div>
</template>
<style scoped>
.head{display:flex;gap:12px;align-items:center;font-size:12.5px;margin-bottom:8px;flex-wrap:wrap}
.m{height:300px;border-radius:12px;border:1px solid var(--line);overflow:hidden;z-index:0}
.lg{display:flex;gap:14px;font-size:11.5px;color:var(--muted);margin-top:8px;flex-wrap:wrap}.lg span{display:inline-flex;align-items:center;gap:5px}
.lg i{width:9px;height:9px;border-radius:50%;display:inline-block}.lg i.ln{width:16px;height:3px;border-radius:2px;background:var(--teal)}
</style>
