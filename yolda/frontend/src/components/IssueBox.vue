<script setup lang="ts">
import { post, errMsg } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { ISSUES } from '@/constants/statuses'
const p = defineProps<{ issue: any }>()
const emit = defineEmits<{ done: [] }>()
const ui = useUiStore()
const mmss = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
async function act(k: string) {
  const i = p.issue
  try {
    if (k === 'resolve') { await post(`/orders/${i.order_id}/issue/resolve`); ui.toast('Muammo hal qilindi') }
    else if (k === 'reassign') { await post(`/orders/${i.order_id}/issue/reassign`); ui.toast('Buyurtma boshqa kuryerga o\'tkazildi') }
    else if (k === 'cancel') {
      if (!confirm(`#${i.order_id} buyurtmani bekor qilasizmi?`)) return
      await post(`/orders/${i.order_id}/cancel`, { reason: `Muammo: ${i.text}` }); ui.toast('Buyurtma bekor qilindi', 'var(--red)')
    }
    emit('done')
  } catch (e) { ui.toast(errMsg(e), 'var(--red)') }
}
</script>
<template>
  <div class="box red">
    <b>{{ issue.text }}</b>
    <div class="sub" style="color:var(--muted)">Kuryer · {{ mmss(issue.seconds || 0) }} davom etmoqda · kutilayotgan kechikish +{{ issue.delay_min }} daq</div>
    <div class="row" style="margin-top:8px;flex-wrap:wrap;gap:6px">
      <template v-for="b in issue.buttons" :key="b.key">
        <a v-if="b.key === 'call_customer' && issue.customer_phone" :href="`tel:${issue.customer_phone}`"><Btn sm icon="phone">{{ b.label }}</Btn></a>
        <a v-else-if="b.key === 'call_restaurant' && issue.restaurant_phone" :href="`tel:${issue.restaurant_phone}`"><Btn sm icon="phone">{{ b.label }}</Btn></a>
        <Btn v-else-if="b.key === 'resolve' || b.key === 'reassign'" sm variant="dark" @click="act(b.key)">{{ b.label }}</Btn>
        <Btn v-else-if="b.key === 'cancel'" sm variant="danger" @click="act('cancel')">{{ b.label }}</Btn>
      </template>
    </div>
  </div>
</template>
