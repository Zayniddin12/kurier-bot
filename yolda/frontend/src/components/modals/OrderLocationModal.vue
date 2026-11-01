<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import L from 'leaflet'
import { patch, errMsg } from '@/api/client'
import { useUiStore } from '@/stores/ui'
const p = defineProps<{ order: any }>()
const emit = defineEmits<{ close: []; done: [] }>()
const ui = useUiStore()
const lat = ref<number>(p.order.lat ?? p.order.restaurant.lat), lng = ref<number>(p.order.lng ?? p.order.restaurant.lng)
const address = ref<string>(p.order.address || '')
const q = ref(''), busy = ref(false), err = ref(''), searching = ref(false)
const moved = ref(false)
const mapEl = ref<HTMLElement>()
let map: L.Map, marker: L.Marker
const pin = L.divIcon({ className: 'hm-wrap', iconSize: [30, 30], iconAnchor: [15, 28],
  html: '<div class="hm big"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke-width="2.4" stroke-linejoin="round"><path d="M3 11l9-8 9 8v10H3z"/></svg></div>' })
function setPoint(la: number, ln: number, fill = true) {
  lat.value = +la.toFixed(6); lng.value = +ln.toFixed(6); moved.value = true
  marker.setLatLng([la, ln]); if (fill) fillAddress(la, ln)
}
onMounted(() => {
  map = L.map(mapEl.value!, { zoomControl: true }).setView([lat.value, lng.value], 15)
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© OpenStreetMap' }).addTo(map)
  const r = p.order.restaurant
  L.circleMarker([r.lat, r.lng], { radius: 7, color: '#fff', weight: 2, fillColor: r.color || '#16201A', fillOpacity: 1 }).bindTooltip(r.name).addTo(map)
  marker = L.marker([lat.value, lng.value], { icon: pin, draggable: true }).addTo(map)
  marker.on('dragend', () => { const l = marker.getLatLng(); setPoint(l.lat, l.lng) })
  map.on('click', (e: L.LeafletMouseEvent) => setPoint(e.latlng.lat, e.latlng.lng))
  setTimeout(() => map.invalidateSize(), 50)
})
onBeforeUnmount(() => map?.remove())
async function fillAddress(la: number, ln: number) {
  try {
    const d = await (await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&accept-language=uz&lat=${la}&lon=${ln}`)).json()
    const a = d.address || {}
    const street = [a.road, a.house_number].filter(Boolean).join(' ')
    const text = street ? [street, a.suburb || a.city_district || a.city || a.town].filter(Boolean).join(', ') : d.display_name
    if (text) address.value = text
  } catch { /* manzilni qo'lda kiritish mumkin */ }
}
async function search() {
  if (!q.value.trim()) return
  searching.value = true; err.value = ''
  try {
    const r = await (await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&countrycodes=uz&accept-language=uz&q=${encodeURIComponent(q.value)}`)).json()
    if (!r.length) { err.value = 'Manzil topilmadi — xaritadan tanlang'; return }
    const la = +r[0].lat, ln = +r[0].lon
    setPoint(la, ln, false); address.value = q.value.trim(); map.flyTo([la, ln], 17, { duration: 0.5 })
  } catch { err.value = 'Qidiruv ishlamadi — xaritadan tanlang' } finally { searching.value = false }
}
async function save() {
  err.value = ''
  if (!moved.value) { err.value = 'Xaritadan yangi nuqtani tanlang yoki pinni suring'; return }
  busy.value = true
  try {
    await patch(`/orders/${p.order.id}/location`, { lat: lat.value, lng: lng.value, address: address.value })
    ui.toast(p.order.status === 'onway' ? "Manzil o'zgardi · kuryerga Telegramda qayta yuboriladi" : "Mijoz manzili o'zgartirildi")
    emit('done'); emit('close')
  } catch (e) { err.value = errMsg(e) } finally { busy.value = false }
}
</script>
<template>
  <Modal wide title="Mijoz manzilini o'zgartirish" :sub="`Buyurtma #${order.id} · ${order.customer_name}`" @close="emit('close')">
    <div class="field"><label>Manzilni qidirish</label>
      <div class="row" style="gap:6px"><input v-model="q" class="inp" style="flex:1" placeholder="Ko'cha, mo'ljal…" @keyup.enter="search" /><Btn :disabled="searching" @click="search">Qidirish</Btn></div></div>
    <div ref="mapEl" class="mm" />
    <div class="field" style="margin-top:12px"><label>Manzil matni</label><input v-model="address" class="inp" /></div>
    <div class="sub" style="margin-top:6px">Koordinata: {{ lat }}, {{ lng }} · pinni suring yoki xaritaga bosing</div>
    <div v-if="order.status === 'onway'" class="box" style="margin-top:10px;font-size:13px">Kuryer ovqatni olgan — saqlansa, yangi lokatsiya unga Telegram botda qayta yuboriladi.</div>
    <div v-if="err" style="color:var(--red);font-size:12.5px;margin-top:8px">{{ err }}</div>
    <template #footer><Btn @click="emit('close')">Bekor qilish</Btn><Btn variant="primary" :disabled="busy" @click="save">Saqlash</Btn></template>
  </Modal>
</template>
<style scoped>.mm{height:360px;border-radius:12px;border:1px solid var(--line);overflow:hidden;margin-top:10px}</style>
