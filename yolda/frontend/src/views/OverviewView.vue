<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { get } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { useLoad, usePeriodParams } from '@/utils/useLoad'
import { useDrawer } from '@/utils/drawer'
import { money, short, dec } from '@/utils/format'
const ui = useUiStore(), router = useRouter(), drawer = useDrawer()
const params = usePeriodParams()
const { data: d, loading, error, reload } = useLoad<any>(() => get('/overview', params()), [() => ui.period, () => ui.from, () => ui.to, () => ui.restaurantId], ['order.created', 'order.updated', 'courier.updated', 'issue.opened', 'issue.closed'])

const k = computed(() => d.value?.kpis)
const cmp = computed(() => d.value?.period.compare_label || '')
const delta = (x: any) => (x?.delta_pct == null ? '' : `${x.delta_pct > 0 ? '+' : ''}${Math.round(x.delta_pct)}% ${cmp.value}`)
const dcls = (x: any) => (x?.delta_pct == null ? 'muted' : x.good ? 'teal' : 'red')
const chart = computed(() => d.value?.chart)
const isHours = computed(() => chart.value?.mode === 'hours')
const flow = computed(() => d.value?.flow)
const c = computed(() => d.value?.couriers)
const maxRest = computed(() => Math.max(1, ...(d.value?.restaurants || []).map((r: any) => r.count)))
const maxTop = computed(() => Math.max(1, ...(d.value?.top_couriers || []).map((r: any) => r.delivered)))
const flowRows = computed(() => !flow.value ? [] : [
  { n: flow.value.searching, t: 'Kuryer qidirilmoqda', s: 'Tizim avtomatik biriktiradi', c: 'var(--red)', go: () => router.push('/orders?status=new') },
  { n: flow.value.pickup, t: "Kuryer restoranga yo'lda", s: 'Taom tayyorlanmoqda', c: 'var(--blue)', go: () => { ui.mapFocus = { filter: 'pickup' }; router.push('/map') } },
  { n: flow.value.delivering, t: "Mijozga yo'lda", s: 'Yetkazib berilmoqda', c: 'var(--teal)', go: () => { ui.mapFocus = { filter: 'delivering' }; router.push('/map') } },
  { n: flow.value.issues + flow.value.risk, t: 'Muammo yoki kechikish', s: `${flow.value.issues} ta muammo · ${flow.value.risk} ta kechikish xavfi`, c: 'var(--amber)', go: () => router.push('/alerts') },
])
const occRows = computed(() => !c.value ? [] : [
  { l: 'Umumiy', s: "Ro'yxatdagi barcha kuryerlar", n: c.value.total, c: 'var(--ink)' },
  { l: 'Onlayn', s: 'Smenada, ilovaga ulangan', n: c.value.online, c: 'var(--blue)' },
  { l: "Yo'lda", s: 'Restoranga yoki mijozga ketmoqda', n: c.value.on_route, c: 'var(--teal)' },
  { l: 'Smenada emas', s: 'Oflayn yoki bloklangan', n: c.value.offline, c: 'var(--faint)' }])
const periodShort = computed(() => ({ today: 'bugun', yesterday: 'kecha', week: '7 kun', month: '30 kun', range: 'davr' } as any)[ui.period])
</script>

