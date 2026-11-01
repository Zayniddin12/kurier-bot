<script setup lang="ts">
import { reactive, ref } from 'vue'
import { post, errMsg } from '@/api/client'
import { useUiStore } from '@/stores/ui'
const emit = defineEmits<{ close: []; done: [] }>()
const ui = useUiStore()
const VEHICLES = [{ v: 'Avto', l: 'Avtomobil' }, { v: 'Skuter', l: 'Skuter' }, { v: 'Velo', l: 'Velosiped' }, { v: 'Piyoda', l: 'Piyoda' }]
const CITIES = ['Toshkent', 'Samarqand', 'Buxoro', 'Andijon', 'Farg\'ona', 'Namangan', 'Qarshi', 'Nukus', 'Urganch', 'Navoiy', 'Jizzax', 'Guliston', 'Termiz']
const f = reactive({
  first_name: '', last_name: '', phone: '', birth_date: '', pinfl: '', license_no: '', vehicle_doc: '',
  vehicle: 'Skuter', plate: '', car_model: '', status: 'active', city: '', shift: '09:00–21:00',
})
const errs = reactive<Record<string, string>>({})
const busy = ref(false)
async function go() {
  Object.keys(errs).forEach((k) => delete errs[k])
  const phone = f.phone.replace(/\D/g, '')
  if (!f.first_name.trim()) errs.first_name = 'Ismni kiriting'
  if (!f.last_name.trim()) errs.last_name = 'Familiyani kiriting'
  if (phone.length !== 9) errs.phone = 'Telefon raqami 9 ta raqamdan iborat bo\'lsin'
  if (!f.birth_date) errs.birth_date = 'Tug\'ilgan sanani kiriting'
  if (!/^\d{14}$/.test(f.pinfl)) errs.pinfl = 'JShShIR 14 ta raqamdan iborat bo\'lsin'
  if (!f.city) errs.city = 'Shaharni tanlang'
  if (Object.keys(errs).length) return
  busy.value = true
  try {
    await post('/couriers', {
      ...f, first_name: f.first_name.trim(), last_name: f.last_name.trim(), phone, birth_date: f.birth_date,
      plate: f.plate.replace(/\s/g, ''),
    })
    ui.toast(`${f.first_name} ${f.last_name} qo'shildi · ilovaga kirganda liniyaga chiqadi`); emit('done'); emit('close')
  } catch (e) {
    const m = errMsg(e)
    if (m.includes('JShShIR')) errs.pinfl = m; else if (m.includes('Telefon')) errs.phone = m; else errs.form = m
  } finally { busy.value = false }
}
</script>
<template>
  <Modal wide title="Yangi kuryer qo'shish" @close="emit('close')">
    <div class="cards">
      <section class="card">
        <header><i class="ic violet"><Icon name="user" :size="18" /></i><div><h4>Shaxsiy ma'lumotlar</h4><p>Ism, kontaktlar va tug'ilgan sana</p></div></header>
        <div class="grid">
          <div class="field"><label>Ism <b>*</b></label><input v-model="f.first_name" class="inp lg" :class="{ bad: errs.first_name }" /><span v-if="errs.first_name" class="err">{{ errs.first_name }}</span></div>
          <div class="field"><label>Familiya <b>*</b></label><input v-model="f.last_name" class="inp lg" :class="{ bad: errs.last_name }" /><span v-if="errs.last_name" class="err">{{ errs.last_name }}</span></div>
          <div class="field"><label>Telefon raqami <b>*</b></label>
            <div class="phone" :class="{ bad: errs.phone }"><span>+998</span><input v-model="f.phone" placeholder="901234567" inputmode="tel" maxlength="12" /></div>
            <span v-if="errs.phone" class="err">{{ errs.phone }}</span></div>
          <div class="field"><label>Tug'ilgan sana <b>*</b></label><input v-model="f.birth_date" type="date" class="inp lg" :class="{ bad: errs.birth_date }" /><span v-if="errs.birth_date" class="err">{{ errs.birth_date }}</span></div>
        </div>
      </section>

      <section class="card">
        <header><i class="ic blue"><Icon name="card" :size="18" /></i><div><h4>Hujjatlar</h4><p>JShShIR va guvohnomalar — soliq tekshiruvi JShShIR bo'yicha</p></div></header>
        <div class="grid">
          <div class="field"><label>JShShIR <b>*</b></label><input v-model="f.pinfl" class="inp lg" :class="{ bad: errs.pinfl }" placeholder="12345678901234" maxlength="14" inputmode="numeric" />
            <span v-if="errs.pinfl" class="err">{{ errs.pinfl }}</span><span v-else class="hint">14 ta raqam, pasportdagi JShShIR</span></div>
          <div class="field"><label>Haydovchilik guvohnomasi seriyasi va raqami</label><input v-model="f.license_no" class="inp lg" placeholder="AB 1234567" /></div>
          <div class="field"><label>Transport hujjati seriyasi va raqami</label><input v-model="f.vehicle_doc" class="inp lg" placeholder="AAF 1234567" /></div>
        </div>
      </section>

      <section class="card">
        <header><i class="ic amber"><Icon name="bike" :size="18" /></i><div><h4>Transport</h4><p>Kuryer nimada yetkazadi</p></div></header>
        <div class="field"><label>Transport turi</label>
          <div class="chips"><button v-for="t in VEHICLES" :key="t.v" type="button" :class="{ on: f.vehicle === t.v }" @click="f.vehicle = t.v">{{ t.l }}</button></div></div>
        <div class="grid" style="margin-top:14px">
          <div class="field"><label>Davlat raqami</label><input v-model="f.plate" class="inp lg" placeholder="01A123BC" maxlength="10" /><span class="hint">8 ta belgi, bo'sh joysiz</span></div>
          <div class="field"><label>Mashina modeli</label><input v-model="f.car_model" class="inp lg" placeholder="Chevrolet Cobalt" /></div>
        </div>
      </section>

      <section class="card">
        <header><i class="ic green"><Icon name="building" :size="18" /></i><div><h4>Ish sozlamalari</h4><p>Status, smena va ish shahri</p></div></header>
        <div class="field"><label>Status <b>*</b></label>
          <div class="status">
            <label :class="{ on: f.status === 'blocked' }"><input v-model="f.status" type="radio" value="blocked" /><i />Nofaol</label>
            <label :class="{ on: f.status === 'active' }"><input v-model="f.status" type="radio" value="active" /><i />Faol</label>
          </div></div>
        <div class="grid" style="margin-top:14px">
          <div class="field"><label>Smena <b>*</b></label><select v-model="f.shift" class="inp lg"><option>08:00–20:00</option><option>09:00–21:00</option><option>10:00–22:00</option><option>11:00–23:00</option></select></div>
          <div class="field"><label>Shahar <b>*</b></label>
            <select v-model="f.city" class="inp lg" :class="{ bad: errs.city }"><option value="" disabled>Shahar</option><option v-for="c in CITIES" :key="c">{{ c }}</option></select>
            <span v-if="errs.city" class="err">{{ errs.city }}</span></div>
        </div>
      </section>
    </div>
    <div v-if="errs.form" class="err" style="margin-top:12px;font-size:13px">{{ errs.form }}</div>
    <template #footer><Btn @click="emit('close')">Bekor qilish</Btn><Btn variant="primary" :disabled="busy" @click="go">Saqlash</Btn></template>
  </Modal>
