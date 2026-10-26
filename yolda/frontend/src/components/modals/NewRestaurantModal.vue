<script setup lang="ts">
import { onMounted, onBeforeUnmount, reactive, ref } from 'vue'
import L from 'leaflet'
import { post, errMsg } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { CUISINES } from '@/constants/statuses'
import KeyModal from './KeyModal.vue'
const emit = defineEmits<{ close: []; done: [] }>()
const ui = useUiStore()
const f = reactive({ name: '', cuisine: CUISINES[0], address: '', lat: 41.3111, lng: 69.2797, phone: '', webhook_url: '', api_key: '' })
const err = ref(''), busy = ref(false), res = ref<any>(null), picked = ref(false)
const mapEl = ref<HTMLElement>()
let map: L.Map, marker: L.Marker
onMounted(() => {
  map = L.map(mapEl.value!, { zoomControl: true }).setView([f.lat, f.lng], 11)
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© OpenStreetMap' }).addTo(map)
  map.on('click', (e: L.LeafletMouseEvent) => {
    f.lat = +e.latlng.lat.toFixed(6); f.lng = +e.latlng.lng.toFixed(6); picked.value = true
    if (marker) marker.setLatLng(e.latlng); else marker = L.marker(e.latlng).addTo(map)
    fillAddress(f.lat, f.lng)
  })
  setTimeout(() => map.invalidateSize(), 50)
})
onBeforeUnmount(() => map?.remove())
async function fillAddress(lat: number, lng: number) {
  try {
    const r = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&accept-language=uz&lat=${lat}&lon=${lng}`)
    const d = await r.json()
    const a = d.address || {}
    const street = [a.road, a.house_number].filter(Boolean).join(' ')
    const text = street ? [street, a.suburb || a.city_district || a.city || a.town].filter(Boolean).join(', ') : d.display_name
    if (text) f.address = text
  } catch { /* manzilni qo'lda kiritish mumkin */ }
}
const ALNUM = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
function genKey() {
  const b = new Uint32Array(32); crypto.getRandomValues(b)
  f.api_key = 'yl_live_' + Array.from(b, n => ALNUM[n % ALNUM.length]).join('')
}
async function copyKey() {
  try { await navigator.clipboard.writeText(f.api_key); ui.toast('Kalit nusxalandi') } catch { ui.toast("Nusxalab bo'lmadi", 'var(--red)') }
}
async function go() {
  err.value = ''
  if (!f.name.trim() || !f.address.trim()) { err.value = 'Nom va manzilni kiriting'; return }
  const key = f.api_key.trim()
  if (key && !/^yl_live_[A-Za-z0-9]{32}$/.test(key)) { err.value = "API kalit formati: yl_live_ + 32 ta harf/raqam"; return }
  busy.value = true
  try {
    res.value = await post('/restaurants', { name: f.name.trim(), cuisine: f.cuisine, address: f.address, lat: f.lat, lng: f.lng, phone: f.phone || undefined, webhook_url: f.webhook_url || undefined, api_key: key || undefined })
    ui.toast(`${f.name} ulandi`, 'var(--violet)'); emit('done')
    if (!res.value.api_key && !res.value.webhook_secret) emit('close')
  } catch (e) { err.value = errMsg(e) } finally { busy.value = false }
}
</script>
<template>
  <KeyModal v-if="res && (res.api_key || res.webhook_secret)" :api-key="res.api_key" :secret="res.webhook_secret" title="Restoran ulandi" @close="emit('close')" />
  <Modal v-else-if="!res" title="Yangi restoran ulash" @close="emit('close')">
    <div class="form-grid">
      <div class="field full"><label>Restoran nomi</label><input v-model="f.name" class="inp" /></div>
      <div class="field"><label>Oshxona turi</label><select v-model="f.cuisine" class="inp"><option v-for="c in CUISINES" :key="c">{{ c }}</option></select></div>
      <div class="field full"><label>Manzil</label><input v-model="f.address" class="inp" /></div>
      <div class="field full"><label>Xaritadan nuqta tanlang {{ picked ? `(${f.lat}, ${f.lng})` : '' }}</label><div ref="mapEl" class="mm" /></div>
      <div class="field"><label>Telefon</label><input v-model="f.phone" class="inp" /></div>
      <div class="field full"><label>Restoran API kaliti</label>
        <div class="row" style="gap:6px"><input v-model="f.api_key" class="inp" style="flex:1" placeholder="yl_live_… — «Yaratish» tugmasini bosing" />
          <Btn sm @click="genKey">Yaratish</Btn><Btn sm icon="copy" :disabled="!f.api_key" @click="copyKey">Nusxalash</Btn></div>
        <div style="font-size:11.5px;color:var(--muted);margin-top:4px">Kalitni nusxalab restoran dasturchisiga bering. Ulangandan keyin kalit qayta ko'rsatilmaydi. Bo'sh qoldirsangiz, ulanganda avtomatik yaratiladi.</div></div>
      <div class="field full"><label>Webhook URL (ixtiyoriy)</label><input v-model="f.webhook_url" class="inp" placeholder="https://" /></div>
      <div v-if="err" class="err full" style="color:var(--red);font-size:12px">{{ err }}</div>
    </div>
    <template #footer><Btn @click="emit('close')">Bekor qilish</Btn><Btn variant="primary" :disabled="busy" @click="go">Ulash</Btn></template>
  </Modal>
</template>
<style scoped>.mm{height:200px;border-radius:10px;border:1px solid var(--line);overflow:hidden}</style>
