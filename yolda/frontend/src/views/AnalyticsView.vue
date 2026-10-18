<script setup lang="ts">
import { computed, ref } from 'vue'
import { get } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { useRestaurantsStore } from '@/stores/restaurants'
import { useLoad } from '@/utils/useLoad'
import { short, dmy, dec } from '@/utils/format'
import { PAY_COLORS } from '@/constants/statuses'
const ui = useUiStore(), rs = useRestaurantsStore()
const days = ref(7)
const { data: d, loading, error, reload } = useLoad<any>(() => get('/analytics', { days: days.value, restaurant_id: ui.restaurantId || undefined }), [days, () => ui.restaurantId])
const rname = computed(() => rs.byId[ui.restaurantId!]?.name || 'barcha restoranlar')
const maxRev = computed(() => Math.max(1, ...(d.value?.restaurants || []).map((r: any) => r.revenue)))
const maxCancel = computed(() => Math.max(1, ...(d.value?.cancel_reasons || []).map((r: any) => r.count)))
</script>
<template>
  <div class="page">
    <div class="row" style="flex-wrap:wrap"><Seg v-model="days" :options="[{ value: 7, label: '7 kun' }, { value: 14, label: '14 kun' }, { value: 30, label: '30 kun' }]" />
      <span v-if="d" class="muted">{{ dmy(d.range.from) }} — {{ dmy(d.range.to) }} · {{ rname }}</span></div>
    <ErrorBox v-if="error && !d" :message="error" @retry="reload()" />
    <div v-else-if="loading && !d" class="grid2"><Skeleton v-for="i in 6" :key="i" :h="240" /></div>
    <div v-else-if="d" class="grid2">
      <Panel title="Kunlik buyurtmalar"><template #actions><Legend :items="[{ label: 'Yetkazildi', color: 'var(--teal)' }, { label: 'Bekor', color: 'var(--red)' }]" /></template>
        <BarChart :height="230" :labels="d.daily.labels" :every="Math.ceil(d.daily.labels.length / 12)" :series="[{ name: 'Yetkazildi', values: d.daily.delivered, color: 'var(--teal)' }, { name: 'Bekor', values: d.daily.cancelled, color: 'var(--red)' }]" /></Panel>
      <Panel title="Tushum, mln so'm"><LineChart :labels="d.revenue_mln.labels" :every="Math.ceil(d.revenue_mln.labels.length / 12)" :series="[{ name: 'Tushum', values: d.revenue_mln.values, color: 'var(--brand)', fill: true }]" :fmt="(n: number) => dec(n)" /></Panel>
      <Panel title="Soatlar kesimida o'rtacha yetkazish vaqti"><template #actions>daqiqa</template>
        <BarChart :height="230" :labels="d.hourly_avg_delivery.labels" :every="3" :series="[{ name: 'O\'rtacha', values: d.hourly_avg_delivery.values, color: 'var(--ink)' }]" /></Panel>
      <Panel title="Restoranlar tushumi">
        <div class="list"><div v-for="r in d.restaurants" :key="r.id" class="li"><RestLogo :name="r.name" :color="r.color" /><div class="lm"><div class="row"><b>{{ r.name }}</b><span class="faint">{{ r.count }} ta</span><span class="sp" /><b class="num">{{ short(r.revenue) }}</b></div>
          <div class="b6"><i :style="{ width: (r.revenue / maxRev) * 100 + '%', background: r.color }" /></div></div></div></div></Panel>
      <Panel title="Eng faol kuryerlar" flush>
        <DataTable><thead><tr><th>Kuryer</th><th class="r">Yetkazdi</th><th class="r">O'rt. vaqt</th><th class="r">Mijoz bahosi</th></tr></thead>
          <tbody><tr v-for="c in d.couriers" :key="c.id"><td><div class="row" style="gap:8px"><Avatar :seed="c.avatar_seed" :female="c.is_female" :size="26" />{{ c.name }}</div></td><td class="r num">{{ c.delivered }}</td><td class="r num">{{ c.avg_minutes }} daq</td><td class="r num">★ {{ c.rating?.toFixed ? c.rating.toFixed(2) : c.rating }}</td></tr></tbody></DataTable></Panel>
      <Panel title="To'lov turlari va bekor sabablari">
        <div class="stack"><i v-for="p in d.payments" :key="p.method" :style="{ width: p.percent + '%', background: PAY_COLORS[p.method] }" /></div>
        <Legend :items="d.payments.map((p: any) => ({ label: `${p.method} ${Math.round(p.percent)}%`, color: PAY_COLORS[p.method] }))" style="margin:10px 0 16px" />
        <div v-for="r in d.cancel_reasons" :key="r.reason" class="li" style="margin-bottom:10px"><div class="lm"><div class="row"><span>{{ r.reason }}</span><span class="sp" /><b class="num">{{ r.count }}</b></div><div class="b6"><i :style="{ width: (r.count / maxCancel) * 100 + '%', background: 'var(--red)' }" /></div></div></div>
      </Panel>
    </div>
  </div>
</template>
<style scoped>
.list{display:flex;flex-direction:column;gap:12px}.li{display:flex;gap:10px;align-items:flex-start}.lm{flex:1;min-width:0}.lm b{font-size:13px}
.b6{height:6px;background:var(--line-2);border-radius:3px;overflow:hidden;margin-top:5px}.b6 i{display:block;height:100%}
.stack{display:flex;height:18px;border-radius:9px;overflow:hidden;background:var(--grey-soft)}.stack i{display:block;height:100%}
</style>
