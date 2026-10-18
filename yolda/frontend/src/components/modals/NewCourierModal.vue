<script setup lang="ts">
import { reactive, ref } from 'vue'
import { post, errMsg } from '@/api/client'
import { useUiStore } from '@/stores/ui'
const emit = defineEmits<{ close: []; done: [] }>()
const ui = useUiStore()
const f = reactive({ first_name: '', last_name: '', phone: '', pinfl: '', vehicle: 'Skuter', shift: '09:00–21:00' })
const errs = reactive<Record<string, string>>({})
const busy = ref(false)
async function go() {
  Object.keys(errs).forEach((k) => delete errs[k])
  const phone = f.phone.replace(/\D/g, '')
  if (!f.first_name.trim() || !f.last_name.trim()) errs.name = 'Ism va familiyani kiriting'
  if (phone.length !== 9) errs.phone = 'Telefon raqami 9 ta raqamdan iborat bo\'lsin'
  if (!/^\d{14}$/.test(f.pinfl)) errs.pinfl = 'JShShIR 14 ta raqamdan iborat bo\'lsin'
  if (Object.keys(errs).length) return
  busy.value = true
  try {
    await post('/couriers', { ...f, first_name: f.first_name.trim(), last_name: f.last_name.trim(), phone })
    ui.toast(`${f.first_name} ${f.last_name} qo'shildi · ilovaga kirganda liniyaga chiqadi`); emit('done'); emit('close')
  } catch (e) { const m = errMsg(e); if (m.includes('JShShIR')) errs.pinfl = m; else errs.name = m } finally { busy.value = false }
}
</script>
<template>
  <Modal title="Yangi kuryer qo'shish" @close="emit('close')">
    <div class="form-grid">
      <div class="field"><label>Ism</label><input v-model="f.first_name" class="inp" /></div>
      <div class="field"><label>Familiya</label><input v-model="f.last_name" class="inp" /></div>
      <div v-if="errs.name" class="err full" style="color:var(--red);font-size:12px">{{ errs.name }}</div>
      <div class="field"><label>Telefon raqami</label><input v-model="f.phone" class="inp" placeholder="90 123 45 67" inputmode="tel" /><span v-if="errs.phone" class="err">{{ errs.phone }}</span></div>
      <div class="field"><label>JShShIR</label><input v-model="f.pinfl" class="inp" maxlength="14" inputmode="numeric" /><span v-if="errs.pinfl" class="err">{{ errs.pinfl }}</span></div>
      <div class="field"><label>Transport turi</label><select v-model="f.vehicle" class="inp"><option value="Skuter">Skuter</option><option value="Avto">Avtomobil</option><option value="Velo">Velosiped</option><option value="Piyoda">Piyoda</option></select></div>
      <div class="field"><label>Smena</label><select v-model="f.shift" class="inp"><option>08:00–20:00</option><option>09:00–21:00</option><option>10:00–22:00</option><option>11:00–23:00</option></select></div>
    </div>
    <template #footer><Btn @click="emit('close')">Bekor qilish</Btn><Btn variant="primary" :disabled="busy" @click="go">Qo'shish</Btn></template>
  </Modal>
</template>