<template>
  <div class="page">
    <ErrorBox v-if="error && !d" :message="error" @retry="reload()" />
    <template v-else-if="loading && !d">
      <Skeleton :h="90" /><Skeleton :h="260" /><Skeleton :h="200" />
    </template>
    <template v-else-if="d">
      <Panel>
        <div class="kpis">
          <div class="k"><span>Buyurtmalar</span><b class="num">{{ k.orders.value }}</b><small :class="dcls(k.orders)">{{ delta(k.orders) }}</small></div>
          <div class="k"><span>Hozir faol</span><b class="num">{{ k.active.value }}</b><small :class="k.active.searching ? 'red' : 'muted'">{{ k.active.searching ? `${k.active.searching} tasiga kuryer qidirilmoqda` : '' }}</small></div>
          <div class="k"><span>Yetkazildi</span><b class="num">{{ k.delivered.value }}</b><small :class="dcls(k.delivered)">{{ delta(k.delivered) }}</small></div>
          <div class="k"><span>Bekor qilindi</span><b class="num">{{ k.cancelled.value }} <em>{{ dec(k.cancelled.rate) }}%</em></b><small class="muted">Me'yor {{ k.cancelled.norm }}% gacha</small></div>
          <div class="k"><span>O'rtacha yetkazish</span><b class="num">{{ k.avg_delivery.value }} daq</b>
            <small v-if="k.avg_delivery.late_count" class="red">{{ k.avg_delivery.late_count }} tasi {{ k.avg_delivery.sla }} daqiqadan oshgan</small><small v-else :class="dcls(k.avg_delivery)">{{ delta(k.avg_delivery) }}</small></div>
          <div class="k"><span>Tushum</span><b class="num">{{ short(k.revenue.value) }} <em>so'm</em></b><small :class="dcls(k.revenue)">{{ delta(k.revenue) }}</small></div>
        </div>
      </Panel>

      <div class="row2">
        <Panel :title="isHours ? 'Soatlar bo\'yicha buyurtmalar' : 'Kunlar bo\'yicha buyurtmalar'">
          <template #actions><Legend :items="[{ label: isHours ? 'Bugun' : 'Tanlangan davr', color: 'var(--brand)' }, { label: isHours ? 'Kecha' : 'Oldingi davr', color: 'var(--faint)' }]" /></template>
          <LineChart :labels="chart.labels" :every="isHours ? 3 : Math.ceil(chart.labels.length / 12)"
            :series="[{ name: 'Oldingi', values: chart.previous, color: 'var(--faint)', dashed: true }, { name: 'Joriy', values: chart.current, color: 'var(--brand)', fill: true }]" />
        </Panel>
        <Panel title="Faol buyurtmalar oqimi"><template #actions>jonli</template>
          <div class="flow">
            <div v-for="r in flowRows" :key="r.t" class="fr" @click="r.go()">
              <b class="num" :style="{ color: r.c }">{{ r.n }}</b>
              <div class="ft"><b>{{ r.t }}</b><small>{{ r.s }}</small></div>
              <div class="bar"><i :style="{ width: (flow.total ? (r.n / flow.total) * 100 : 0) + '%', background: r.c }" /></div>
            </div>
          </div>
        </Panel>
      </div>

      <div class="grid3">
        <Panel title="Kuryerlar bandligi">
          <template #actions><Btn sm @click="router.push('/couriers')">Batafsil</Btn></template>
          <div class="big"><b class="num">{{ c.online }}</b><span>/ {{ c.total }} kuryer onlayn</span></div>
          <div class="stack"><i :style="{ width: (c.total ? (c.on_route / c.total) * 100 : 0) + '%', background: 'var(--teal)' }" /><i :style="{ width: (c.total ? ((c.online - c.on_route) / c.total) * 100 : 0) + '%', background: 'var(--blue)' }" /></div>
          <div class="occ">
            <div v-for="o in occRows" :key="o.l" class="orow" @click="router.push('/couriers')">
              <i :style="{ background: o.c }" /><div class="ot"><b>{{ o.l }}</b><small>{{ o.s }}</small></div><b class="num">{{ o.n }}</b>
            </div>
          </div>
        </Panel>
        <Panel title="Restoranlar bo'yicha"><template #actions><Btn sm @click="router.push('/restaurants')">Hammasi</Btn></template>
          <div class="list">
            <div v-for="r in d.restaurants" :key="r.id" class="li" :style="{ opacity: ui.restaurantId && ui.restaurantId !== r.id ? .45 : 1 }">
              <RestLogo :name="r.name" :color="r.color" />
              <div class="lm"><div class="row"><b>{{ r.name }}</b><span class="sp" /><b class="num">{{ r.count }}</b></div><div class="b6"><i :style="{ width: (r.count / maxRest) * 100 + '%', background: r.color }" /></div></div>
            </div>
            <Empty v-if="!d.restaurants.length" title="Buyurtma yo'q" />
          </div>
        </Panel>
        <Panel title="Eng faol kuryerlar"><template #actions>{{ periodShort }}</template>
          <div class="list">
            <div v-for="(r, i) in d.top_couriers" :key="r.id" class="li click" @click="drawer.open('courier', r.id)">
              <span class="idx">{{ i + 1 }}</span><Avatar :seed="r.avatar_seed" :female="r.is_female" :size="30" />
              <div class="lm"><div class="row"><b>{{ r.name }}</b><span class="sp" /><b class="num">{{ r.delivered }}</b></div>
                <div class="b6"><i :style="{ width: (r.delivered / maxTop) * 100 + '%', background: 'var(--teal)' }" /></div>
                <small class="muted">{{ short(r.earned) }} so'm · o'rt. {{ r.avg_minutes }} daq <span v-if="r.late" class="red">· {{ r.late }} kechikkan</span></small></div>
            </div>
            <Empty v-if="!d.top_couriers.length" title="Yetkazish yo'q" text="Bu davrda yetkazilgan buyurtma topilmadi" />
          </div>
        </Panel>
      </div>
    </template>
  </div>
