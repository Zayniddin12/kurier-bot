<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { get } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import { useRestaurantsStore } from '@/stores/restaurants'
import { onLive } from '@/stores/live'
import { useDrawer } from '@/utils/drawer'
import { useLoad } from '@/utils/useLoad'
import { money, short, dmyhm, dec } from '@/utils/format'
const ui = useUiStore(), rs = useRestaurantsStore(), auth = useAuthStore(), drawer = useDrawer(), route = useRoute()
const period = ref<string>('today'), from = ref(''), to = ref('')
const status = ref((route.query.status as string) || 'all'), pay = ref(''), q = ref(''), dq = ref(''), page = ref(1)
const flash = ref<Set<number>>(new Set())
let t: any
watch(q, (v) => { clearTimeout(t); t = setTimeout(() => { dq.value = v; page.value = 1 }, 300) })
watch([period, from, to, status, pay, () => ui.restaurantId], () => { page.value = 1 })

const { data, loading, error, reload } = useLoad<any>(
  () => get('/orders', { period: period.value, from: period.value === 'range' ? from.value || undefined : undefined, to: period.value === 'range' ? to.value || undefined : undefined,
    restaurant_id: ui.restaurantId || undefined, status: status.value, pay: pay.value || undefined, q: dq.value || undefined, page: page.value, per_page: 20 }),
  [period, from, to, status, pay, dq, page, () => ui.restaurantId])
const items = computed(() => data.value?.items || [])
const s = computed(() => data.value?.summary)
const ch = computed(() => data.value?.chart)
const totalPages = computed(() => Math.max(1, Math.ceil((data.value?.total || 0) / 20)))

function matches(o: any) {
  if (period.value !== 'today' && period.value !== 'week' && period.value !== 'month') return false
  if (ui.restaurantId && o.restaurant.id !== ui.restaurantId) return false
  if (pay.value && o.pay_method !== pay.value) return false
  if (status.value === 'delivered' || status.value === 'cancelled') return false
  return !dq.value
}
onLive('order.created', (o) => {
  if (!data.value || page.value !== 1 || !matches(o)) return
  if (items.value.some((x: any) => x.id === o.id)) return
  data.value = { ...data.value, items: [o, ...items.value].slice(0, 20), total: data.value.total + 1 }
  flash.value.add(o.id); flash.value = new Set(flash.value)
  setTimeout(() => { flash.value.delete(o.id); flash.value = new Set(flash.value) }, 2000)
})
onLive('order.updated', (o) => {
  if (!data.value) return
  const i = items.value.findIndex((x: any) => x.id === o.id)
  if (i >= 0) { const arr = [...items.value]; arr[i] = o; data.value = { ...data.value, items: arr } }
})
</script>

