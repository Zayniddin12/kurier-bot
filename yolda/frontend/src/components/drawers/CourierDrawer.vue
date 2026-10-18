<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { get, post, errMsg } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import { useDrawer } from '@/utils/drawer'
import { useLoad } from '@/utils/useLoad'
import { money, moneyS, dmy, hm, ago } from '@/utils/format'
import { LEDGER, VEHICLES, workLine, WORK_STATUS, CASH_LIMIT } from '@/constants/statuses'
import IssueBox from '../IssueBox.vue'
import EtaBox from '../EtaBox.vue'
import Steps from '../Steps.vue'
import TopupModal from '../modals/TopupModal.vue'
const p = defineProps<{ id: number }>()
defineEmits<{ close: [] }>()
const ui = useUiStore(), router = useRouter(), drawer = useDrawer(), auth = useAuthStore()
const { data: d, loading, error, reload } = useLoad<any>(() => get(`/couriers/${p.id}`), [() => p.id], ['courier.updated', 'order.updated', 'issue.opened', 'issue.closed'])
const topup = ref(false)
const c = computed(() => d.value?.courier)
const o = computed(() => d.value?.order)
const line = computed(() => (c.value ? workLine(c.value.work_status, c.value.account_status === 'blocked') : null))
const idleMin = computed(() => (c.value?.idle_since ? Math.max(0, Math.floor((Date.now() - new Date(c.value.idle_since).getTime()) / 60000)) : 0))
const shiftTxt = computed(() => { const m = d.value?.today.shift_minutes; return m == null ? '—' : `${Math.floor(m / 60)}:${String(m % 60).padStart(2, '0')}` })
async function block() {
  try {
    if (c.value.account_status === 'blocked') { await post(`/couriers/${p.id}/unblock`); ui.toast(`${c.value.full_name} blokdan chiqarildi`) }
    else { if (!confirm(`${c.value.full_name} ni bloklaysizmi?`)) return; await post(`/couriers/${p.id}/block`); ui.toast(`${c.value.full_name} bloklandi`, 'var(--red)') }
    reload(true)
  } catch (e) { ui.toast(errMsg(e), 'var(--red)') }
}
async function unlink() {
  if (!confirm('Telegram bog\'lanishi uziladi: kuryer botda qayta ro\'yxatdan o\'tishi kerak. Davom etasizmi?')) return
  try { await post(`/couriers/${p.id}/unlink-telegram`); ui.toast('Telegram uzildi'); reload(true) } catch (e) { ui.toast(errMsg(e), 'var(--red)') }
}
function onMap() { ui.mapFocus = { courierId: p.id }; router.push('/map') }
const stateBox = computed(() => {
  if (!c.value) return ''
  if (c.value.account_status === 'blocked') return 'Bloklangan'
  if (c.value.work_status === 'break') return 'Tanaffusda'
  if (c.value.work_status === 'offline') return 'Smenada emas'
  return `Bo'sh · ${idleMin.value} daq`
})
</script>

