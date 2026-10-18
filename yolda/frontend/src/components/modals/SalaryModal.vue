<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { get, post, errMsg } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { money, moneyS, dm } from '@/utils/format'
const emit = defineEmits<{ close: []; done: [] }>()
const ui = useUiStore()
const d = ref<any>(null)
const load = async () => { d.value = await get('/reports/salary') }
onMounted(load)
async function settle(r: any) {
  try { const x = await post(`/couriers/${r.courier.id}/settle`); ui.toast(`${r.courier.name}: ${moneyS(x.paid)} to'landi`); await load(); emit('done') } catch (e) { ui.toast(errMsg(e), 'var(--red)') }
}
async function all() {
  if (!confirm(`Hammasiga ${moneyS(d.value.total_payable)} to'lansinmi?`)) return
  try { const x = await post('/couriers/settle-all'); ui.toast(`${x.count} kuryerga ${moneyS(x.paid_total)} to'landi`); await load(); emit('done') } catch (e) { ui.toast(errMsg(e), 'var(--red)') }
}
</script>
<template>
  <Modal wide title="Kuryerlar maoshini hisoblash" sub="Har bir kuryer uchun oxirgi hisob-kitobdan buyon" @close="emit('close')">
    <div v-if="d" class="box rules">Daromad har yetkazishda balansga avtomatik yoziladi: yetkazish haqining {{ Math.round((1 - d.rules.commission) * 100) }}% i. Har 10 ta yetkazish uchun bonus {{ money(d.rules.bonus_per_10) }} so'm, {{ d.rules.sla }} daqiqadan kechikkan har bir buyurtma uchun jarima {{ money(d.rules.late_fine) }} so'm. <b>To'lanadi</b> = balans + bonus − jarima; naqd qarzi bo'lsa avval qarz yopiladi.</div>
    <DataTable v-if="d" style="margin-top:10px">
      <thead><tr><th>Kuryer</th><th>Oxirgi hisob</th><th class="r">Yetkazdi</th><th class="r">Daromad</th><th class="r">Bonus (+)</th><th class="r">Jarima (−)</th><th class="r">Balans</th><th class="r">To'lanadi</th><th /></tr></thead>
      <tbody><tr v-for="r in d.items" :key="r.courier.id">
        <td><div class="row" style="gap:8px"><Avatar :seed="r.courier.avatar_seed" :female="r.courier.is_female" :size="26" />{{ r.courier.name }}</div></td>
        <td>{{ r.settled_at ? dm(r.settled_at) : '—' }}</td><td class="r num">{{ r.deliveries }}</td><td class="r num">{{ money(r.earned) }}</td>
        <td class="r num teal">{{ r.bonus ? '+' + money(r.bonus) : '—' }}</td><td class="r num red">{{ r.fine ? '−' + money(r.fine) : '—' }}</td>
        <td class="r num" :class="{ red: r.balance < 0 }">{{ money(r.balance) }}</td><td class="r num"><b>{{ money(r.payable) }}</b></td>
        <td class="r"><Btn v-if="r.payable > 0" sm variant="primary" @click="settle(r)">To'lash</Btn><span v-else class="red" style="font-size:12px">qarz bor</span></td></tr></tbody>
      <tfoot><tr><td colspan="7">Jami to'lanadi</td><td class="r num">{{ moneyS(d.total_payable) }}</td><td class="r"><Btn sm variant="dark" @click="all">Hammasini to'lash</Btn></td></tr></tfoot>
    </DataTable>
    <Skeleton v-else :h="30" :n="5" />
  </Modal>
</template>
<style scoped>.rules{font-size:12.5px;color:var(--muted)}</style>