</template>

<style scoped>
.kpis{display:grid;grid-template-columns:repeat(6,1fr)}
.k{padding:16px 18px;border-right:1px solid var(--line-2);display:flex;flex-direction:column;gap:3px;min-width:0}.k:last-child{border:0}
.k span{font-size:12.5px;color:var(--muted)}.k b{font-size:26px;font-weight:700;line-height:1.15}.k em{font-size:13px;font-style:normal;color:var(--muted);font-weight:600}.k small{font-size:12px;font-weight:600;min-height:16px}
.row2{display:grid;grid-template-columns:1.7fr 1fr;gap:16px}
.flow{display:flex;flex-direction:column;gap:8px}
.fr{display:flex;align-items:center;gap:12px;background:var(--surface-2);border-radius:11px;padding:12px;cursor:pointer}
.fr>b{font-size:24px;min-width:34px;text-align:center}.ft{flex:1;min-width:0}.ft b{display:block;font-size:13.5px}.ft small{font-size:12px;color:var(--muted)}
.bar{width:34%;height:6px;border-radius:3px;background:var(--line);overflow:hidden}.bar i{display:block;height:100%}
.big{display:flex;align-items:baseline;gap:8px}.big b{font-size:30px;font-weight:800}.big span{color:var(--muted)}
.stack{display:flex;height:14px;border-radius:7px;background:var(--grey-soft);overflow:hidden;margin:10px 0 12px}.stack i{display:block;height:100%}
.occ{display:flex;flex-direction:column}.orow{display:flex;align-items:center;gap:10px;padding:8px 0;border-top:1px solid var(--line-2);cursor:pointer}
.orow>i{width:9px;height:9px;border-radius:50%}.ot{flex:1}.ot b{display:block;font-size:13px}.ot small{font-size:12px;color:var(--muted)}
.list{display:flex;flex-direction:column;gap:12px}.li{display:flex;gap:10px;align-items:flex-start}.li.click{cursor:pointer}
.lm{flex:1;min-width:0}.lm b{font-size:13px}.b6{height:6px;background:var(--line-2);border-radius:3px;overflow:hidden;margin:5px 0 3px}.b6 i{display:block;height:100%;border-radius:3px}
.idx{width:16px;font-size:12px;color:var(--faint);padding-top:6px;text-align:center}
@media (max-width:1280px){.kpis{grid-template-columns:repeat(3,1fr)}.k{border-bottom:1px solid var(--line-2)}}
@media (max-width:1100px){.row2{grid-template-columns:1fr}}
@media (max-width:860px){.kpis{grid-template-columns:repeat(2,1fr)}}
</style>
