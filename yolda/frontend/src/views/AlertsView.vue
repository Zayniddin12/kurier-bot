<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { post, errMsg } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { useAlertsStore } from '@/stores/alerts'
import { useRestaurantsStore } from '@/stores/restaurants'
import { useDrawer } from '@/utils/drawer'
import { onLive } from '@/stores/live'
import { onMounted } from 'vue'
import CancelModal from '@/components/modals/CancelModal.vue'
import TopupModal from '@/components/modals/TopupModal.vue'
const ui = useUiStore(), al = useAlertsStore(), rs = useRestaurantsStore(), router = useRouter(), drawer = useDrawer()
const loading = ref(!al.items.length), error = ref('')
onMounted(async () => { try { await al.load() } catch (e) { error.value = errMsg(e) } loading.value = false })
onLive('alerts.changed', () => al.load().catch(() => {}))
const cancel = ref<number | null>(null), topup = ref(false)
const ICON: Record<string, string> = { issue: 'alert', late: 'clock', nocourier: 'bike', payfail: 'card', cash: 'dollar', restpaused: 'store', complaint: 'msg' }
async function call(fn: () => Promise<any>, msg: string) { try { await fn(); ui.toast(msg); al.load() } catch (e) { ui.toast(errMsg(e), 'var(--red)') } }
async function act(a: any, k: string) {
  const oid = a.order_id
  switch (k) {
    case 'resolve': return call(() => post(`/orders/${oid}/issue/resolve`), 'Muammo hal qilindi')
    case 'reassign': return call(() => post(`/orders/${oid}/issue/reassign`), "Buyurtma boshqa kuryerga o'tkazildi")
    case 'cancel':
      if (a.kind === 'issue') { if (!confirm(`#${oid} buyurtmani bekor qilasizmi?`)) return; return call(() => post(`/orders/${oid}/cancel`, { reason: `Muammo: ${a.title.replace(/^#\d+:\s*/, '')}` }), 'Buyurtma bekor qilindi') }
      cancel.value = oid; return
    case 'view_courier': ui.mapFocus = { courierId: a.courier_id }; return router.push('/map')
    case 'notify_customer': case 'write_customer': return call(() => post(`/orders/${oid}/notify-customer`), 'Mijozga xabar yuborildi')
    case 'details': return drawer.open('order', oid)
    case 'topup': topup.value = true; return
    case 'resume_restaurant': return call(async () => { await post(`/restaurants/${a.restaurant_id}/resume`); rs.load() }, 'Restoran faollashtirildi')
    case 'write_restaurant': return ui.toast('Restoranga xabar yuborildi')
  }
}
const dismiss = (a: any) => call(() => post(`/alerts/${encodeURIComponent(a.key)}/dismiss`), 'Yopildi')
</script>
<template>
  <div class="page">
    <Panel flush>
      <ErrorBox v-if="error" :message="error" @retry="al.load()" />
      <div v-else-if="loading" style="padding:16px"><Skeleton :h="50" :n="4" /></div>
      <template v-else-if="al.items.length">
        <div v-for="a in al.items" :key="a.key" class="al">
          <span class="ic" :style="{ background: `var(--${a.severity}-soft)`, color: `var(--${a.severity})` }"><Icon :name="ICON[a.kind] || 'bell'" /></span>
          <div class="tx"><b>{{ a.title }}</b><div class="sub">{{ a.text }}</div></div>
          <div class="ac">
            <template v-for="b in a.actions" :key="b.key">
              <a v-if="b.key === 'call_customer' && a.customer_phone" :href="`tel:${a.customer_phone}`"><Btn sm icon="phone">{{ b.label }}</Btn></a>
              <a v-else-if="b.key === 'call_restaurant' && a.restaurant_phone" :href="`tel:${a.restaurant_phone}`"><Btn sm icon="phone">{{ b.label }}</Btn></a>
              <Btn v-else-if="!b.key.startsWith('call_')" sm :variant="b.key === 'cancel' ? 'danger' : b.key === 'topup' || b.key === 'resolve' ? 'primary' : undefined" @click="act(a, b.key)">{{ b.label }}</Btn>
            </template>
            <Btn v-if="a.dismissible" sm variant="ghost" @click="dismiss(a)">Yopish</Btn>
          </div>
        </div>
      </template>
      <Empty v-else title="Hammasi joyida" text="Hozircha e'tibor talab qiladigan holat yo'q" />
    </Panel>
    <CancelModal v-if="cancel" :order-id="cancel" @close="cancel = null" @done="al.load()" />
    <TopupModal v-if="topup" @close="topup = false" @done="al.load()" />
  </div>
</template>
<style scoped>
.al{display:flex;align-items:center;gap:14px;padding:14px 16px;border-bottom:1px solid var(--line-2)}.al:last-child{border:0}
.ic{width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;flex:none}
.tx{flex:1;min-width:0}.tx b{font-size:14px}.ac{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
@media (max-width:860px){.al{flex-wrap:wrap}.ac{width:100%;justify-content:flex-start;padding-left:50px}}
</style>
