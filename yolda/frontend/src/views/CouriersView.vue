<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { get } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { useDrawer } from '@/utils/drawer'
import { useLoad } from '@/utils/useLoad'
import { money, moneyS, dmy } from '@/utils/format'
import { workLine, CASH_LIMIT } from '@/constants/statuses'
import IncomeModal from '@/components/modals/IncomeModal.vue'
import SalaryModal from '@/components/modals/SalaryModal.vue'
import TopupModal from '@/components/modals/TopupModal.vue'
import NewCourierModal from '@/components/modals/NewCourierModal.vue'
const router = useRouter(), drawer = useDrawer(), ui = useUiStore()
const f = reactive({ q: '', phone: '', pinfl: '', vehicle: '', status: 'all' })
const dq = reactive({ q: '', phone: '', pinfl: '' })
let t: any
watch(f, () => { clearTimeout(t); t = setTimeout(() => Object.assign(dq, { q: f.q, phone: f.phone, pinfl: f.pinfl }), 300) })
const sort = ref('work'), dir = ref('asc')
const { data, loading, error, reload } = useLoad<any>(
  () => get('/couriers', { q: dq.q || undefined, phone: dq.phone.replace(/\D/g, '') || undefined, pinfl: dq.pinfl || undefined, vehicle: f.vehicle || undefined, status: f.status, sort: sort.value, dir: dir.value }),
  [() => dq.q, () => dq.phone, () => dq.pinfl, () => f.vehicle, () => f.status, sort, dir], ['courier.updated', 'order.updated'])
const modal = ref<'' | 'income' | 'salary' | 'topup' | 'new'>('')
const cols: [string, string, string?][] = [['', '#'], ['name', 'Kuryer ismi'], ['phone', 'Telefon raqami'], ['pinfl', 'JShShIR (PINFL)'], ['vehicle', 'Transport turi'], ['balance', 'Balans', 'r'], ['today', 'Bugungi buyurtmalar', 'r'], ['work', 'Ishda'], ['status', 'Holat'], ['created', 'Yaratilgan'], ['', '']]
function setSort(k: string) { if (!k) return; if (sort.value === k) dir.value = dir.value === 'asc' ? 'desc' : 'asc'; else { sort.value = k; dir.value = 'asc' } }
const stats = computed(() => data.value?.stats)
const cards = computed(() => !stats.value ? [] : [
  { k: 'all', l: 'Jami kuryerlar', n: stats.value.total, s: "ro'yxatdan o'tgan", c: 'var(--ink)' },
  { k: 'line', l: 'Liniyada', n: stats.value.line, s: 'hozir ishda', c: 'var(--teal)' },
  { k: 'pause', l: 'Pauzada', n: stats.value.pause, s: 'vaqtincha buyurtma qabul qilmaydi', c: 'var(--amber)' },
  { k: 'blocked', l: 'Nofaol', n: stats.value.inactive, s: "bloklangan yoki o'chirilgan", c: 'var(--red)' },
])
const quick = [
  { l: 'Onlayn kuryerlar xaritasi', i: 'pin', c: 'blue', go: () => router.push('/map') },
  { l: 'Kuryerlar daromadi hisoboti', i: 'chart', c: 'violet', go: () => (modal.value = 'income') },
  { l: 'Kuryerlar maoshini hisoblash', i: 'dollar', c: 'teal', go: () => (modal.value = 'salary') },
  { l: "Balansni to'ldirish", i: 'download', c: 'amber', go: () => (modal.value = 'topup') },
]
</script>

