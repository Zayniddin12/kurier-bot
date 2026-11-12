<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { get, post, errMsg } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import { useDrawer } from '@/utils/drawer'
import { useLoad } from '@/utils/useLoad'
import { comma, dmyhms } from '@/utils/format'

const ui = useUiStore(), auth = useAuthStore(), drawer = useDrawer()
const PER = 20
const f = reactive({ status: '', method: '', restaurant_id: '', q: '', from: '', to: '' })
const applied = ref({ ...f })
const page = ref(1)
let t: any
watch(f, () => { clearTimeout(t); t = setTimeout(() => { applied.value = { ...f }; page.value = 1 }, 300) })

const { data, loading, error, reload } = useLoad<any>(() => {
  const a = applied.value
  return get('/payments', { status: a.status || undefined, method: a.method || undefined, restaurant_id: a.restaurant_id || undefined,
    q: a.q.trim() || undefined, from: a.from || undefined, to: a.to || undefined, page: page.value, per_page: PER })
}, [applied, page], ['order.updated'])
const items = computed(() => data.value?.items || [])
const totalPages = computed(() => Math.max(1, Math.ceil((data.value?.total || 0) / PER)))
const tone = (s: string) => ({ paid: 'teal', pending: 'amber', refund_required: 'red', refunded: 'grey', cancelled: 'grey', expired: 'grey' } as any)[s] || 'grey'
const busyId = ref(0)

async function act(p: any, what: 'sync' | 'refund') {
  if (what === 'refund' && !confirm(`#${p.order_id} buyurtma to'lovi (${comma(p.amount)} so'm) mijozga qaytarilsinmi?`)) return
  busyId.value = p.id
  try { await post(`/payments/${p.id}/${what}`); ui.toast(what === 'refund' ? "To'lov qaytarildi" : 'Holat yangilandi'); reload(true) }
  catch (e) { ui.toast(errMsg(e), 'var(--red)') } finally { busyId.value = 0 }
}
</script>

<template>
  <div class="page">
    <div class="cards">
      <div class="c"><small>To'langan</small><b class="num">{{ comma(data?.summary?.paid?.amount ?? 0) }} so'm</b><span class="muted">{{ data?.summary?.paid?.count ?? 0 }} ta to'lov</span></div>
      <div class="c" :class="{ warn: data?.summary?.refund_required?.count }"><small>Qaytarish kerak</small><b class="num">{{ comma(data?.summary?.refund_required?.amount ?? 0) }} so'm</b><span class="muted">{{ data?.summary?.refund_required?.count ?? 0 }} ta to'lov</span></div>
      <div class="c"><small>Jami urinishlar</small><b class="num">{{ comma(data?.total ?? 0) }}</b><span class="muted">Multicard · bitta kassa</span></div>
    </div>

    <div class="flt">
      <input v-model="f.q" class="inp" placeholder="Buyurtma # yoki invoice" />
      <select v-model="f.restaurant_id" class="inp wide"><option value="">Barcha restoranlar</option><option v-for="r in data?.restaurants || []" :key="r.value" :value="r.value">{{ r.label }}</option></select>
      <select v-model="f.status" class="inp"><option value="">Holati</option><option v-for="s in data?.statuses || []" :key="s.value" :value="s.value">{{ s.label }}</option></select>
      <select v-model="f.method" class="inp"><option value="">Usuli</option><option v-for="m in data?.methods || []" :key="m.value" :value="m.value">{{ m.label }}</option></select>
      <div class="dates"><input v-model="f.from" type="date" /><span>—</span><input v-model="f.to" type="date" /></div>
    </div>

    <Panel flush>
      <ErrorBox v-if="error && !data" :message="error" @retry="reload()" />
      <div v-else-if="loading && !data" style="padding:16px"><Skeleton :h="44" :n="6" /></div>
      <template v-else-if="data">
        <DataTable v-if="items.length">
          <thead><tr><th>#</th><th>Restoran</th><th>Buyurtma</th><th>Usul</th><th class="r">Summa</th><th>Holati</th><th>Karta</th><th>Yaratilgan</th><th>To'langan</th><th /></tr></thead>
          <tbody>
            <tr v-for="p in items" :key="p.id">
              <td class="muted num">{{ p.id }}</td>
              <td><a class="lnk" href="#" @click.prevent="drawer.open('restaurant', p.restaurant.id)">{{ p.restaurant.name }}</a></td>
              <td><a class="lnk num" href="#" @click.prevent="drawer.open('order', p.order_id)">#{{ p.order_id }}</a><div class="s">{{ p.invoice_id }}</div></td>
              <td>{{ p.method }}<span v-if="p.ps" class="s"> · {{ p.ps }}</span></td>
              <td class="r num">{{ comma(p.amount) }}</td>
              <td><Pill :tone="tone(p.status)">{{ p.status_label }}</Pill></td>
              <td class="num">{{ p.card || '—' }}</td>
              <td class="num">{{ dmyhms(p.created_at) }}</td>
              <td class="num">{{ p.paid_at ? dmyhms(p.paid_at) : '—' }}</td>
              <td class="act">
                <a v-if="p.receipt_url" :href="p.receipt_url" target="_blank" rel="noopener" class="lnk">Chek</a>
                <Btn v-if="p.status === 'pending'" sm :disabled="busyId === p.id" @click="act(p, 'sync')">Tekshirish</Btn>
                <Btn v-if="!auth.isStaff && (p.status === 'paid' || p.status === 'refund_required')" sm :disabled="busyId === p.id" @click="act(p, 'refund')">Qaytarish</Btn>
              </td>
            </tr>
          </tbody>
        </DataTable>
        <Empty v-else title="To'lov topilmadi" text="Filtrlarni o'zgartirib ko'ring" />
        <div class="pager">
          <span class="muted num">{{ data.total ? (page - 1) * PER + 1 : 0 }}–{{ Math.min(page * PER, data.total) }} / {{ comma(data.total) }}</span><span style="flex:1" />
          <Btn sm :disabled="page <= 1" @click="page--">Oldingi</Btn><span class="num">{{ page }} / {{ totalPages }}</span><Btn sm :disabled="page >= totalPages" @click="page++">Keyingi</Btn>
        </div>
      </template>
    </Panel>
  </div>
</template>

<style scoped>
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.c{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:16px 20px;display:flex;flex-direction:column;gap:4px}
.c small{color:var(--muted);font-size:13px}.c b{font-size:22px}.c.warn{border-color:var(--red)}
.flt{display:flex;flex-wrap:wrap;gap:8px;align-items:center}.flt .wide{min-width:200px}
.dates{display:flex;align-items:center;gap:6px}
.s{font-size:11.5px;color:var(--faint)}.act{display:flex;gap:6px;align-items:center;justify-content:flex-end;white-space:nowrap}
.pager{display:flex;align-items:center;gap:10px;padding:12px 16px;border-top:1px solid var(--line)}
@media (max-width:800px){.cards{grid-template-columns:1fr}}
</style>
