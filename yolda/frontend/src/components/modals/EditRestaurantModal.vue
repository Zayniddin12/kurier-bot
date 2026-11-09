<script setup lang="ts">
import { reactive, ref } from 'vue'
import { patch, errMsg } from '@/api/client'
const p = defineProps<{ r: any }>()
const emit = defineEmits<{ close: []; done: [] }>()
const f = reactive({ name: p.r.name, cuisine: p.r.cuisine, district: p.r.district, address: p.r.address, phone: p.r.phone, manager: p.r.manager, prep_minutes: p.r.prep_minutes })
const err = ref(''), busy = ref(false)
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
      <div class="field"><label>Telefon</label><input v-model="f.phone" class="inp" /></div>
      <div class="field"><label>Menejer</label><input v-model="f.manager" class="inp" /></div>
      <div class="field"><label>Tayyorlash vaqti (daq)</label><input v-model.number="f.prep_minutes" class="inp" type="number" min="1" /></div>
    </div>
    <div v-if="err" style="color:var(--red);font-size:12.5px;margin-top:8px">{{ err }}</div>
    <template #footer><Btn @click="emit('close')">Bekor qilish</Btn><Btn variant="primary" :disabled="busy" @click="save">Saqlash</Btn></template>
  </Modal>
</template>
