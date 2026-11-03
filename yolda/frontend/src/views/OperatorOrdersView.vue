<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { get } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { useRestaurantsStore } from '@/stores/restaurants'
import { onLive } from '@/stores/live'
import { useLoad } from '@/utils/useLoad'
import { hm, money } from '@/utils/format'
import { SLA } from '@/constants/statuses'
import OrderPanel from '@/components/operator/OrderPanel.vue'

const ui = useUiStore(), rs = useRestaurantsStore(), route = useRoute(), router = useRouter()
const chip = ref('all'), sub = ref('all'), courierId = ref(''), q = ref(''), dq = ref(''), page = ref(1)
const now = ref(Date.now())
const searchEl = ref<HTMLInputElement>()
const opened = ref<{ id: number; label: string }[]>([])
const active = ref<number | null>(route.query.o ? Number(route.query.o) : null)
const mobileDetail = ref(!!active.value)
let t: any, tick: any, reloadT: any

watch(q, (v) => { clearTimeout(t); t = setTimeout(() => { dq.value = v; page.value = 1 }, 300) })
watch([chip, sub, courierId, () => ui.restaurantId], () => { page.value = 1 })
watch(chip, (c) => { if (c !== 'done') sub.value = 'all' })

const { data, loading, error, reload } = useLoad<any>(
  () => get('/operator/queue', { chip: chip.value, sub: sub.value, courier_id: courierId.value || undefined, restaurant_id: ui.restaurantId || undefined, q: dq.value || undefined, page: page.value, per_page: 20 }),
  [chip, sub, courierId, dq, page, () => ui.restaurantId])
const { data: couriers } = useLoad<any[]>(() => get('/operator/couriers-brief'))
const items = computed<any[]>(() => data.value?.items || [])
const c = computed(() => data.value?.counts)
const totalPages = computed(() => Math.max(1, Math.ceil((data.value?.total || 0) / 20)))

function softReload() { clearTimeout(reloadT); reloadT = setTimeout(() => reload(true), 600) }
onLive('order.created', softReload)
onLive('order.updated', softReload)
onLive('courier.updated', softReload)

function open(id: number, label?: string) {
  active.value = id; mobileDetail.value = true
  const it = items.value.find((x) => x.id === id)
  const text = label || it?.customer_name || ''
  if (!opened.value.some((x) => x.id === id)) opened.value.push({ id, label: text })
  router.replace({ query: { ...route.query, o: String(id) } })
}
function closeTab(id: number) {
  const i = opened.value.findIndex((x) => x.id === id)
  opened.value = opened.value.filter((x) => x.id !== id)
  if (active.value === id) {
    const nx = opened.value[Math.max(0, i - 1)]
    if (nx) open(nx.id)
    else { active.value = null; mobileDetail.value = false; const qq = { ...route.query }; delete qq.o; router.replace({ query: qq }) }
  }
}
function onLoaded(o: any) { const t = opened.value.find((x) => x.id === o.id); if (t) t.label = o.customer_name }
if (active.value) opened.value.push({ id: active.value, label: '' })

// birinchi yuklanishda ro'yxatdagi birinchi buyurtmani ochamiz
let first = true
watch(data, (d) => {
  if (first && d) { first = false; if (!active.value && d.items.length) open(d.items[0].id) }
})

function onKey(e: KeyboardEvent) {
  const el = e.target as HTMLElement
  const typing = el && ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName)
  if (e.key === '/' && !typing) { e.preventDefault(); searchEl.value?.focus(); return }
  if (typing || !items.value.length || !['ArrowDown', 'ArrowUp'].includes(e.key)) return
  e.preventDefault()
  const i = items.value.findIndex((x) => x.id === active.value)
  const n = items.value[Math.min(items.value.length - 1, Math.max(0, i + (e.key === 'ArrowDown' ? 1 : -1)))]
  if (n) open(n.id)
}
onMounted(() => { tick = setInterval(() => (now.value = Date.now()), 1000); window.addEventListener('keydown', onKey) })
onBeforeUnmount(() => { clearInterval(tick); clearTimeout(t); clearTimeout(reloadT); window.removeEventListener('keydown', onKey) })

const CHIPS = [
  { k: 'all', l: 'Hammasi', n: 'active' }, { k: 'attention', l: 'Diqqat', n: 'attention', warn: true }, { k: 'nocourier', l: 'Kuryersiz', n: 'nocourier' },
  { k: 'new', l: 'Yangi', n: 'new' }, { k: 'assigned', l: 'Biriktirilgan', n: 'assigned' }, { k: 'onway', l: "Yo'lda", n: 'onway' }, { k: 'done', l: 'Yakunlangan', n: 'done' },
]
const SUBS = [{ k: 'all', l: 'Hammasi' }, { k: 'delivered', l: 'Bajarilgan' }, { k: 'cancelled', l: 'Bekor qilingan' }]
const subN = (k: string) => k === 'all' ? c.value?.done : k === 'delivered' ? c.value?.done_delivered : c.value?.done_cancelled
const isActive = (o: any) => ['new', 'assigned', 'onway'].includes(o.status)
function timer(o: any) {
  const s = Math.max(0, Math.floor((now.value - new Date(o.created_at).getTime()) / 1000))
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}
const isLate = (o: any) => isActive(o) && (now.value - new Date(o.created_at).getTime()) / 60000 > SLA
const hasFilters = computed(() => !!(courierId.value || ui.restaurantId || dq.value))
</script>

