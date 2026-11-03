<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { get, post, patch, errMsg } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { useDrawer } from '@/utils/drawer'
import { useLoad } from '@/utils/useLoad'
import { money, moneyS, hm, dmyhm, phoneFmt } from '@/utils/format'
import { SLA } from '@/constants/statuses'
import CancelModal from '../modals/CancelModal.vue'
import OrderLocationModal from '../modals/OrderLocationModal.vue'
import CourierPickModal from './CourierPickModal.vue'
import NoteModal from './NoteModal.vue'
import OrderMap from './OrderMap.vue'

const p = defineProps<{ id: number; now: number }>()
const emit = defineEmits<{ changed: []; open: [number]; loaded: [any] }>()
const ui = useUiStore(), router = useRouter(), drawer = useDrawer()
const { data: o, loading, error, reload } = useLoad<any>(() => get(`/operator/orders/${p.id}`), [() => p.id],
  ['order.updated', 'issue.opened', 'issue.closed', 'courier.updated'])
watch(o, (v) => { if (v) emit('loaded', v) })

const tab = ref<'main' | 'items' | 'pay' | 'fiscal' | 'logs'>('main')
watch(() => p.id, () => { tab.value = 'main' })
const modal = ref<'' | 'cancel' | 'loc' | 'courier' | 'swap' | 'rnote' | 'cnote' | 'custnote' | 'block' | 'unassign'>('')
const busy = ref(false)

function apply(d: any) { o.value = d; emit('changed'); modal.value = '' }
async function run(fn: () => Promise<any>, okMsg?: string) {
  if (busy.value) return
  busy.value = true
  try { const d = await fn(); apply(d); if (okMsg) ui.toast(okMsg) }
  catch (e) { ui.toast(errMsg(e), 'var(--red)') } finally { busy.value = false }
}
const advance = () => run(() => post(`/operator/orders/${p.id}/advance`), 'Buyurtma keyingi bosqichga o\'tkazildi')
const unassign = () => run(() => post(`/operator/orders/${p.id}/unassign`), 'Kuryer olib tashlandi — buyurtma qayta qidiruvda')
const saveNote = (field: 'restaurant_note' | 'courier_note', v: string) => run(() => patch(`/operator/orders/${p.id}/notes`, { [field]: v }), 'Izoh saqlandi')
const addCustNote = (v: string) => run(() => post(`/operator/orders/${p.id}/customer-notes`, { text: v }), 'Eslatma qo\'shildi')
const block = (v: string) => run(() => post(`/operator/orders/${p.id}/block-customer`, { reason: v }), 'Mijoz bloklandi')
const unblock = () => run(() => post(`/operator/orders/${p.id}/unblock-customer`), 'Mijoz blokdan chiqarildi')
async function notify() { try { await post(`/orders/${p.id}/notify-customer`); ui.toast('Mijozga xabar yuborildi') } catch (e) { ui.toast(errMsg(e), 'var(--red)') } }
async function copy(t: string) { try { await navigator.clipboard.writeText(t); ui.toast('Nusxalandi') } catch { /* ignore */ } }
function onMap() { ui.mapFocus = { courierId: o.value?.courier?.id }; router.push('/map') }
function onNext() { o.value.next_action.kind === 'assign' ? (modal.value = 'courier') : advance() }