<template>
  <Drawer title="Kuryer" @close="$emit('close')">
    <ErrorBox v-if="error && !d" :message="error" @retry="reload()" />
    <Skeleton v-else-if="loading && !d" :h="40" :n="6" />
    <template v-else-if="d">
      <div class="row" style="gap:14px;align-items:flex-start">
        <Avatar :seed="c.avatar_seed" :female="c.is_female" :size="68" />
        <div><b style="font-size:19px">{{ c.full_name }}</b>
          <div class="sub">#{{ c.number }} · {{ c.vehicle_name || c.vehicle }}<template v-if="c.plate && c.plate !== '—'"> · {{ c.plate }}</template></div>
          <div class="row" style="gap:6px;margin-top:6px;flex-wrap:wrap">
            <Pill :tone="line!.tone">{{ line!.label }}</Pill>
            <Pill v-if="line!.label === 'Liniyada'" :tone="WORK_STATUS[c.work_status].tone">{{ WORK_STATUS[c.work_status].label }}</Pill>
            <Tag>★ {{ c.rating }}</Tag></div></div>
      </div>

      <template v-if="o">
        <IssueBox v-if="d.issue" :issue="d.issue" style="display:block;margin-top:14px" @done="reload(true)" />
        <div v-if="d.eta" style="margin-top:14px"><EtaBox :eta="d.eta" /></div>
        <div class="sec-title">Yo'nalish · #{{ o.id }}</div>
        <div class="route">
          <div class="pt"><i class="sq" /><div><b>{{ o.restaurant.name }}</b><div class="sub">{{ o.restaurant.address }}</div></div></div>
          <div class="pt"><i class="ci" /><div><b>{{ o.customer_name }} · <a :href="`tel:${o.customer_phone}`">{{ o.customer_phone }}</a></b><div class="sub">{{ o.district }}, {{ o.address }}</div></div></div>
        </div>
        <div class="sec-title">To'lov</div>
        <dl class="kv">
          <dt>To'lov usuli</dt><dd>{{ o.payment.method }}</dd><dt>Holati</dt><dd><Pill :tone="o.payment.status_color">{{ o.payment.status_text }}</Pill></dd>
          <template v-if="o.payment.method === 'Naqd'"><dt>Kuryer mijozdan oladi</dt><dd class="num">{{ moneyS(o.payment.courier_collects) }}</dd><dt>Kompaniyaga topshiradi</dt><dd class="num">{{ moneyS(o.payment.company_due) }}</dd></template>
          <template v-else><dt>Mijozdan yechildi</dt><dd class="num">{{ moneyS(o.total) }}</dd></template>
          <dt>Kuryer haqi</dt><dd class="num">{{ moneyS(o.payment.courier_fee) }}</dd><dt>Platforma komissiyasi</dt><dd class="num">{{ moneyS(o.payment.commission) }}</dd>
        </dl>
        <div class="sec-title">Nima olib ketmoqda</div>
        <table class="items"><tbody>
          <tr v-for="(it, i) in o.items" :key="i"><td>{{ it.qty }} × {{ it.name }}</td><td class="num r">{{ money(it.qty * it.price) }}</td></tr>
          <tr><td class="muted">Yetkazish</td><td class="num r">{{ money(o.delivery_fee) }}</td></tr>
          <tr class="tot"><td>Jami · {{ o.pay_method }}</td><td class="num r">{{ moneyS(o.total) }}</td></tr>
        </tbody></table>
        <div class="sec-title">Buyurtma bosqichlari</div>
        <Steps :steps="o.timeline" />
        <a class="lnk" @click="drawer.open('order', o.id)">Buyurtmani ochish →</a>
      </template>
      <div v-else class="box" style="margin-top:14px">
        <b>{{ stateBox }}</b>
        <div class="sub" v-if="d.offer">Tizim #{{ d.offer.order_id }} buyurtmani taklif qildi, javob kutilmoqda</div>
        <div class="sub" v-else-if="c.work_status === 'idle' && c.account_status === 'active'">Tizim keyingi mos buyurtmani avtomatik beradi</div>
      </div>

      <template v-if="d.queue?.length">
        <div class="sec-title">Navbatdagi buyurtmalar</div>
        <div v-for="q in d.queue" :key="q.id" class="qrow" @click="drawer.open('order', q.id)"><b>#{{ q.id }}</b> {{ q.restaurant.name }} → {{ q.district }}</div>
      </template>

      <div class="sec-title">Balans</div>
      <div class="row" style="align-items:flex-start">
        <div><small class="muted">{{ c.balance < 0 ? 'Kuryer kompaniyaga qarzdor' : 'Kompaniya kuryerga qarzdor' }}</small>
          <div class="num" :class="{ red: c.balance < 0 }" style="font-size:24px;font-weight:800">{{ moneyS(c.balance) }}</div></div>
        <span class="sp" /><Btn v-if="!auth.isStaff" variant="primary" @click="topup = true">To'ldirish</Btn>
      </div>
      <div v-if="c.balance < -(d.limit || CASH_LIMIT)" class="box red" style="margin-top:8px">Naqd limitidan oshgan ({{ moneyS(d.limit || CASH_LIMIT) }}) — tizim naqd buyurtma bermaydi</div>
      <div class="mini-cards" style="margin-top:10px">
        <div class="mini"><b class="num">{{ money(d.today.earned) }}</b><span>Bugun ishladi</span></div>
        <div class="mini"><b class="num">{{ money(d.today.cash) }}</b><span>Naqd oldi</span></div>
        <div class="mini"><b class="num">{{ d.today.delivered }}</b><span>Yetkazdi</span></div>
      </div>
      <div class="led">
        <div v-for="l in d.ledger" :key="l.id" class="lr">
          <i :style="{ background: LEDGER[l.type]?.color }" />
          <div class="lt"><b>{{ LEDGER[l.type]?.label }}<template v-if="l.order_id"> #{{ l.order_id }}</template></b><small>{{ l.note }}</small></div>
          <div class="rt"><b class="num" :class="{ red: l.amount < 0 }">{{ l.amount > 0 ? '+' : '' }}{{ money(l.amount) }}</b><small>{{ hm(l.created_at) }}</small></div>
        </div>
      </div>

      <div class="sec-title">Bugungi natija</div>
      <dl class="kv"><dt>Yetkazdi</dt><dd class="num">{{ d.today.delivered }}</dd><dt>Km yurdi</dt><dd class="num">{{ d.today.km }}</dd><dt>Smenada</dt><dd class="num">{{ shiftTxt }}</dd></dl>
      <div class="sec-title">Ma'lumot</div>
      <dl class="kv">
        <dt>Telefon</dt><dd>+998 {{ c.phone }}</dd><dt>JShShIR</dt><dd class="num">{{ c.pinfl }}</dd><dt>Smena</dt><dd>{{ c.shift }}</dd>
        <dt>Ro'yxatdan o'tgan</dt><dd>{{ dmy(c.created_at) }}</dd><dt>Maksimal masofa</dt><dd>{{ VEHICLES[c.vehicle]?.max }}</dd>
        <dt>Telegram bot</dt><dd><Pill :tone="c.telegram_linked ? 'teal' : 'amber'">{{ c.telegram_linked ? 'Ulangan' : 'Ulanmagan' }}</Pill>
          <Btn v-if="c.telegram_linked && !auth.isStaff" sm style="margin-left:8px" @click="unlink">Uzish</Btn></dd>
      </dl>
      <div v-if="!c.telegram_linked" class="sub" style="margin-top:6px">Kuryer botga /start yozib, telefon va JShShIR bilan ulanadi — shundan keyin buyurtmalar Telegramga keladi.</div>
    </template>
    <template #footer>
      <template v-if="d">
        <a :href="`tel:+998${c.phone}`"><Btn variant="primary" icon="phone">Qo'ng'iroq</Btn></a>
        <Btn icon="msg" @click="ui.toast('Xabar yuborildi')">Xabar</Btn>
        <Btn icon="pin" @click="onMap">Xaritada</Btn>
        <span class="sp" />
        <Btn v-if="!auth.isStaff" variant="danger" @click="block">{{ c.account_status === 'blocked' ? 'Blokdan chiqarish' : 'Bloklash' }}</Btn>
      </template>
    </template>
    <TopupModal v-if="topup" :courier-id="id" @close="topup = false" @done="reload(true)" />
  </Drawer>