<template>
  <div class="wrap">
    <div class="bar">
      <div class="srch"><Icon name="search" :size="16" /><input ref="searchEl" v-model="q" class="inp" placeholder="Qidiruv: № / ism / telefon / restoran  ( / )" /></div>
      <div class="kpis" v-if="c">
        <div><span>Faol buyurtma</span><b class="num">{{ c.active }}</b></div>
        <div :class="{ warn: c.attention }"><span>Diqqat</span><b class="num">{{ c.attention }}</b></div>
        <div><span>Kuryersiz</span><b class="num">{{ c.nocourier }}</b></div>
        <div><span>Yo'lda</span><b class="num">{{ c.onway }}</b></div>
        <div class="ok"><span>Bo'sh kuryer</span><b class="num">{{ c.idle_couriers }}</b></div>
      </div>
    </div>

    <div class="body" :class="{ detail: mobileDetail }">
      <!-- Chap: ro'yxat -->
      <section class="list">
        <div class="chips">
          <Chip v-for="x in CHIPS" :key="x.k" :on="chip === x.k" :class="{ warnchip: x.warn && c?.[x.n] }" :n="c?.[x.n] ?? 0" @click="chip = x.k">{{ x.l }}</Chip>
        </div>
        <div v-if="chip === 'done'" class="chips sm"><Chip v-for="x in SUBS" :key="x.k" :on="sub === x.k" :n="subN(x.k) ?? 0" @click="sub = x.k">{{ x.l }}</Chip></div>
        <div class="filters">
          <select v-model="courierId" class="inp"><option value="">Kuryer bo'yicha</option><option v-for="k in couriers || []" :key="k.id" :value="k.id">{{ k.name }}</option></select>
          <select class="inp" :value="ui.restaurantId ?? ''" @change="ui.restaurantId = ($event.target as HTMLSelectElement).value ? Number(($event.target as HTMLSelectElement).value) : null">
            <option value="">Restoran bo'yicha</option><option v-for="r in rs.items" :key="r.id" :value="r.id">{{ r.name }}</option></select>
        </div>

        <div class="scroll">
          <ErrorBox v-if="error && !data" :message="error" @retry="reload()" />
          <div v-else-if="loading && !data" style="padding:12px"><Skeleton :h="64" :n="5" /></div>
          <template v-else>
            <button v-for="o in items" :key="o.id" class="card" :class="{ on: o.id === active, att: o.attention }" @click="open(o.id)">
              <div class="l1"><b class="num">#{{ o.id }}</b><span class="faint num">{{ hm(o.created_at) }}</span><span class="sp" /><Pill :tone="o.status_color">{{ o.pay_pending ? "To'lov kutilmoqda" : o.status_text }}</Pill></div>
              <div class="l2"><span class="nm">{{ o.customer_name || '—' }}</span><span v-if="isActive(o)" class="tm num" :class="{ red: isLate(o) }">{{ timer(o) }}</span><span v-else-if="o.delivery_minutes != null" class="tm num faint">{{ o.delivery_minutes }} daq</span></div>
              <div class="l3"><span class="sub">{{ o.restaurant.name }} · <Icon name="bike" :size="12" /> {{ o.courier ? o.courier.name : 'kuryer yo\'q' }}</span><b class="num">{{ money(o.total) }} so'm</b></div>
              <div v-if="o.attention" class="l4 att">{{ o.attention }}</div>
              <div v-else-if="o.cancel_reason" class="l4 can">{{ o.cancel_reason }}</div>
            </button>
            <Empty v-if="!items.length" :title="dq ? 'Hech narsa topilmadi' : 'Buyurtma topilmadi'" :text="hasFilters ? 'Filtrlarni o\'zgartirib ko\'ring' : 'Yangi buyurtma kelganda shu yerda paydo bo\'ladi'" />
          </template>
        </div>

        <div class="pager"><Btn sm :disabled="page <= 1" @click="page--">‹ Oldingi</Btn><span class="num">{{ page }} / {{ totalPages }}</span><Btn sm :disabled="page >= totalPages" @click="page++">Keyingi ›</Btn></div>
        <div class="foot"><span>{{ data?.total ?? 0 }} ta buyurtma</span><span class="sp" /><span class="kb">↑↓ tanlash · / qidiruv</span></div>
      </section>

      <!-- O'ng: tafsilot -->
      <section class="det">
        <div v-if="opened.length" class="otabs">
          <button class="back" @click="mobileDetail = false"><Icon name="chevleft" :size="16" /> Ro'yxat</button>
          <span v-for="t in opened" :key="t.id" class="ot" :class="{ on: t.id === active }" @click="open(t.id, t.label)">
            <b class="num">#{{ t.id }}</b><i v-if="t.label">{{ t.label }}</i><button title="Yopish" @click.stop="closeTab(t.id)"><Icon name="x" :size="12" /></button>
          </span>
        </div>
        <div class="dscroll">
          <OrderPanel v-if="active" :id="active" :now="now" @changed="reload(true)" @open="(id) => open(id, '')" @loaded="onLoaded" />
          <Empty v-else title="Buyurtma tanlanmagan" text="Ro'yxatdan buyurtmani tanlang" />
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.wrap{height:100%;display:flex;flex-direction:column;min-height:0}
.bar{display:flex;gap:16px;align-items:center;padding:12px 20px;background:var(--surface);border-bottom:1px solid var(--line);flex-wrap:wrap}
.srch{position:relative;flex:1;min-width:240px;max-width:560px}.srch :deep(svg){position:absolute;left:10px;top:50%;transform:translateY(-50%);color:var(--faint)}
.srch .inp{width:100%;padding-left:32px;height:38px}
.kpis{display:flex;border:1px solid var(--line);border-radius:12px;overflow:hidden}
.kpis div{padding:6px 18px;border-left:1px solid var(--line-2);display:flex;flex-direction:column;align-items:flex-start;min-width:84px}.kpis div:first-child{border-left:0}
.kpis span{font-size:11.5px;color:var(--muted);white-space:nowrap}.kpis b{font-size:19px;line-height:1.2}
.kpis .warn b{color:var(--red)}.kpis .ok b{color:var(--teal)}
.body{flex:1;min-height:0;display:grid;grid-template-columns:350px 1fr;gap:14px;padding:14px 20px 16px}
.list{background:var(--surface);border:1px solid var(--line);border-radius:14px;display:flex;flex-direction:column;min-height:0;overflow:hidden}
.chips{display:flex;flex-wrap:wrap;gap:6px;padding:12px 12px 4px}.chips.sm{padding-top:2px}
.warnchip :deep(b){color:var(--red)}
.filters{display:grid;grid-template-columns:1fr 1fr;gap:6px;padding:6px 12px 10px;border-bottom:1px solid var(--line-2)}.filters .inp{width:100%;font-size:12.5px}
.scroll{flex:1;overflow:auto;min-height:0}
.card{display:block;width:100%;text-align:left;border:0;border-bottom:1px solid var(--line-2);background:transparent;padding:10px 14px;border-left:3px solid transparent}
.card:hover{background:var(--surface-2)}.card.on{background:var(--brand-soft);border-left-color:var(--brand)}.card.att{border-left-color:var(--red)}
.l1,.l2,.l3{display:flex;align-items:center;gap:8px}.l2{margin:3px 0 2px}.l3{justify-content:space-between;gap:10px}
.nm{font-weight:600;font-size:13.5px;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tm{font-weight:700;font-size:13px;color:var(--amber)}.tm.red{color:var(--red)}.tm.faint{color:var(--faint)}
.l3 .sub{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}.l3 b{font-size:12.5px;white-space:nowrap}
.l4{font-size:12px;margin-top:3px;font-weight:600}.l4.att{color:var(--red)}.l4.can{color:var(--red);opacity:.85}
.pager{display:flex;justify-content:center;align-items:center;gap:10px;padding:8px;border-top:1px solid var(--line-2);font-size:12.5px}
.foot{display:flex;padding:7px 14px;border-top:1px solid var(--line-2);font-size:11.5px;color:var(--muted)}
.det{display:flex;flex-direction:column;min-height:0;min-width:0}
.otabs{display:flex;gap:4px;align-items:flex-end;margin-bottom:-1px;overflow-x:auto;flex:none}
.ot{display:inline-flex;align-items:center;gap:6px;padding:6px 8px 6px 12px;border:1px solid var(--line);border-bottom:0;border-radius:10px 10px 0 0;background:var(--surface-2);font-size:12.5px;cursor:pointer;max-width:200px;color:var(--muted)}
.ot.on{background:var(--surface);color:var(--ink)}.ot i{font-style:normal;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100px}
.ot button{border:0;background:transparent;display:inline-flex;padding:2px;border-radius:5px;color:var(--faint)}.ot button:hover{background:var(--grey-soft)}
.back{display:none;border:0;background:transparent;font-weight:600;color:var(--blue);align-items:center;padding:6px 8px}
.dscroll{flex:1;overflow:auto;min-height:0}
@media (max-width:1000px){
  .body{grid-template-columns:1fr;padding:10px 12px}
  .body:not(.detail) .det{display:none}.body.detail .list{display:none}
  .back{display:inline-flex}.bar{padding:10px 12px}.kpis{width:100%;overflow:auto}
}
</style>
