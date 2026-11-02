<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { get } from '@/api/client'
import { useDrawer } from '@/utils/drawer'
import { useLoad } from '@/utils/useLoad'
import { comma, dmyhms } from '@/utils/format'
import FinanceCards from '@/components/FinanceCards.vue'

const drawer = useDrawer()
const PER = 20
const f = reactive({ restaurant_id: '', q: '', desc: '', kind: '', type: '', creator: '', from: '', to: '' })
const applied = ref({ ...f })
const page = ref(1)
let t: any
watch(f, () => { clearTimeout(t); t = setTimeout(() => { applied.value = { ...f }; page.value = 1 }, 300) })

const { data, loading, error, reload } = useLoad<any>(
  () => {
    const a = applied.value
    return get('/finance/vendors', {
      restaurant_id: a.restaurant_id.trim() || undefined, q: a.q.trim() || undefined, desc: a.desc.trim() || undefined,
      kind: a.kind || undefined, type: a.type || undefined, creator: a.creator || undefined,
      from: a.from || undefined, to: a.to || undefined, page: page.value, per_page: PER,
    })
  }, [applied, page])
const items = computed(() => data.value?.items || [])
const totalPages = computed(() => Math.max(1, Math.ceil((data.value?.total || 0) / PER)))
</script>

<template>
  <div class="page">
    <div class="fin-crumb"><Icon name="home" :size="16" /><span class="sl">›</span><span>Barcha vendor tranzaksiyalari</span></div>
    <FinanceCards :summary="data?.summary" />

    <div class="fin-filters">
      <input v-model="f.restaurant_id" class="inp" inputmode="numeric" placeholder="Shartnoma ID" />
      <input v-model="f.q" class="inp" placeholder="Qisqa nomi" />
      <input v-model="f.desc" class="inp" placeholder="Tavsif" />
      <select v-model="f.kind" class="inp"><option value="">Yo'nalishi</option><option value="income">Daromad</option><option value="expense">Xarajat</option></select>
      <select v-model="f.type" class="inp wide"><option value="">Turi</option><option v-for="r in data?.types || []" :key="r.value" :value="r.value">{{ r.label }}</option></select>
      <select v-model="f.creator" class="inp wide"><option value="">Kim yaratdi</option><option v-for="r in data?.creators || []" :key="r.value" :value="r.value">{{ r.label }}</option></select>
      <div class="dates"><input v-model="f.from" type="date" title="Sana oralig'i: dan" /><span>—</span><input v-model="f.to" type="date" title="Sana oralig'i: gacha" /></div>
    </div>

    <Panel flush>
      <div class="fin-head"><Icon name="building" :size="22" /><span>Barcha vendor tranzaksiyalari</span><span class="fin-count num">{{ comma(data?.total ?? 0) }}</span></div>
      <ErrorBox v-if="error && !data" :message="error" @retry="reload()" />
      <div v-else-if="loading && !data" style="padding:16px"><Skeleton :h="44" :n="6" /></div>
      <template v-else-if="data">
        <DataTable v-if="items.length" class="fin-t">
          <thead><tr><th>#</th><th>Shartnoma</th><th>Yo'nalishi</th><th>Turi</th><th class="r">Summa</th><th>Kim yaratdi</th><th>Tavsif</th><th>Yaratilgan vaqti</th><th class="r">Balans</th></tr></thead>
          <tbody>
            <tr v-for="(e, i) in items" :key="e.id">
              <td class="muted num">{{ (page - 1) * PER + i + 1 }}</td>
              <td><a class="lnk" href="#" @click.prevent="drawer.open('restaurant', e.restaurant.id)">{{ e.restaurant.name }}</a><div class="s">ID {{ e.restaurant.id }}</div></td>
              <td><Pill :tone="e.kind === 'income' ? 'teal' : 'red'">{{ e.kind === 'income' ? 'Daromad' : 'Xarajat' }}</Pill></td>
              <td><Pill :tone="e.type_color === 'green' ? 'teal' : e.type_color">{{ e.type_label }}</Pill></td>
              <td class="r num" :class="e.kind === 'income' ? 'in' : 'out'">{{ comma(e.amount, true) }}</td>
              <td>{{ e.creator }}</td>
              <td><div class="desc" :title="e.description">{{ e.description || '—' }}</div></td>
              <td class="num">{{ dmyhms(e.created_at) }}</td>
              <td class="r num bal">{{ comma(e.balance_after) }}</td>
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