</template>

<style scoped>
.route{display:flex;flex-direction:column;gap:14px;position:relative}
.route::before{content:'';position:absolute;left:5px;top:12px;bottom:12px;border-left:2px dashed var(--line)}
.pt{display:flex;gap:12px;position:relative}.pt i{width:12px;height:12px;flex:none;margin-top:4px;background:var(--surface)}
.sq{border:2.5px solid var(--ink);border-radius:3px}.ci{border:3px solid var(--teal);border-radius:50%}
.items{width:100%;border-collapse:collapse;font-size:13px}.items td{padding:4px 0}.items .r{text-align:right}.items .tot td{font-weight:700;border-top:1px solid var(--line);padding-top:8px}
.qrow{padding:8px 10px;background:var(--surface-2);border-radius:9px;margin-bottom:6px;cursor:pointer;font-size:13px}
.led{margin-top:10px;display:flex;flex-direction:column}.lr{display:flex;gap:10px;align-items:center;padding:7px 0;border-top:1px solid var(--line-2)}
.lr>i{width:8px;height:8px;border-radius:50%;flex:none}.lt{flex:1;min-width:0}.lt b{font-size:13px;display:block}.lt small,.rt small{font-size:11.5px;color:var(--muted)}
.rt{text-align:right}.rt b{display:block;font-size:13px}
.lnk{display:inline-block;margin-top:10px;cursor:pointer;font-weight:600;font-size:13px}
</style>
