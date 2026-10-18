<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { get, post, errMsg } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { money, moneyS } from '@/utils/format'
import { CASH_LIMIT } from '@/constants/statuses'
const p = defineProps<{ courierId?: number }>()
const emit = defineEmits<{ close: []; done: [] }>()
const ui = useUiStore()
const list = ref<any[]>([])
const cid = ref<number | ''>(p.courierId ?? '')
const type = ref('topup'), amount = ref(''), note = ref(''), err = ref(''), busy = ref(false)
onMounted(async () => {
  const r = await get('/couriers', { status: 'all', sort: 'balance', dir: 'asc' })
  list.value = (r.items as any[]).filter((c) => c.account_status === 'active').sort((a, b) => a.balance - b.balance)
  if (cid.value === '' && list.value.length) cid.value = list.value[0].id
  fillDebt()
})
const cur = computed(() => list.value.find((c) => c.id === cid.value))
function fillDebt() { if (type.value === 'topup' && cur.value && cur.value.balance < 0) amount.value = String(-cur.value.balance) }
watch([cid, type], fillDebt)
async function go() {
  err.value = ''
  const n = Number(String(amount.value).replace(/\s/g, ''))
  if (!n || n <= 0) { err.value = 'Summani kiriting'; return }
  busy.value = true
  try {
    await post(`/couriers/${cid.value}/ledger`, { type: type.value, amount: n, note: note.value })
    ui.toast(`${cur.value?.full_name}: balans yangilandi`); emit('done'); emit('close')
  } catch (e) { err.value = errMsg(e) } finally { busy.value = false }
}
</script>
<template>
  <Modal title="Balansni to'ldirish" sub="Kuryer naqd pulni topshirganda yoki tuzatish kiritilganda" @close="emit('close')">
    <div class="form-grid">
      <div class="field full"><label>Kuryer</label>
        <select v-model="cid" class="inp"><option v-for="c in list" :key="c.id" :value="c.id">{{ c.full_name }} · #{{ c.number }} · {{ money(c.balance) }} so'm</option></select></div>
      <div class="field"><label>Operatsiya</label>
        <select v-model="type" class="inp"><option value="topup">Naqd pul topshirdi (+)</option><option value="fix">Bonus / tuzatish (+)</option><option value="payout">Maosh to'lab berildi (−)</option><option value="penalty">Jarima (−)</option></select></div>
      <div class="field"><label>Summa</label><input v-model="amount" class="inp" inputmode="numeric" /><span v-if="err" class="err">{{ err }}</span></div>
      <div class="field full"><label>Izoh</label><input v-model="note" class="inp" placeholder="Masalan, ofisda kassaga topshirdi" /></div>
    </div>
    <p v-if="cur" style="margin-top:12px;font-size:13px" class="muted">Joriy balans: <b :class="{ red: cur.balance < 0 }">{{ moneyS(cur.balance) }}</b>
      <span v-if="cur.balance < -CASH_LIMIT" class="red"> · naqd limitidan oshgan</span></p>
    <template #footer><Btn @click="emit('close')">Bekor qilish</Btn><Btn variant="primary" :disabled="busy" @click="go">Saqlash</Btn></template>
  </Modal>
</template>
