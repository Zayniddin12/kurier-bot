<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import L from 'leaflet'
import { get, post, errMsg } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { useRestaurantsStore } from '@/stores/restaurants'
import { money } from '@/utils/format'

const emit = defineEmits<{ close: []; created: [number] }>()
const ui = useUiStore(), rs = useRestaurantsStore()
const open = computed(() => rs.items.filter((r: any) => r.status !== 'paused'))
const rid = ref<number | null>(ui.restaurantId && open.value.some((r: any) => r.id === ui.restaurantId) ? ui.restaurantId : open.value[0]?.id ?? null)
const rest = computed<any>(() => rs.items.find((r: any) => r.id === rid.value))
const menu = ref<{ id: number; name: string; price: number }[]>([])
const qty = ref<Record<number, number>>({})
const name = ref(''), phone = ref('+998'), address = ref(''), note = ref(''), cnote = ref('')
const lat = ref<number | null>(null), lng = ref<number | null>(null)
const fee = ref<number | null>(null), km = ref<number | null>(null), manualFee = ref<number | null>(null)
const q = ref(''), searching = ref(false), err = ref(''), busy = ref(false)
const mapEl = ref<HTMLElement>()
let map: L.Map | null = null, marker: L.Marker | null = null, restMarker: L.CircleMarker | null = null

watch(rid, async (id) => {
  qty.value = {}; menu.value = []
  if (!id) return
  try { menu.value = (await get(`/operator/restaurants/${id}/menu`)).items } catch (e) { err.value = errMsg(e) }
  drawRest(); requote()
}, { immediate: true })

const lines = computed(() => menu.value.filter((m) => qty.value[m.id] > 0).map((m) => ({ ...m, qty: qty.value[m.id] })))
const subtotal = computed(() => lines.value.reduce((s, l) => s + l.qty * l.price, 0))
const deliveryFee = computed(() => (lat.value != null ? fee.value : manualFee.value))
const total = computed(() => subtotal.value + (deliveryFee.value || 0))
const inc = (id: number, d: number) => { qty.value = { ...qty.value, [id]: Math.max(0, Math.min(100, (qty.value[id] || 0) + d)) } }

const pin = L.divIcon({ className: 'hm-wrap', iconSize: [30, 30], iconAnchor: [15, 28],
  html: '<div class="hm big"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke-width="2.4" stroke-linejoin="round"><path d="M3 11l9-8 9 8v10H3z"/></svg></div>' })
const mapReady = ref(false)
watch(mapEl, async (el) => {
  if (!el || map) return
  await nextTick()
  const c: [number, number] = rest.value ? [rest.value.lat, rest.value.lng] : [41.3111, 69.2797]
  map = L.map(el).setView(c, 13)
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© OpenStreetMap' }).addTo(map)
  map.on('click', (e: L.LeafletMouseEvent) => setPoint(e.latlng.lat, e.latlng.lng))
  mapReady.value = true; drawRest()
  setTimeout(() => map?.invalidateSize(), 80)
})
onBeforeUnmount(() => map?.remove())
function drawRest() {
  if (!map || !rest.value) return
  restMarker?.remove()
  restMarker = L.circleMarker([rest.value.lat, rest.value.lng], { radius: 7, color: '#fff', weight: 2, fillColor: rest.value.color || '#16353C', fillOpacity: 1 }).bindTooltip(rest.value.name).addTo(map)
  if (lat.value == null) map.setView([rest.value.lat, rest.value.lng], 13)
}
function setPoint(la: number, ln: number, fill = true) {
  lat.value = +la.toFixed(6); lng.value = +ln.toFixed(6)
  if (!marker && map) { marker = L.marker([la, ln], { icon: pin, draggable: true }).addTo(map); marker.on('dragend', () => { const l = marker!.getLatLng(); setPoint(l.lat, l.lng) }) }
  else marker?.setLatLng([la, ln])
  if (fill) fillAddress(la, ln)
  requote()
}
async function requote() {
  if (!rid.value || lat.value == null || lng.value == null) { fee.value = null; km.value = null; return }
  try { const d = await get('/operator/quote', { restaurant_id: rid.value, lat: lat.value, lng: lng.value }); fee.value = d.delivery_fee; km.value = d.distance_km } catch { fee.value = null }
}
async function fillAddress(la: number, ln: number) {
  try {
    const d = await (await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&accept-language=uz&lat=${la}&lon=${ln}`)).json()
    const a = d.address || {}
    const street = [a.road, a.house_number].filter(Boolean).join(' ')
    const text = street ? [street, a.suburb || a.city_district || a.city || a.town].filter(Boolean).join(', ') : d.display_name
    if (text && !address.value.trim()) address.value = text
  } catch { /* manzil qo'lda kiritiladi */ }
}
async function search() {
  if (!q.value.trim()) return
  searching.value = true; err.value = ''
  try {
    const r = await (await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&countrycodes=uz&accept-language=uz&q=${encodeURIComponent(q.value)}`)).json()
    if (!r.length) { err.value = 'Manzil topilmadi — xaritadan tanlang'; return }
    setPoint(+r[0].lat, +r[0].lon, false); address.value = q.value.trim(); map?.flyTo([+r[0].lat, +r[0].lon], 16, { duration: 0.5 })
  } catch { err.value = 'Qidiruv ishlamadi — xaritadan tanlang' } finally { searching.value = false }
}