const active = computed(() => !!o.value?.can_edit)
const elapsed = computed(() => {
  if (!o.value) return ''
  const s = active.value ? Math.max(0, Math.floor((p.now - new Date(o.value.created_at).getTime()) / 1000)) : o.value.total_seconds
  const m = Math.floor(s / 60)
  return `${String(m).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
})
const late = computed(() => active.value && o.value && (p.now - new Date(o.value.created_at).getTime()) / 60000 > SLA)
const totalFmt = computed(() => { const s = o.value?.total_seconds || 0; const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60); return h ? `${h}:${String(m).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}` : `${String(m).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}` })
const tabs = computed(() => o.value ? [
  { k: 'main', l: 'Asosiy' }, { k: 'items', l: 'Mahsulotlar', n: o.value.items.length }, { k: 'pay', l: "To'lovlar", n: o.value.payments.length },
  { k: 'fiscal', l: 'Fiskal cheklar' }, { k: 'logs', l: 'Loglar', n: o.value.logs.length },
] : [])
</script>

<template>
  <div class="panel">
    <ErrorBox v-if="error && !o" :message="error" @retry="reload()" />
    <div v-else-if="loading && !o" style="padding:20px"><Skeleton :h="44" :n="6" /></div>
    <template v-else-if="o">
      <div class="top">
        <div class="t1">
          <b class="num">#{{ o.id }}</b><span class="faint num">{{ hm(o.created_at) }}</span>
          <span v-if="o.external_id" class="faint ext" :title="'Restoran buyurtma raqami'">{{ o.external_id }}</span>
          <span class="sp" />
          <span class="timer num" :class="{ red: late }"><Icon name="clock" :size="14" /> {{ elapsed }}</span>
          <Btn v-if="active" sm variant="danger" @click="modal = 'cancel'">Bekor qilish</Btn>
        </div>
        <div class="t2">
          <Pill :tone="o.status_color">{{ o.status_text }}</Pill>
          <Tag>{{ o.pay_method }} · {{ moneyS(o.total) }}</Tag><Pill :tone="o.pay_status_color">{{ o.pay_status_text }}</Pill>
          <Tag v-if="o.distance_km != null">{{ o.distance_km.toFixed(1) }} km</Tag>
          <Tag v-if="o.queued">kuryer navbatida</Tag>
          <Pill v-if="o.customer.blocked" tone="red">Mijoz bloklangan</Pill>
        </div>
        <div class="steps">
          <span v-for="s in o.steps" :key="s.key" class="st" :class="s.state"><i />{{ s.label }}</span>
          <span v-if="o.status === 'cancelled'" class="st cancelled"><i />Bekor qilindi</span>
        </div>
      </div>

      <div v-if="o.issue" class="warn red">
        <b>{{ o.issue.text }}</b><span class="sub"> · kechikish +{{ o.issue.delay_min }} daq</span>
      </div>
      <div v-if="o.next_action && active" class="next">
        <div class="nt"><b>{{ o.next_action.title }}</b><p>{{ o.next_action.text }}</p></div>
        <Btn variant="primary" :disabled="busy" @click="onNext">{{ o.next_action.button }}</Btn>
      </div>
      <div v-else-if="o.status === 'cancelled'" class="warn red"><b>Bekor qilindi</b><span> · {{ o.cancel_reason || '—' }}</span></div>

      <div class="tabs"><button v-for="t in tabs" :key="t.k" :class="{ on: tab === t.k }" @click="tab = t.k as any">{{ t.l }}<small v-if="t.n != null">{{ t.n }}</small></button></div>

      <!-- Asosiy -->
      <div v-if="tab === 'main'" class="main">
        <div class="cols">
          <div class="note"><div class="nh">Mijoz izohi — restoranga<IconBtn v-if="active" icon="edit" title="Tahrirlash" @click="modal = 'rnote'" /></div><p :class="{ faint: !o.restaurant_note }">{{ o.restaurant_note || 'Izoh yo\'q' }}</p></div>
          <div class="note"><div class="nh">Mijoz izohi — kuryerga<IconBtn v-if="active" icon="edit" title="Tahrirlash" @click="modal = 'cnote'" /></div><p :class="{ faint: !o.courier_note }">{{ o.courier_note || 'Izoh yo\'q' }}</p></div>

          <div class="card">
            <div class="ch">Mijoz<span class="sp" /><span class="stat teal" title="Yetkazilgan buyurtmalar">✓ {{ o.customer.delivered }}</span><span class="stat red" title="Bekor qilingan buyurtmalar">✗ {{ o.customer.cancelled }}</span></div>
            <div class="r1"><b>{{ o.customer_name }}</b><a :href="`tel:${o.customer_phone}`" class="num">{{ o.customer_phone }}</a><IconBtn icon="copy" title="Nusxalash" @click="copy(o.customer_phone)" /></div>
            <div v-if="o.customer.last_delivered_id" class="sub">Oxirgi yakunlangan: <a href="#" @click.prevent="emit('open', o.customer.last_delivered_id)">#{{ o.customer.last_delivered_id }}</a></div>
            <div v-if="o.customer.last_cancelled_id" class="sub">Oxirgi bekor: <a href="#" @click.prevent="emit('open', o.customer.last_cancelled_id)">#{{ o.customer.last_cancelled_id }}</a></div>
            <div v-if="o.customer.blocked" class="sub red">Bloklangan{{ o.customer.block_reason ? ': ' + o.customer.block_reason : '' }}</div>
            <ul v-if="o.customer.notes.length" class="cn"><li v-for="n in o.customer.notes.slice(0, 3)" :key="n.id"><b>{{ n.text }}</b><small>{{ n.author }} · {{ dmyhm(n.created_at) }}</small></li></ul>
            <div class="acts">
              <Btn sm icon="mail" @click="notify">Xabar yuborish</Btn><Btn sm icon="note" @click="modal = 'custnote'">Eslatma qo'shish</Btn>
              <Btn v-if="!o.customer.blocked" sm variant="danger" icon="ban" @click="modal = 'block'">Mijozni bloklash</Btn>
              <Btn v-else sm :disabled="busy" @click="unblock">Blokdan chiqarish</Btn>
            </div>
          </div>

          <div class="card">
            <div class="ch">Yetkazish manzili<span class="sp" /><a v-if="active" href="#" @click.prevent="modal = 'loc'">tahrirlash</a></div>
            <div class="r1"><b>{{ o.address }}</b></div>
            <div class="sub">{{ o.district }}</div>
            <div v-if="o.handoff" class="sub">Buyurtma bergan joy: {{ o.handoff.name }}</div>
          </div>

          <div class="card">
            <div class="ch">Restoran</div>
            <div class="row" style="gap:8px"><RestLogo :name="o.restaurant.name" :color="o.restaurant.color" /><div><b>{{ o.restaurant.name }}</b><div class="sub">{{ o.restaurant.address }}</div></div></div>
            <div class="r1"><a :href="`tel:${o.restaurant.phone}`" class="num">{{ o.restaurant.phone || '—' }}</a></div>
          </div>

          <div class="card">
            <div class="ch">Kuryer</div>
            <template v-if="o.courier">
              <div class="row" style="gap:10px"><Avatar :seed="o.courier.avatar_seed" :female="o.courier.is_female" :size="34" />
                <div style="flex:1;min-width:0"><a href="#" class="cb" @click.prevent="drawer.open('courier', o.courier.id)">{{ o.courier.name }}</a>
                  <div class="sub"><a :href="`tel:${o.courier.phone}`" class="num">{{ o.courier.phone }}</a> · {{ o.courier.vehicle }} {{ o.courier.plate && o.courier.plate !== '—' ? o.courier.plate : '' }}</div></div></div>
              <div v-if="o.eta" class="sub" style="margin-top:6px">Taxminan <b>{{ o.eta.eta_min }} daq</b> · {{ o.eta.remaining_km }} km qoldi</div>
              <div class="acts"><Btn sm icon="pin" @click="onMap">Xaritada</Btn>
                <template v-if="active"><Btn sm @click="modal = 'swap'">Almashtirish</Btn><Btn sm variant="danger" @click="modal = 'unassign'">Olib tashlash</Btn></template></div>
            </template>
            <template v-else>
              <div class="muted">Kuryer biriktirilmagan</div>
              <div v-if="o.search" class="sub">{{ o.search.pending_payment ? 'To\'lov kutilmoqda' : o.search.offer_courier ? `Taklif: ${o.search.offer_courier.name}` : 'Tizim qidirmoqda' }} · {{ o.search.declined_count }} ta rad etdi</div>
              <button v-if="active" class="pickbtn" @click="modal = 'courier'">+ Kuryer tanlash</button>
            </template>
          </div>

          <div class="card wide"><div class="ch">Yetkazib berish xaritasi</div><OrderMap :order="o" /></div>
        </div>

        <aside class="tl">
          <div class="ch">Buyurtma bosqichlari</div>
          <div v-for="(s, i) in o.op_timeline" :key="s.key" class="ti" :class="s.state">
            <div class="dot"><Icon :name="s.state === 'done' ? 'check' : s.state === 'cancelled' ? 'x' : 'clock'" :size="12" /></div>
            <div class="tb"><small v-if="s.delta" class="d num">+{{ s.delta }}</small><b>{{ s.label }}</b><div v-if="s.at" class="sub num">{{ dmyhm(s.at) }}</div></div>
            <span v-if="i < o.op_timeline.length - 1" class="ln" />
          </div>
          <div class="tot">Jami vaqt<b class="num">{{ totalFmt }}</b></div>
        </aside>
      </div>

      <!-- Mahsulotlar -->
      <div v-else-if="tab === 'items'" class="pane">
        <table class="tbl"><tbody>
          <tr v-for="(it, i) in o.items" :key="i"><td><b>{{ it.name }}</b> <span class="muted">× {{ it.qty }}</span><div class="sub num">{{ money(it.price) }} so'm × {{ it.qty }}</div></td><td class="r num">{{ money(it.qty * it.price) }} so'm</td></tr>
        </tbody></table>
        <p class="sub" style="margin-top:8px">{{ active ? 'Buyurtma tarkibini restoran tizimi yuboradi — bu yerda tahrirlab bo\'lmaydi.' : 'Buyurtma yakunlangan.' }}</p>
        <dl class="sum"><dt>Mahsulotlar</dt><dd class="num">{{ money(o.subtotal) }} so'm</dd><dt>Yetkazib berish</dt><dd class="num">{{ money(o.delivery_fee) }} so'm</dd><dt class="tt">Jami</dt><dd class="num tt">{{ money(o.total) }} so'm</dd></dl>
      </div>

      <!-- To'lovlar -->
      <div v-else-if="tab === 'pay'" class="pane">
        <table class="tbl"><tbody>
          <tr v-for="(x, i) in o.payments" :key="i"><td><b>{{ x.label }}</b><div class="sub">{{ x.note || '' }}</div></td><td class="num sub">{{ dmyhm(x.at) }}</td><td class="r num" :class="{ red: x.amount < 0 }">{{ money(x.amount) }} so'm</td></tr>
        </tbody></table>
        <dl class="sum"><dt>Kuryer haqi</dt><dd class="num">{{ moneyS(o.payment.courier_fee) }}</dd><dt>Platforma komissiyasi</dt><dd class="num">{{ moneyS(o.payment.commission) }}</dd>
          <template v-if="o.payment.courier_collects"><dt>Kuryer mijozdan oladi</dt><dd class="num">{{ moneyS(o.total) }}</dd><dt>Kompaniyaga topshiradi</dt><dd class="num">{{ moneyS(o.payment.company_due) }}</dd></template></dl>
      </div>

      <!-- Fiskal -->
      <div v-else-if="tab === 'fiscal'" class="pane"><Empty title="Fiskal cheklar yo'q" text="Fiskalizatsiya tizimi hali ulanmagan — cheklar shu yerda ko'rinadi." /></div>

      <!-- Loglar -->
      <div v-else class="pane">
        <div v-for="(l, i) in o.logs" :key="i" class="lg"><span class="num faint">{{ dmyhm(l.at) }}</span><span>{{ l.text }}</span><Tag>{{ l.actor }}</Tag></div>
      </div>

      <CancelModal v-if="modal === 'cancel'" :order-id="o.id" @close="modal = ''" @done="reload(true); emit('changed')" />
      <OrderLocationModal v-if="modal === 'loc'" :order="o" @close="modal = ''" @done="reload(true); emit('changed')" />
      <CourierPickModal v-if="modal === 'courier' || modal === 'swap'" :order-id="o.id" :replacing="modal === 'swap'" @close="modal = ''" @done="apply" />
      <NoteModal v-if="modal === 'rnote'" title="Mijoz izohi — restoranga" :sub="`Buyurtma #${o.id}`" label="Izoh" ok="Saqlash" :initial="o.restaurant_note || ''" @close="modal = ''" @submit="(v) => saveNote('restaurant_note', v)" />
      <NoteModal v-if="modal === 'cnote'" title="Mijoz izohi — kuryerga" :sub="`Buyurtma #${o.id}`" label="Izoh" ok="Saqlash" :initial="o.courier_note || ''" @close="modal = ''" @submit="(v) => saveNote('courier_note', v)" />
      <NoteModal v-if="modal === 'custnote'" title="Mijoz haqida eslatma" :sub="`${o.customer_name} · ${phoneFmt(o.customer_phone)}`" label="Eslatma (barcha operatorlarga ko'rinadi)" ok="Qo'shish" required @close="modal = ''" @submit="addCustNote" />
      <NoteModal v-if="modal === 'block'" title="Mijozni bloklash" :sub="`${o.customer_name} · ${o.customer_phone}`" label="Sabab" ok="Bloklash" danger @close="modal = ''" @submit="block" />
      <Modal v-if="modal === 'unassign'" title="Kuryerni olib tashlash" sub="Buyurtma qayta kuryer qidiruviga qo'yiladi" @close="modal = ''">
        <p>{{ o.courier?.name }} buyurtma #{{ o.id }} dan olib tashlansinmi?</p>
        <template #footer><Btn @click="modal = ''">Yo'q</Btn><Btn variant="dark" :disabled="busy" @click="unassign">Olib tashlash</Btn></template>
      </Modal>
    </template>
  </div>
</template>

<style scoped>
.panel{background:var(--surface);border:1px solid var(--line);border-radius:14px;min-width:0;overflow:hidden}
.top{padding:14px 18px 10px;display:flex;flex-direction:column;gap:9px}
.t1{display:flex;align-items:center;gap:10px}.t1 b{font-size:20px}.ext{font-size:12px}
.timer{display:inline-flex;align-items:center;gap:5px;font-weight:700;font-size:15px;color:var(--amber)}.timer.red{color:var(--red)}
.t2{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.steps{display:flex;gap:4px;flex-wrap:wrap;margin-top:4px}
.st{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border-radius:8px;font-size:12.5px;font-weight:600;border:1px solid var(--line-2);color:var(--faint);background:var(--surface-2)}
.st i{width:7px;height:7px;border-radius:50%;background:currentColor}
.st.done{color:var(--teal);background:var(--teal-soft);border-color:transparent}.st.current{color:var(--amber);background:var(--amber-soft);border-color:var(--amber)}
.st.cancelled{color:var(--red);background:var(--red-soft);border-color:transparent}.st.off{opacity:.45}
.warn{margin:0 18px 10px;padding:10px 12px;border-radius:10px;font-size:13px}.warn.red{background:var(--red-soft);color:var(--red)}
.next{margin:0 18px 12px;padding:12px 14px;border-radius:12px;background:var(--amber-soft);border:1px solid var(--amber);display:flex;gap:14px;align-items:center}
.nt{flex:1;font-size:13px}.nt p{margin-top:2px;color:var(--ink);opacity:.8}
.tabs{display:flex;gap:2px;border-bottom:1px solid var(--line);padding:0 12px;overflow:auto}
.tabs button{border:0;background:transparent;padding:11px 12px;font-weight:600;color:var(--muted);border-bottom:2px solid transparent;display:inline-flex;gap:6px;align-items:center;white-space:nowrap}
.tabs button.on{color:var(--ink);border-bottom-color:var(--brand)}.tabs small{background:var(--grey-soft);border-radius:999px;padding:0 7px;font-size:11px;color:var(--muted)}
.main{display:grid;grid-template-columns:1fr 260px;gap:16px;padding:16px 18px}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:12px;align-content:start;min-width:0}
.card,.note{border:1px solid var(--line);border-radius:12px;padding:12px 14px;display:flex;flex-direction:column;gap:6px;min-width:0}
.card.wide{grid-column:1/-1}
.ch,.nh{font-size:11.5px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;display:flex;align-items:center;gap:8px}
.nh{justify-content:space-between}.note p{font-size:13px;margin:0}
.stat{font-weight:700;font-size:12px;text-transform:none;letter-spacing:0}
.r1{display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:13.5px}
.cb{font-weight:700;color:var(--ink)}.cb:hover{color:var(--blue)}
.cn{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:4px;font-size:12.5px}.cn li{background:var(--amber-soft);border-radius:8px;padding:5px 8px}.cn small{display:block;color:var(--muted);font-size:11px}
.acts{display:flex;gap:6px;flex-wrap:wrap;margin-top:4px}
.pickbtn{margin-top:4px;border:1.5px dashed var(--line);background:transparent;border-radius:10px;padding:10px;font-weight:600;color:var(--blue)}.pickbtn:hover{background:var(--surface-2)}
.tl{border:1px solid var(--line);border-radius:12px;padding:12px 14px;align-self:start}
.ti{position:relative;display:flex;gap:10px;padding-bottom:16px}
.dot{width:24px;height:24px;border-radius:50%;border:2px solid var(--line);display:flex;align-items:center;justify-content:center;flex:none;background:var(--surface);color:var(--faint);z-index:1}
.ti.done .dot{border-color:var(--teal);color:var(--teal)}.ti.current .dot{border-color:var(--amber);color:var(--amber)}.ti.cancelled .dot{border-color:var(--red);color:var(--red)}
.ti .ln{position:absolute;left:11px;top:24px;bottom:0;border-left:2px solid var(--line)}
.ti.todo b{color:var(--faint)}.tb b{font-size:13px;display:block}.d{font-size:11px;color:var(--teal);font-weight:700}
.tot{display:flex;justify-content:space-between;border-top:1px solid var(--line);padding-top:10px;font-size:13px}
.pane{padding:14px 18px 20px}
.tbl{width:100%;border-collapse:collapse;font-size:13.5px}.tbl td{padding:10px 0;border-bottom:1px solid var(--line-2);vertical-align:top}.tbl .r{text-align:right;white-space:nowrap}
.sum{display:grid;grid-template-columns:1fr auto;gap:6px 20px;margin:14px 0 0;font-size:13.5px}.sum dd{margin:0;text-align:right}.sum dt{color:var(--muted)}.sum .tt{font-weight:800;color:var(--ink);font-size:15px;border-top:1px solid var(--line);padding-top:8px}
.lg{display:flex;gap:12px;padding:8px 0;border-bottom:1px solid var(--line-2);font-size:13px;align-items:baseline}.lg .num{white-space:nowrap;font-size:12px}.lg span:nth-child(2){flex:1}
@media (max-width:1180px){.main{grid-template-columns:1fr}.tl{order:-1}}
@media (max-width:640px){.cols{grid-template-columns:1fr}.next{flex-direction:column;align-items:stretch}}
</style>