<template>
  <div class="page">
    <Panel>
      <div class="filters">
        <div class="field"><label>Davr</label>
          <Seg v-model="period" :options="[{ value: 'today', label: 'Bugun' }, { value: 'yesterday', label: 'Kecha' }, { value: 'week', label: 'Hafta' }, { value: 'month', label: 'Oy' }, { value: 'range', label: 'Oraliq' }]" /></div>
        <template v-if="period === 'range'">
          <div class="field"><label>Dan</label><input v-model="from" type="date" class="inp" /></div>
          <div class="field"><label>Gacha</label><input v-model="to" type="date" class="inp" /></div>
        </template>
        <div class="field"><label>Restoran</label>
          <select class="inp" :value="ui.restaurantId ?? ''" :disabled="auth.isStaff" @change="ui.restaurantId = ($event.target as HTMLSelectElement).value ? Number(($event.target as HTMLSelectElement).value) : null">
            <option value="">Barcha restoranlar</option><option v-for="r in rs.items" :key="r.id" :value="r.id">{{ r.name }}</option></select></div>
        <div class="field"><label>Holat</label>
          <select v-model="status" class="inp"><option value="all">Barchasi</option><option value="active">Faol</option><option value="delivered">Yetkazildi</option><option value="cancelled">Bekor qilindi</option></select></div>
        <div class="field"><label>To'lov</label>
          <select v-model="pay" class="inp"><option value="">Barchasi</option><option>Payme</option><option>Naqd</option><option>Click</option><option>Karta</option></select></div>
        <div class="field grow"><label>Qidiruv</label><SearchInput v-model="q" placeholder="Raqam, mijoz, manzil yoki kuryer" /></div>
      </div>

      <ErrorBox v-if="error && !data" :message="error" @retry="reload()" />
      <div v-else-if="loading && !data" style="padding:16px"><Skeleton :h="40" :n="6" /></div>
      <template v-else-if="data">
        <div class="sum">
          <div><span>Buyurtmalar</span><b class="num">{{ s.orders }}</b></div>
          <div><span>Tushum</span><b class="num">{{ short(s.revenue) }} so'm</b></div>
          <div><span>O'rtacha chek</span><b class="num">{{ money(s.avg_check) }}</b></div>
          <div><span>Muvaffaqiyatli</span><b class="num">{{ dec(s.success_pct) }}%</b></div>
          <div><span>O'rtacha yetkazish</span><b class="num">{{ s.avg_delivery }} daq</b></div>
        </div>
        <div style="padding:8px 16px"><BarChart :height="150" :labels="ch.labels" :every="ch.mode === 'hours' ? 3 : Math.ceil(ch.labels.length / 14)"
          :series="[{ name: 'Yetkazildi', values: ch.delivered, color: 'var(--teal)' }, { name: 'Boshqa', values: ch.other, color: 'var(--red)' }]" /></div>
        <DataTable v-if="items.length">
          <thead><tr><th>Buyurtma</th><th>Restoran</th><th>Mijoz va manzil</th><th>Kuryer</th><th class="r">Summa</th><th>To'lov</th><th>Yetkazish</th><th>Holat</th></tr></thead>
          <tbody>
            <tr v-for="o in items" :key="o.id" class="click" :class="{ flash: flash.has(o.id) }" @click="drawer.open('order', o.id)">
              <td><b class="num">#{{ o.id }}</b><div class="s">{{ dmyhm(o.created_at) }}</div></td>
              <td><div class="row" style="gap:8px"><RestLogo :name="o.restaurant.name" :color="o.restaurant.color" /><span>{{ o.restaurant.name }}</span></div></td>
              <td class="wrap"><b>{{ o.customer_name }}</b><div class="s">{{ o.district }}, {{ o.address }}</div></td>
              <td><div v-if="o.courier" class="row" style="gap:8px"><Avatar :seed="o.courier.avatar_seed" :female="o.courier.is_female" :size="26" />{{ o.courier.name }}</div><span v-else class="faint">—</span></td>
              <td class="r num">{{ money(o.total) }}</td>
              <td>{{ o.pay_method }}<div class="s">{{ o.pay_status_text }}</div></td>
              <td class="num"><b v-if="o.delivery_minutes != null" :class="{ red: o.is_late }">{{ o.delivery_minutes }} daq</b><span v-else class="faint">—</span></td>
              <td><Pill :tone="o.status_color">{{ o.status_text }}</Pill></td>
            </tr>
          </tbody>
        </DataTable>
        <Empty v-else title="Bu filtr bo'yicha buyurtma yo'q" text="Davrni kengaytiring yoki boshqa restoranni tanlang" />
        <div class="pager">
          <span class="muted num">{{ data.total ? (page - 1) * 20 + 1 : 0 }}–{{ Math.min(page * 20, data.total) }} / {{ data.total }}</span><span class="sp" />
          <Btn sm :disabled="page <= 1" @click="page--">Oldingi</Btn><span class="num">{{ page }} / {{ totalPages }}</span><Btn sm :disabled="page >= totalPages" @click="page++">Keyingi</Btn>
        </div>
      </template>
    </Panel>
  </div>
</template>

<style scoped>
.filters{display:flex;flex-wrap:wrap;gap:12px;padding:16px;align-items:flex-end;border-bottom:1px solid var(--line-2)}
.grow{flex:1;min-width:220px;max-width:300px}
.sum{display:grid;grid-template-columns:repeat(5,1fr);border-bottom:1px solid var(--line-2)}
.sum div{padding:12px 16px;display:flex;flex-direction:column}.sum span{font-size:12px;color:var(--muted)}.sum b{font-size:19px}
.pager{display:flex;align-items:center;gap:10px;padding:12px 16px;border-top:1px solid var(--line-2)}
@media (max-width:1100px){.sum{grid-template-columns:repeat(3,1fr)}}
@media (max-width:520px){.sum{grid-template-columns:repeat(2,1fr)}}
</style>