async function submit() {
  err.value = ''
  if (!rid.value) { err.value = 'Restoranni tanlang'; return }
  if (!lines.value.length) { err.value = "Kamida bitta taom tanlang"; return }
  if (!name.value.trim()) { err.value = 'Mijoz ismini kiriting'; return }
  if (phone.value.replace(/\D/g, '').length < 9) { err.value = "Telefon raqamini to'liq kiriting"; return }
  if (!address.value.trim()) { err.value = 'Manzilni kiriting'; return }
  if (lat.value == null && manualFee.value == null) { err.value = "Xaritadan manzilni belgilang yoki yetkazish haqini kiriting"; return }
  busy.value = true
  try {
    const o = await post('/operator/orders', {
      restaurant_id: rid.value, customer_name: name.value.trim(), customer_phone: phone.value.trim(), address: address.value.trim(),
      lat: lat.value, lng: lng.value, items: lines.value.map((l) => ({ menu_id: l.id, qty: l.qty })),
      note: note.value.trim() || null, courier_note: cnote.value.trim() || null, delivery_fee: lat.value == null ? manualFee.value : null,
    })
    ui.toast(`Buyurtma #${o.id} yaratildi`)
    emit('created', o.id); emit('close')
  } catch (e) { err.value = errMsg(e) } finally { busy.value = false }
}
</script>

