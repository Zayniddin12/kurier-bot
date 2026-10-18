<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { get } from '@/api/client'
import { money, dmy } from '@/utils/format'
const emit = defineEmits<{ close: [] }>()
const days = ref(1), d = ref<any>(null), error = ref('')
async function load() { try { d.value = await get('/reports/courier-income', { days: days.value }) } catch (e: any) { error.value = e.message } }
onMounted(load); watch(days, load)
function csv() {
  if (!d.value) return
  const rows = [['Kuryer', 'Yetkazdi', 'Buyurtmalar summasi', 'Naqd oldi', 'Kuryer daromadi', 'Komissiya'], ...d.value.items.map((r: any) => [r.courier.name, r.delivered, r.amount, r.cash, r.earned, r.commission])]
  const blob = new Blob(['﻿' + rows.map((r) => r.join(';')).join('\n')], { type: 'text/csv' })
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `kuryer-daromadi-${days.value}kun.csv`; a.click()
}
</script>
<template>
  <Modal wide title="Kuryerlar daromadi hisoboti" :sub="d ? `${dmy(d.from)} — ${dmy(d.to)} · yetkazilgan buyurtmalar bo'yicha` : ''" @close="emit('close')">
    <div class="row" style="margin-bottom:10px"><Seg v-model="days" :options="[{ value: 1, label: 'Bugun' }, { value: 7, label: '7 kun' }, { value: 30, label: '30 kun' }]" /><span class="sp" /><Btn sm icon="download" @click="csv">CSV yuklab olish</Btn></div>
    <DataTable v-if="d">
      <thead><tr><th>Kuryer</th><th class="r">Yetkazdi</th><th class="r">Buyurtmalar summasi</th><th class="r">Naqd oldi</th><th class="r">Kuryer daromadi</th><th class="r">Komissiya</th></tr></thead>
      <tbody><tr v-for="r in d.items" :key="r.courier.id"><td><div class="row" style="gap:8px"><Avatar :seed="r.courier.avatar_seed" :female="r.courier.is_female" :size="26" />{{ r.courier.name }}</div></td>
        <td class="r num">{{ r.delivered }}</td><td class="r num">{{ money(r.amount) }}</td><td class="r num">{{ money(r.cash) }}</td><td class="r num"><b>{{ money(r.earned) }}</b></td><td class="r num muted">{{ money(r.commission) }}</td></tr></tbody>
      <tfoot><tr><td>Jami</td><td class="r num">{{ d.totals.delivered }}</td><td class="r num">{{ money(d.totals.amount) }}</td><td class="r num">{{ money(d.totals.cash) }}</td><td class="r num">{{ money(d.totals.earned) }}</td><td class="r num">{{ money(d.totals.commission) }}</td></tr></tfoot>
    </DataTable>
    <Skeleton v-else :h="30" :n="5" />
  </Modal>
</template>
