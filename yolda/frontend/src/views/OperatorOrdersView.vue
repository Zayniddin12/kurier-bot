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
  if (!typing && !e.ctrlKey && !e.metaKey && !e.altKey && /^[1-7]$/.test(e.key)) { chip.value = CHIPS[Number(e.key) - 1].k; return }
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
    <Teleport to="#hdr-slot">
      <div class="srch"><Icon name="search" :size="16" /><input ref="searchEl" v-model="q" class="inp" placeholder="Qidiruv: № / ism / telefon / restoran  ( / )" /></div>
    </Teleport>
    <div class="kpis" v-if="c">
      <div><b class="num">{{ c.active }}</b><span>Faol buyurtma</span></div>
      <div :class="{ warn: c.attention }"><b class="num">{{ c.attention }}</b><span>Diqqat</span></div>
      <div><b class="num">{{ c.nocourier }}</b><span>Kuryersiz</span></div>
      <div><b class="num">{{ c.onway }}</b><span>Yo'lda</span></div>
      <div class="ok"><b class="num">{{ c.idle_couriers }}</b><span>Bo'sh kuryer</span></div>
    </div>

    <div class="body" :class="{ detail: mobileDetail }">
      <!-- Chap: ro'yxat -->
      <section class="list">
        <div class="chips">
          <Chip v-for="x in CHIPS" :key="x.k" :on="chip === x.k" :class="{ warnchip: x.warn && c?.[x.n] }" :n="c?.[x.n] ?? 0" @click="chip = x.k">{{ x.l }}</Chip>
          <template v-if="chip === 'done'"><span class="brk" /><Chip v-for="x in SUBS" :key="x.k" class="subchip" :on="sub === x.k" :n="subN(x.k) ?? 0" @click="sub = x.k">{{ x.l }}</Chip></template>
          <span class="brk" />
          <select v-model="courierId" class="pillsel"><option value="">Kuryer bo'yicha</option><option v-for="k in couriers || []" :key="k.id" :value="k.id">{{ k.name }}</option></select>
          <select class="pillsel" :value="ui.restaurantId ?? ''" @change="ui.restaurantId = ($event.target as HTMLSelectElement).value ? Number(($event.target as HTMLSelectElement).value) : null">
            <option value="">Restoran bo'yicha</option><option v-for="r in rs.items" :key="r.id" :value="r.id">{{ r.name }}</option></select>
        </div>

        <div class="scroll">
          <ErrorBox v-if="error && !data" :message="error" @retry="reload()" />
          <div v-else-if="loading && !data" style="padding:12px"><Skeleton :h="64" :n="5" /></div>
          <template v-else>
            <button v-for="o in items" :key="o.id" class="card" :class="{ on: o.id === active, att: o.attention }" @click="open(o.id)">
              <div class="l1"><b class="num">#{{ o.id }}</b><span class="faint num">{{ hm(o.created_at) }}</span><span class="sp" /><Pill :tone="o.status_color">{{ o.pay_pending ? "To'lov kutilmoqda" : o.status_text }}</Pill></div>
              <div class="l2"><span class="nm">{{ o.customer_name || '—' }}</span><span v-if="isActive(o)" class="tm num" :class="{ red: isLate(o) }">{{ timer(o) }}</span><span v-else-if="o.delivery_minutes != null" class="tm num faint">{{ o.delivery_minutes }} daq</span></div>
              <div class="l3"><span class="sub">{{ o.restaurant.name }} · <Icon name="bike" :size="12" class="bk" /> <span :class="{ red: !o.courier }">{{ o.courier ? o.courier.name : 'kuryer yo\'q' }}</span></span><b class="num">{{ money(o.total) }} so'm</b></div>
              <div v-if="o.attention" class="l4 att"><Icon name="ban" :size="13" /> {{ o.attention }}</div>
              <div v-else-if="o.cancel_reason" class="l4 can"><Icon name="ban" :size="13" /> {{ o.cancel_reason }}</div>
            </button>
            <Empty v-if="!items.length" :title="dq ? 'Hech narsa topilmadi' : 'Buyurtma topilmadi'" :text="hasFilters ? 'Filtrlarni o\'zgartirib ko\'ring' : 'Yangi buyurtma kelganda shu yerda paydo bo\'ladi'" />
          </template>
        </div>

        <div v-if="totalPages > 1" class="pager"><button :disabled="page <= 1" @click="page--">‹ Oldingi</button><span class="num">{{ page }} / {{ totalPages }}</span><button :disabled="page >= totalPages" @click="page++">Keyingi ›</button></div>
        <div class="foot"><span>{{ data?.total ?? 0 }} ta buyurtma</span><span class="sp" /><span class="kb"><kbd>↑↓</kbd> tanlash</span><span class="kb"><kbd>/</kbd> qidiruv</span><span class="kb"><kbd>1-7</kbd> filtr</span></div>
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
.wrap{height:100%;display:flex;flex-direction:column;min-height:0;padding:14px 14px 13px;gap:15px}
.srch{position:relative;flex:0 1 446px;min-width:120px;margin-left:6px}.srch :deep(svg){position:absolute;left:11px;top:50%;transform:translateY(-50%);color:var(--faint)}
.srch .inp{width:100%;padding-left:34px;height:38px;border-radius:8px;font-size:14px}
.kpis{display:flex;align-self:flex-start;flex:none;background:var(--surface);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.kpis div{padding:8px 13px 7px;border-left:1px solid var(--line);display:flex;flex-direction:column;align-items:flex-start;gap:2px}.kpis div:first-child{border-left:0}
.kpis b{font-size:20px;line-height:1.2;font-weight:700}.kpis span{font-size:12.5px;color:var(--muted);white-space:nowrap;line-height:1.3}
.kpis .warn b{color:var(--red)}.kpis .ok b{color:var(--teal)}
.body{flex:1;min-height:0;display:grid;grid-template-columns:418px 1fr;gap:14px}
.list{background:var(--surface);border:1px solid var(--line);border-radius:10px;display:flex;flex-direction:column;min-height:0;overflow:hidden}
.chips{display:flex;flex-wrap:wrap;gap:6px;padding:10px 11px 9px;border-bottom:1px solid var(--line);flex:none}
.brk{flex-basis:100%;height:0}
.subchip{height:20px;font-size:12px;padding:0 8px}.subchip :deep(b){font-size:11px}
.warnchip :deep(b){color:var(--red)}
.pillsel{height:26px;border-radius:999px;border:1px solid var(--line);background:var(--surface) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='8' height='5' viewBox='0 0 8 5'%3E%3Cpath d='M0 0l4 5 4-5z' fill='%238A9AA0'/%3E%3C/svg%3E") no-repeat right 9px center;appearance:none;-webkit-appearance:none;padding:0 24px 0 10px;font-size:13px;font-weight:500;max-width:100%;color:var(--ink)}
.scroll{flex:1;overflow:auto;min-height:0}
.card{display:block;width:100%;text-align:left;border:0;border-bottom:1px solid var(--line-2);background:transparent;padding:11px 12px 11px 14px}
.card:hover{background:var(--surface-2)}.card.on{background:var(--brand-soft)}
.l1,.l2,.l3{display:flex;align-items:center;gap:8px}.l2{margin:4px 0 3px}.l3{justify-content:space-between;gap:10px;align-items:flex-end}
.l1 b{font-size:16px;font-weight:700}.l1 .faint{font-size:12.5px}
.nm{font-weight:500;font-size:14px;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tm{font-weight:600;font-size:13px;color:var(--amber)}.tm.red{color:var(--red)}.tm.faint{color:var(--faint);font-weight:500}
.l3 .sub{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0;flex:1 1 0;font-size:12.5px;color:var(--faint)}.l3 b{font-size:13px;font-weight:500;flex:0 1 auto;text-align:right;color:var(--ink)}
.bk{color:var(--red);vertical-align:-2px}
.l4{display:flex;align-items:center;gap:4px;font-size:12.5px;margin-top:4px;font-weight:500}.l4.att{color:var(--red)}.l4.can{color:var(--red)}
.pager{display:flex;justify-content:center;align-items:center;gap:8px;padding:8px;border-top:1px solid var(--line);font-size:12.5px;color:var(--muted);flex:none}
.pager button{height:24px;border:1px solid var(--line);background:var(--surface);border-radius:6px;padding:0 10px;font-size:12.5px;color:var(--ink)}.pager button:disabled{color:var(--faint);cursor:default}
.foot{display:flex;align-items:center;gap:12px;padding:0 12px;height:34px;border-top:1px solid var(--line);font-size:12px;color:var(--muted);flex:none}
.kb{display:inline-flex;align-items:center;gap:5px;white-space:nowrap}
kbd{font:inherit;font-size:11px;border:1px solid var(--line);border-radius:4px;padding:0 4px;background:var(--surface-2);line-height:16px}
.det{display:flex;flex-direction:column;min-height:0;min-width:0;background:var(--surface);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.otabs{display:flex;gap:2px;align-items:flex-end;overflow-x:auto;flex:none;border-bottom:1px solid var(--line);padding:0 12px;height:34px;background:var(--surface)}
.ot{display:inline-flex;align-items:center;gap:6px;height:33px;padding:0 6px 0 8px;border-bottom:2px solid transparent;font-size:13px;cursor:pointer;max-width:230px;color:var(--muted);white-space:nowrap}
.ot b{font-style:italic;font-weight:700;color:var(--ink)}
.ot.on{border-bottom-color:var(--brand)}.ot i{opacity:.7;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:110px}
.ot button{border:0;background:transparent;display:inline-flex;padding:2px;border-radius:5px;color:var(--faint)}.ot button:hover{background:var(--grey-soft)}
.back{display:none;border:0;background:transparent;font-weight:600;color:var(--link);align-items:center;padding:6px 8px}
.dscroll{flex:1;overflow:auto;min-height:0}
@media (max-width:1000px){
  .wrap{padding:10px 12px;gap:10px}
  .body{grid-template-columns:1fr}
  .body:not(.detail) .det{display:none}.body.detail .list{display:none}
  .back{display:inline-flex}.kpis{align-self:stretch;overflow:auto}
}
</style>