<template>
  <Modal wide title="Yangi buyurtma" sub="Operator buyurtmasi · to'lov naqd, mijoz kuryerga o'zi to'laydi" @close="emit('close')">
    <div class="grid">
      <div class="col">
        <div class="field"><label>Restoran</label>
          <select v-model="rid" class="inp"><option v-for="r in open" :key="r.id" :value="r.id">{{ r.name }}</option></select></div>
        <div class="sec">Menyu</div>
        <div class="menu">
          <div v-for="m in menu" :key="m.id" class="mi" :class="{ on: qty[m.id] > 0 }">
            <div class="mn"><b>{{ m.name }}</b><span class="num">{{ money(m.price) }} so'm</span></div>
            <div class="st"><button type="button" :disabled="!qty[m.id]" @click="inc(m.id, -1)">−</button><span class="num">{{ qty[m.id] || 0 }}</span><button type="button" @click="inc(m.id, 1)">+</button></div>
          </div>
          <Skeleton v-if="!menu.length" :h="40" :n="4" />
        </div>
      </div>

      <div class="col">
        <div class="form-grid">
          <div class="field"><label>Mijoz ismi</label><input v-model="name" class="inp" maxlength="200" placeholder="Ism" /></div>
          <div class="field"><label>Telefon</label><input v-model="phone" class="inp" maxlength="30" placeholder="+998 90 123 45 67" inputmode="tel" /></div>
        </div>
        <div class="field" style="margin-top:10px"><label>Manzilni qidirish</label>
          <div class="row" style="gap:6px"><input v-model="q" class="inp" style="flex:1" placeholder="Ko'cha, mo'ljal…" @keyup.enter="search" /><Btn :disabled="searching" @click="search">Qidirish</Btn></div></div>
        <div ref="mapEl" class="mm" />
        <div class="sub" style="margin-top:4px">Xaritaga bosib mijoz manzilini belgilang — yetkazish haqi masofadan hisoblanadi</div>
        <div class="field" style="margin-top:10px"><label>Manzil matni</label><input v-model="address" class="inp" maxlength="400" placeholder="Ko'cha, uy, kvartira" /></div>
        <div v-if="lat == null" class="field" style="margin-top:10px"><label>Yetkazish haqi (xaritasiz, so'm)</label><input v-model.number="manualFee" class="inp" type="number" min="0" step="1000" placeholder="Masalan 12000" /></div>
        <div class="form-grid" style="margin-top:10px">
          <div class="field"><label>Izoh — restoranga</label><textarea v-model="note" class="inp" rows="2" maxlength="500" /></div>
          <div class="field"><label>Izoh — kuryerga</label><textarea v-model="cnote" class="inp" rows="2" maxlength="500" /></div>
        </div>
      </div>
    </div>

    <div class="sum">
      <dl><dt>Mahsulotlar</dt><dd class="num">{{ money(subtotal) }} so'm</dd>
        <dt>Yetkazib berish<span v-if="km != null" class="faint"> · {{ km }} km</span></dt><dd class="num">{{ deliveryFee != null ? money(deliveryFee) + " so'm" : '—' }}</dd>
        <dt class="tt">Mijoz kuryerga to'laydi (naqd)</dt><dd class="num tt">{{ money(total) }} so'm</dd></dl>
    </div>
    <div v-if="err" class="err">{{ err }}</div>
    <template #footer><Btn @click="emit('close')">Bekor qilish</Btn><Btn variant="primary" :disabled="busy" @click="submit">Buyurtma yaratish</Btn></template>
  </Modal>
</template>

<style scoped>
.grid{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,6fr);gap:20px}
.col{min-width:0}
.sec{font-size:11.5px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.03em;margin:14px 0 6px}
.menu{display:flex;flex-direction:column;gap:6px;max-height:430px;overflow:auto;padding-right:2px}
.mi{display:flex;align-items:center;justify-content:space-between;gap:10px;border:1px solid var(--line);border-radius:8px;padding:8px 10px}
.mi.on{border-color:var(--brand);background:var(--brand-soft)}
.mn{display:flex;flex-direction:column;min-width:0}.mn b{font-size:13.5px;font-weight:600}.mn span{font-size:12px;color:var(--muted)}
.st{display:flex;align-items:center;gap:8px;flex:none}.st span{min-width:18px;text-align:center;font-weight:600}
.st button{width:28px;height:28px;border-radius:7px;border:1px solid var(--line);background:var(--surface);font-size:16px;line-height:1;color:var(--ink)}.st button:disabled{opacity:.4;cursor:default}
.mm{height:230px;border-radius:10px;border:1px solid var(--line);overflow:hidden;margin-top:10px}
.sum{margin-top:14px;border-top:1px solid var(--line);padding-top:10px}
dl{display:grid;grid-template-columns:1fr auto;gap:4px 20px;margin:0;font-size:13.5px}dd{margin:0;text-align:right}dt{color:var(--muted)}
.tt{font-weight:700;color:var(--ink);font-size:15px}
.err{color:var(--red);font-size:12.5px;margin-top:8px}
@media (max-width:760px){.grid{grid-template-columns:1fr}}
</style>