</template>
<style scoped>
.cards{display:grid;grid-template-columns:1fr 1fr;gap:14px;align-items:start}
.card{background:var(--surface);border:1px solid var(--line-2);border-radius:14px;padding:16px;box-shadow:0 1px 2px rgba(22,32,26,.05)}
.card>header{display:flex;gap:11px;align-items:center;padding:0 0 12px;margin-bottom:14px;border-bottom:1px solid var(--line-2)}
.card h4{font-size:14.5px;font-weight:700}.card p{font-size:12px;color:var(--muted);margin-top:1px}
.ic{width:36px;height:36px;border-radius:10px;display:grid;place-items:center;flex:none}
.ic.violet{background:var(--violet-soft);color:var(--violet)}.ic.blue{background:var(--blue-soft);color:var(--blue)}
.ic.amber{background:var(--amber-soft);color:var(--amber)}.ic.green{background:var(--teal-soft);color:var(--teal)}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px 14px}
.field label{font-size:12.5px;font-weight:600;color:var(--ink)}.field label b{color:var(--red)}
.hint{font-size:11.5px;color:var(--muted)}
.inp.bad,.phone.bad{border-color:var(--red)}
.phone{display:flex;height:40px;border:1px solid var(--line);border-radius:9px;overflow:hidden;background:var(--surface)}
.phone span{display:grid;place-items:center;padding:0 12px;background:var(--surface-2);color:var(--muted);font-size:13px;font-weight:600;border-right:1px solid var(--line)}
.phone input{flex:1;min-width:0;border:0;outline:0;padding:0 11px;font-size:13px;background:transparent}
.phone:focus-within,.inp:focus{border-color:var(--brand);box-shadow:0 0 0 3px var(--brand-soft)}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chips button{border:1px solid var(--line);background:var(--surface);border-radius:999px;padding:8px 18px;font-size:13px;font-weight:500;color:var(--muted);cursor:pointer}
.chips button.on{background:var(--brand-soft);border-color:var(--brand);color:var(--ink);font-weight:600}
.status{display:flex;gap:22px;background:var(--surface-2);border:1px solid var(--line-2);border-radius:10px;padding:11px 14px}
.status label{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:600;color:var(--muted);cursor:pointer}
.status input{display:none}
.status i{width:9px;height:9px;border-radius:50%;background:var(--line)}
.status label.on{color:var(--ink)}.status label.on i{background:var(--teal)}
@media (max-width:860px){.cards,.grid{grid-template-columns:1fr}}
</style>
