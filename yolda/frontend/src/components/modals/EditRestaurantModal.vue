<script setup lang="ts">
import { onMounted, onBeforeUnmount, reactive, ref } from 'vue'
import L from 'leaflet'
import { patch, errMsg } from '@/api/client'
const p = defineProps<{ r: any }>()
const emit = defineEmits<{ close: []; done: [] }>()
const f = reactive({ name: p.r.name, cuisine: p.r.cuisine, district: p.r.district, address: p.r.address, phone: p.r.phone, manager: p.r.manager, prep_minutes: p.r.prep_minutes, lat: Number(p.r.lat) || 41.3111, lng: Number(p.r.lng) || 69.2797 })
const err = ref(''), busy = ref(false)
const mapEl = ref<HTMLElement>()
let map: L.Map, marker: L.Marker
onMounted(() => {
  const has = !!(p.r.lat && p.r.lng)
  map = L.map(mapEl.value!).setView([f.lat, f.lng], has ? 15 : 11)
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© OpenStreetMap' }).addTo(map)
  if (has) marker = L.marker([f.lat, f.lng]).addTo(map)
  map.on('click', (e: L.LeafletMouseEvent) => {
    f.lat = +e.latlng.lat.toFixed(6); f.lng = +e.latlng.lng.toFixed(6)
    if (marker) marker.setLatLng(e.latlng); else marker = L.marker(e.latlng).addTo(map)
    fillAddress(f.lat, f.lng)
  })
  setTimeout(() => map.invalidateSize(), 50)
})
onBeforeUnmount(() => map?.remove())
async function fillAddress(lat: number, lng: number) {
  try {
    const r = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&accept-language=uz&lat=${lat}&lon=${lng}`)
    const a = (await r.json()).address || {}
    const street = [a.road, a.house_number].filter(Boolean).join(' ')
    if (street) f.address = [street, a.suburb || a.city_district || a.city || a.town].filter(Boolean).join(', ')
  } catch { /* manzilni qo'lda kiritish mumkin */ }
}
async function save() {
  if (!f.name.trim()) { err.value = 'Nomini kiriting'; return }
  busy.value = true; err.value = ''
  try { await patch(`/restaurants/${p.r.id}`, { ...f, name: f.name.trim(), prep_minutes: Number(f.prep_minutes) || 15 }); emit('done'); emit('close') }
  catch (e) { err.value = errMsg(e) } finally { busy.value = false }
}
</script>
<template>
  <Modal title="Restoranni tahrirlash" :sub="r.name" @close="emit('close')">
    <div class="form-grid">
      <div class="field full"><label>Nomi</label><input v-model="f.name" class="inp" /></div>
      <div class="field"><label>Oshxona turi</label><input v-model="f.cuisine" class="inp" /></div>
      <div class="field"><label>Tuman</label><input v-model="f.district" class="inp" /></div>
      <div class="field full"><label>Manzil</label><input v-model="f.address" class="inp" /></div>
      <div class="field full"><label>Xaritadan joylashuvni o'zgartiring ({{ f.lat }}, {{ f.lng }})</label><div ref="mapEl" class="mm" /></div>
      <div class="field"><label>Telefon</label><input v-model="f.phone" class="inp" /></div>
      <div class="field"><label>Menejer</label><input v-model="f.manager" class="inp" /></div>
      <div class="field"><label>Tayyorlash vaqti (daq)</label><input v-model.number="f.prep_minutes" class="inp" type="number" min="1" /></div>
    </div>
    <div v-if="err" style="color:var(--red);font-size:12.5px;margin-top:8px">{{ err }}</div>
    <template #footer><Btn @click="emit('close')">Bekor qilish</Btn><Btn variant="primary" :disabled="busy" @click="save">Saqlash</Btn></template>
  </Modal>
</template>
<style scoped>.mm{height:220px;border-radius:10px;border:1px solid var(--line);overflow:hidden}</style>
