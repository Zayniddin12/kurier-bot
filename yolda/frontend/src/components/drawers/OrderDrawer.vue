<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { get, post, errMsg } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { useDrawer } from '@/utils/drawer'
import { useLoad } from '@/utils/useLoad'
import { money, moneyS, dmyhm, ago } from '@/utils/format'
import IssueBox from '../IssueBox.vue'
import EtaBox from '../EtaBox.vue'
import Steps from '../Steps.vue'
import CancelModal from '../modals/CancelModal.vue'
const p = defineProps<{ id: number }>()
defineEmits<{ close: [] }>()
const ui = useUiStore(), router = useRouter(), drawer = useDrawer()
const { data: o, loading, error, reload } = useLoad<any>(() => get(`/orders/${p.id}`), [() => p.id], ['order.updated', 'issue.opened', 'issue.closed'])
const cancel = ref(false)
const active = computed(() => o.value && ['new', 'assigned', 'onway'].includes(o.value.status))
const pay = computed(() => o.value?.payment)
async function notify() { try { await post(`/orders/${p.id}/notify-customer`); ui.toast('Mijozga xabar yuborildi') } catch (e) { ui.toast(errMsg(e), 'var(--red)') } }
function onMap() { ui.mapFocus = { courierId: o.value?.courier?.id }; router.push('/map') }
const stars = (n: number) => '★'.repeat(n) + '☆'.repeat(5 - n)
</script>

