<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { get } from '@/api/client'
import { useDrawer } from '@/utils/drawer'
import { useLoad } from '@/utils/useLoad'
import { comma, dmyhms } from '@/utils/format'
import FinanceCards from '@/components/FinanceCards.vue'

const drawer = useDrawer()
const PER = 20
const f = reactive({ courier_id: '', q: '', pinfl: '', desc: '', kind: '', reason: '', from: '', to: '' })
const applied = ref({ ...f })
const page = ref(1)
let t: any
watch(f, () => { clearTimeout(t); t = setTimeout(() => { applied.value = { ...f }; page.value = 1 }, 300) })

const { data, loading, error, reload } = useLoad<any>(
  () => {
    const a = applied.value
    return get('/finance/couriers', {
      courier_id: a.courier_id.trim() || undefined, q: a.q.trim() || undefined, pinfl: a.pinfl.trim() || undefined,
      desc: a.desc.trim() || undefined, kind: a.kind || undefined, reason: a.reason || undefined,
      from: a.from || undefined, to: a.to || undefined, page: page.value, per_page: PER,
    })
  }, [applied, page])
const items = computed(() => data.value?.items || [])
const totalPages = computed(() => Math.max(1, Math.ceil((data.value?.total || 0) / PER)))
</script>

<template>
  <div class="page">
    <div class="fin-crumb"><Icon name="home" :size="16" /><span class="sl">›</span><span>Barcha haydovchi tranzaksiyalari</span></div>
    <FinanceCards :summary="data?.summary" />

    <div class="fin-filters">
      <input v-model="f.courier_id" class="inp" inputmode="numeric" placeholder="Haydovchi ID" />
      <input v-model="f.q" class="inp" placeholder="Kuryer ismi" />
      <input v-model="f.pinfl" class="inp" inputmode="numeric" placeholder="PINFL (JSHSHIR)" />
      <input v-model="f.desc" class="inp" placeholder="Tavsif" />
      <select v-model="f.kind" class="inp"><option value="">Turi</option><option value="income">Daromad</option><option value="expense">Xarajat</option></select>
      <select v-model="f.reason" class="inp wide"><option value="">Sababi</option><option v-for="r in data?.reasons || []" :key="r.value" :value="r.value">{{ r.label }}</option></select>
      <div class="dates"><input v-model="f.from" type="date" title="Sana oralig'i: dan" /><span>—</span><input v-model="f.to" type="date" title="Sana oralig'i: gacha" /></div>
    </div>

    <Panel flush>
      <div class="fin-head"><Icon name="truck" :size="22" /><span>Barcha haydovchi tranzaksiyalari</span><span class="fin-count num">{{ comma(data?.total ?? 0) }}</span></div>
      <ErrorBox v-if="error && !data" :message="error" @retry="reload()" />
      <div v-else-if="loading && !data" style="padding:16px"><Skeleton :h="44" :n="6" /></div>
      <template v-else-if="data">
        <DataTable v-if="items.length" class="fin-t">
          <thead><tr><th>#</th><th>Haydovchi</th><th>PINFL (JSHSHIR)</th><th>Turi</th><th class="r">Summa</th><th>Sababi</th><th>Tavsif</th><th>Yaratilgan vaqti</th><th class="r">Tranzaksiyadan keyingi balans</th><th>Chek</th></tr></thead>
          <tbody>
            <tr v-for="(e, i) in items" :key="e.id">
              <td class="muted num">{{ (page - 1) * PER + i + 1 }}</td>
              <td><a class="lnk" href="#" @click.prevent="drawer.open('courier', e.courier.id)">{{ e.courier.name }}</a><div class="s">ID {{ e.courier.number }}</div></td>
              <td class="num">{{ e.pinfl }}</td>
              <td><Pill :tone="e.kind === 'income' ? 'teal' : 'red'">{{ e.kind === 'income' ? 'Daromad' : 'Xarajat' }}</Pill></td>
              <td class="r num" :class="e.kind === 'income' ? 'in' : 'out'">{{ comma(e.amount, true) }}</td>
              <td>{{ e.reason_label }}</td>
              <td><div class="desc" :title="e.description">{{ e.description || '—' }}</div></td>
              <td class="num">{{ dmyhms(e.created_at) }}</td>
              <td class="r num bal">{{ comma(e.balance_after) }}</td>
              <td class="faint">—</td>
            </tr>
          </tbody>
        </DataTable>
        <Empty v-else title="Tranzaksiya topilmadi" text="Filtrlarni o'zgartirib ko'ring" />
        <div class="fin-pager">
          <span class="muted num">{{ data.total ? (page - 1) * PER + 1 : 0 }}–{{ Math.min(page * PER, data.total) }} / {{ comma(data.total) }}</span><span style="flex:1" />
          <Btn sm :disabled="page <= 1" @click="page--">Oldingi</Btn><span class="num">{{ page }} / {{ totalPages }}</span><Btn sm :disabled="page >= totalPages" @click="page++">Keyingi</Btn>
        </div>
      </template>
    </Panel>
  </div>
</template>