<template>
  <div class="page">
    <div class="top">
      <div class="crumb"><Icon name="home" :size="16" /> › <b>Kuryerlar</b></div><span class="sp" />
      <button v-for="q in quick" :key="q.l" class="qb" @click="q.go()"><span class="qi" :style="{ background: `var(--${q.c}-soft)`, color: `var(--${q.c})` }"><Icon :name="q.i" :size="16" /></span>{{ q.l }}</button>
    </div>
    <ErrorBox v-if="error && !data" :message="error" @retry="reload()" />
    <template v-else>
      <div class="cards">
        <button v-for="c in cards" :key="c.k" class="card" :class="{ on: f.status === c.k }" @click="f.status = c.k"><span>{{ c.l }}</span><b class="num" :style="{ color: c.c }">{{ c.n }}</b><small>{{ c.s }}</small></button>
      </div>
      <Panel>
        <div class="filters">
          <input v-model="f.q" class="inp lg" placeholder="Ism / familiya" /><input v-model="f.phone" class="inp lg" placeholder="Telefon raqami" /><input v-model="f.pinfl" class="inp lg" placeholder="JShShIR (PINFL)" />
          <select v-model="f.vehicle" class="inp lg"><option value="">Barcha transport</option><option value="Skuter">Skuter</option><option value="Avto">Avtomobil</option><option value="Velo">Velosiped</option><option value="Piyoda">Piyoda</option></select>
          <select v-model="f.status" class="inp lg"><option value="all">Barcha holatlar</option><option value="line">Liniyada</option><option value="pause">Pauzada</option><option value="offline">Oflayn</option><option value="blocked">Bloklangan</option></select>
          <Btn variant="primary" icon="plus" style="height:40px" @click="modal = 'new'">Kuryer qo'shish</Btn>
        </div>
        <div v-if="loading && !data" style="padding:16px"><Skeleton :h="40" :n="6" /></div>
        <DataTable v-else-if="data?.items.length">
          <thead><tr><th v-for="(c, i) in cols" :key="i" :class="[c[2], { sortable: c[0] }]" @click="setSort(c[0])">{{ c[1] }}<template v-if="c[0]"> <span :style="{ opacity: sort === c[0] ? 1 : .35 }">{{ sort === c[0] ? (dir === 'asc' ? '↑' : '↓') : '↕' }}</span></template></th></tr></thead>
          <tbody>
            <tr v-for="(c, i) in data.items" :key="c.id" class="click" @click="drawer.open('courier', c.id)">
              <td class="muted">{{ i + 1 }}</td>
              <td><a>{{ c.full_name }}</a><div class="s">#{{ c.number }}</div></td>
              <td class="num">{{ c.phone.replace(/(\d{2})(\d{3})(\d{2})(\d{2})/, '$1 $2 $3 $4') }}</td>
              <td class="num muted">{{ c.pinfl }}</td><td>{{ c.vehicle_name || c.vehicle }}</td>
              <td class="r num"><span :class="{ red: c.balance < 0 }">{{ money(c.balance) }}</span><div v-if="c.over_limit" class="s red">naqd limitidan oshgan</div></td>
              <td class="r num">{{ c.today_orders }}<div class="s">{{ money(c.today_amount) }}</div></td>
              <td><Pill :tone="workLine(c.work_status, c.account_status === 'blocked').tone">{{ c.account_status === 'blocked' ? 'Oflayn' : workLine(c.work_status).label }}</Pill><div class="s" :class="{ red: c.issue }">{{ c.issue ? c.issue.text : c.current_text }}</div></td>
              <td><Pill :tone="c.account_status === 'blocked' ? 'red' : 'teal'">{{ c.account_status === 'blocked' ? 'Bloklangan' : 'Faol' }}</Pill></td>
              <td class="muted">{{ dmy(c.created_at) }}</td>
              <td><Icon name="card" /></td>
            </tr>
          </tbody>
        </DataTable>
        <Empty v-else title="Kuryer topilmadi" text="Filtrlarni o'zgartiring" />
        <div v-if="data" class="foot"><span>{{ data.items.length }} ta kuryer</span><span class="sp" /><span>Kuryerlardagi naqd qarz: <b class="red">{{ moneyS(data.debt_total) }}</b></span></div>
      </Panel>
    </template>
    <IncomeModal v-if="modal === 'income'" @close="modal = ''" />
    <SalaryModal v-if="modal === 'salary'" @close="modal = ''" @done="reload(true)" />
    <TopupModal v-if="modal === 'topup'" @close="modal = ''" @done="reload(true)" />
    <NewCourierModal v-if="modal === 'new'" @close="modal = ''" @done="reload(true)" />
  </div>
</template>

<style scoped>
.top{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.crumb{display:flex;gap:6px;align-items:center;color:var(--muted)}.crumb b{color:var(--ink)}
.qb{height:40px;border:1px solid var(--line);background:var(--surface);border-radius:10px;display:flex;align-items:center;gap:8px;padding:0 12px 0 6px;font-size:13px;font-weight:600}
.qi{width:28px;height:28px;border-radius:8px;display:flex;align-items:center;justify-content:center}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.card{text-align:left;background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:14px 16px;display:flex;flex-direction:column;gap:2px}
.card.on{box-shadow:inset 0 0 0 1px var(--ink)}.card span{font-size:13px;font-weight:600}.card b{font-size:28px;font-weight:800}.card small{color:var(--muted);font-size:12px}
.filters{display:grid;grid-template-columns:repeat(5,1fr) auto;gap:10px;padding:16px;border-bottom:1px solid var(--line-2)}
.foot{display:flex;padding:12px 16px;border-top:1px solid var(--line-2);font-size:13px}
@media (max-width:1280px){.filters{grid-template-columns:repeat(3,1fr)}}
@media (max-width:1100px){.cards{grid-template-columns:repeat(2,1fr)}}
@media (max-width:520px){.filters{grid-template-columns:1fr}}
</style>