<template>
  <Drawer :title="`Buyurtma #${id}`" @close="$emit('close')">
    <ErrorBox v-if="error && !o" :message="error" @retry="reload()" />
    <Skeleton v-else-if="loading && !o" :h="40" :n="6" />
    <template v-else-if="o">
      <div class="row" style="gap:12px;align-items:flex-start">
        <RestLogo lg :name="o.restaurant.name" :color="o.restaurant.color" />
        <div style="flex:1"><b style="font-size:16px">{{ o.restaurant.name }}</b><div class="sub">{{ dmyhm(o.created_at) }} · {{ ago(o.created_at) }}</div></div>
        <Pill :tone="o.status_color">{{ o.status_text }}</Pill>
      </div>

      <IssueBox v-if="o.issue" :issue="o.issue" style="display:block;margin-top:14px" @done="reload(true)" />
      <div v-if="o.status === 'new' && o.search" class="box" style="margin-top:14px">
        <b>Avtomatik taqsimlash</b>
        <div>{{ o.search.pending_payment ? 'Onlayn to\'lov tasdiqlanishi kutilmoqda' : o.search.offer_courier ? `Taklif yuborildi: ${o.search.offer_courier.name}` : 'Mos kuryer qidirilmoqda' }}</div>
        <div class="sub">{{ o.search.declined_count }} ta kuryer rad etdi · {{ o.search.wait_minutes }} daq kutmoqda · naqd: limitdan oshgan kuryerlarga berilmaydi</div>
      </div>
      <div v-if="o.eta && o.courier && active" style="margin-top:14px"><EtaBox :eta="o.eta" /></div>
      <div v-if="o.status === 'delivered'" class="mini-cards" style="margin-top:14px">
        <div class="mini"><b :class="{ red: o.is_late }">{{ o.delivery_minutes }} daq<small v-if="o.is_late"> · kechikdi</small></b><span>Yetkazish</span></div>
        <div class="mini"><b>{{ o.prep_minutes ?? '—' }} daq</b><span>Tayyorlash</span></div>
        <div class="mini"><b>{{ o.distance_km != null ? o.distance_km.toFixed(1) : '—' }} km</b><span>Masofa</span></div>
      </div>

      <div class="sec-title">Mijoz</div>
      <div class="route">
        <div class="pt"><i class="sq" /><div><b>{{ o.restaurant.name }}</b><div class="sub">{{ o.restaurant.address }}</div></div></div>
        <div class="pt"><i class="ci" /><div><b>{{ o.customer_name }} · <a :href="`tel:${o.customer_phone}`">{{ o.customer_phone }}</a></b><div class="sub">{{ o.district }}, {{ o.address }}</div>
          <div v-if="o.note" class="sub">Izoh: {{ o.note }}</div></div></div>
      </div>

      <div class="sec-title">Kuryer</div>
      <div v-if="o.courier" class="crow" @click="drawer.open('courier', o.courier.id)">
        <Avatar :seed="o.courier.avatar_seed" :female="o.courier.is_female" :size="34" /><div style="flex:1"><b>{{ o.courier.name }}</b><div class="sub">#{{ o.courier.number }} · {{ o.courier.vehicle }}</div></div>
        <Tag v-if="o.queued">navbatda</Tag>
      </div>
      <div v-else class="muted">Tizim avtomatik biriktiradi</div>

      <div class="sec-title">To'lov</div>
      <dl class="kv">
        <dt>To'lov usuli</dt><dd>{{ pay.method }}</dd>
        <dt>Holati</dt><dd><Pill :tone="pay.status_color">{{ pay.status_text }}</Pill></dd>
        <template v-if="pay.method === 'Naqd'"><dt>Kuryer mijozdan oladi</dt><dd class="num">{{ moneyS(pay.courier_collects) }}</dd><dt>Kompaniyaga topshiradi</dt><dd class="num">{{ moneyS(pay.company_due) }}</dd></template>
        <dt>Kuryer haqi</dt><dd class="num">{{ moneyS(pay.courier_fee) }}</dd>
        <dt>Platforma komissiyasi</dt><dd class="num">{{ moneyS(pay.commission) }}</dd>
      </dl>

      <div class="sec-title">Tarkibi</div>
      <table class="items"><tbody>
        <tr v-for="(it, i) in o.items" :key="i"><td>{{ it.qty }} × {{ it.name }}</td><td class="num r">{{ money(it.qty * it.price) }}</td></tr>
        <tr><td class="muted">Yetkazish</td><td class="num r">{{ money(o.delivery_fee) }}</td></tr>
        <tr class="tot"><td>Jami · {{ o.pay_method }}</td><td class="num r">{{ moneyS(o.total) }}</td></tr>
      </tbody></table>

      <div class="sec-title">Buyurtma bosqichlari</div>
      <Steps :steps="o.timeline" />
      <div v-if="o.status === 'cancelled' && o.cancel_reason" class="red" style="margin-top:6px;font-size:13px">Bekor qilindi: {{ o.cancel_reason }}</div>

      <template v-if="o.issues?.length">
        <div class="sec-title">Muammolar tarixi</div>
        <div v-for="i in o.issues" :key="i.id" class="hist"><b>{{ i.text }}</b><span class="sub"> · {{ dmyhm(i.started_at) }}{{ i.resolved_by ? ' · ' + i.resolved_by : '' }}</span></div>
      </template>
      <template v-if="o.customer_rating">
        <div class="sec-title">Mijoz bahosi</div>
        <div style="color:var(--brand);font-size:18px;letter-spacing:2px">{{ stars(o.customer_rating) }}</div>
      </template>
    </template>
    <template #footer>
      <template v-if="o">
        <Btn v-if="active" icon="pin" @click="onMap">Xaritada</Btn>
        <Btn icon="msg" @click="notify">Mijozga yozish</Btn>
        <span class="sp" />
        <Btn v-if="active" variant="danger" @click="cancel = true">Bekor qilish</Btn>
      </template>
    </template>
    <CancelModal v-if="cancel" :order-id="id" @close="cancel = false" @done="reload(true)" />
  </Drawer>
</template>

<style scoped>
.route{display:flex;flex-direction:column;gap:14px;position:relative}
.route::before{content:'';position:absolute;left:5px;top:12px;bottom:12px;border-left:2px dashed var(--line)}
.pt{display:flex;gap:12px;position:relative}.pt i{width:12px;height:12px;flex:none;margin-top:4px;background:var(--surface)}
.sq{border:2.5px solid var(--ink);border-radius:3px}.ci{border:3px solid var(--teal);border-radius:50%}
.crow{display:flex;align-items:center;gap:10px;cursor:pointer;background:var(--surface-2);border-radius:11px;padding:10px}
.items{width:100%;border-collapse:collapse;font-size:13px}.items td{padding:4px 0}.items .r{text-align:right}.items .tot td{font-weight:700;border-top:1px solid var(--line);padding-top:8px}
.hist{font-size:13px;padding:3px 0}
</style>
