<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { get, post, patch, errMsg } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import { useRestaurantsStore } from '@/stores/restaurants'
import { useDrawer } from '@/utils/drawer'
import { useLoad } from '@/utils/useLoad'
import { dmy, agoSec, moneyS } from '@/utils/format'
import { REST_STATUS } from '@/constants/statuses'
import PromptModal from '../modals/PromptModal.vue'
import KeyModal from '../modals/KeyModal.vue'
const p = defineProps<{ id: number }>()
defineEmits<{ close: [] }>()
const ui = useUiStore(), auth = useAuthStore(), rs = useRestaurantsStore(), router = useRouter(), drawer = useDrawer()
const { data: d, loading, error, reload } = useLoad<any>(() => get(`/restaurants/${p.id}`), [() => p.id], ['order.created', 'order.updated', 'restaurant.updated'])
const r = computed(() => d.value?.restaurant)
const modal = ref<'' | 'pause' | 'hook'>('')
const key = ref<{ api_key: string } | null>(null)
const st = computed(() => (r.value ? REST_STATUS[r.value.status] : null))
async function run(fn: () => Promise<any>, msg: string) { try { const x = await fn(); ui.toast(msg); reload(true); rs.load(); return x } catch (e) { ui.toast(errMsg(e), 'var(--red)') } }
const pause = (reason: string) => { modal.value = ''; run(() => post(`/restaurants/${p.id}/pause`, { reason }), 'Restoran pauzaga qo\'yildi') }
const resume = () => run(() => post(`/restaurants/${p.id}/resume`), 'Restoran faollashtirildi')
const hook = (url: string) => { modal.value = ''; run(() => patch(`/restaurants/${p.id}`, { webhook_url: url }), 'Webhook saqlandi') }
async function rotate() {
  if (!confirm('Eski kalit ishlamay qoladi. Davom etasizmi?')) return
  const x = await run(() => post(`/restaurants/${p.id}/rotate-key`), 'Kalit yangilandi')
  if (x) key.value = x
}
const isSel = computed(() => ui.restaurantId === p.id)
</script>

<template>
  <Drawer title="Restoran" @close="$emit('close')">
    <ErrorBox v-if="error && !d" :message="error" @retry="reload()" />
    <Skeleton v-else-if="loading && !d" :h="40" :n="6" />
    <template v-else-if="d">
      <div class="row" style="gap:12px;align-items:flex-start">
        <RestLogo lg :name="r.name" :color="r.color" />
        <div style="flex:1"><b style="font-size:17px">{{ r.name }}</b><div class="sub">{{ r.cuisine }} · {{ r.district }}</div></div>
        <Pill :tone="st!.tone">{{ st!.label }}</Pill>
      </div>
      <div v-if="r.status === 'paused' && r.pause_reason" class="sub" style="margin-top:8px">Sabab: {{ r.pause_reason }}</div>
      <div class="mini-cards" style="margin-top:14px">
        <div class="mini"><b class="num">{{ r.today }}</b><span>Bugun</span></div>
        <div class="mini"><b class="num">{{ r.active }}</b><span>Faol hozir</span></div>
        <div class="mini"><b class="num">{{ r.prep_minutes }} daq</b><span>Tayyorlash</span></div>
      </div>
      <div class="sec-title">Oxirgi 7 kun</div>
      <BarChart :height="150" :labels="d.week.labels" :series="[{ name: 'Buyurtma', values: d.week.values, color: r.color }]" />
      <div class="sec-title">Faol buyurtmalar</div>
      <div v-for="o in d.active_orders" :key="o.id" class="qrow" @click="drawer.open('order', o.id)"><b>#{{ o.id }}</b> {{ o.customer_name }} · {{ moneyS(o.total) }}<Pill :tone="o.status_color" style="float:right">{{ o.status_text }}</Pill></div>
      <div v-if="!d.active_orders.length" class="muted">Faol buyurtma yo'q</div>
      <div class="sec-title">Ko'p buyurtma qilinadigan taomlar</div>
      <div v-for="(t, i) in d.top_items" :key="t.name" class="row" style="padding:3px 0;font-size:13px"><span class="faint" style="width:16px">{{ i + 1 }}</span>{{ t.name }}<span class="sp" /><b class="num">{{ t.qty }}</b></div>
      <div class="sec-title">Integratsiya</div>
      <dl class="kv">
        <dt>Turi</dt><dd>{{ d.integration.type }}<template v-if="d.integration.pos_system"> · {{ d.integration.pos_system }}</template></dd>
        <dt>Holati</dt><dd><Pill :tone="d.integration.ok ? 'teal' : 'amber'">{{ d.integration.ok ? 'Ulangan, ishlayapti' : 'Aloqa yo\'q' }}</Pill></dd>
        <dt>Oxirgi sinxronlash</dt><dd>{{ agoSec(d.integration.last_sync_at) }}</dd>
        <dt>API kalit</dt><dd class="num">yl_live_••••{{ d.integration.api_key_prefix ? ' ' + d.integration.api_key_prefix : '' }}</dd>
        <dt>Webhook URL</dt><dd style="word-break:break-all">{{ d.integration.webhook_url || '—' }}</dd>
      </dl>
      <div v-if="auth.canManage" class="row" style="margin-top:8px;gap:6px"><Btn sm icon="key" @click="rotate">Kalitni yangilash</Btn><Btn sm @click="modal = 'hook'">Webhook'ni sozlash</Btn></div>
      <div class="sec-title">Aloqa</div>
      <dl class="kv"><dt>Manzil</dt><dd>{{ r.address }}</dd><dt>Telefon</dt><dd><a :href="`tel:${r.phone}`">{{ r.phone }}</a></dd><dt>Menejer</dt><dd>{{ r.manager || '—' }}</dd><dt>Ish vaqti</dt><dd>{{ r.hours }}</dd><dt>Ulangan</dt><dd>{{ dmy(r.connected_at) }}</dd></dl>
    </template>
    <template #footer>
      <template v-if="d">
        <Btn variant="dark" @click="router.push({ path: '/orders', query: { r: id } })">Buyurtmalari</Btn>
        <Btn v-if="!auth.isStaff" @click="ui.restaurantId = isSel ? null : id">{{ isSel ? 'Tanlovni bekor qilish' : 'Panelda tanlash' }}</Btn>
        <span class="sp" />
        <template v-if="auth.canManage">
          <Btn v-if="r.status === 'paused'" variant="primary" @click="resume">Faollashtirish</Btn><Btn v-else @click="modal = 'pause'">Pauza</Btn>
        </template>
      </template>
    </template>
    <PromptModal v-if="modal === 'pause'" title="Restoranni pauzaga qo'yish" sub="Pauza davomida yangi buyurtma qabul qilinmaydi" label="Sabab" ok="Pauza" @close="modal = ''" @submit="pause" />
    <PromptModal v-if="modal === 'hook'" title="Webhook sozlash" label="Webhook URL" ok="Saqlash" :initial="d?.integration.webhook_url || ''" @close="modal = ''" @submit="hook" />
    <KeyModal v-if="key" :api-key="key.api_key" title="Yangi API kalit" @close="key = null" />
  </Drawer>
</template>

<style scoped>
.qrow{padding:8px 10px;background:var(--surface-2);border-radius:9px;margin-bottom:6px;cursor:pointer;font-size:13px}
</style>
