<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { get, post, errMsg } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { money } from '@/utils/format'
const p = defineProps<{ orderId: number; replacing?: boolean }>()
const emit = defineEmits<{ close: []; done: [any] }>()
const ui = useUiStore()
const q = ref(''), list = ref<any[]>([]), loading = ref(true), err = ref(''), busy = ref(0)
let t: any
async function load() {
  try { list.value = await get(`/operator/orders/${p.orderId}/couriers`, { q: q.value || undefined }); err.value = '' }
  catch (e) { err.value = errMsg(e) } finally { loading.value = false }
}
onMounted(load)
watch(q, () => { clearTimeout(t); t = setTimeout(load, 250) })
async function pick(c: any) {
  if (!c.selectable || busy.value) return
  busy.value = c.id
  try {
    const d = await post(`/operator/orders/${p.orderId}/assign`, { courier_id: c.id })
    ui.toast(`#${p.orderId} → ${c.name}${c.busy ? ' (navbatga qo\'yildi)' : ''}`)
    emit('done', d); emit('close')
  } catch (e) { err.value = errMsg(e) } finally { busy.value = 0 }
}
</script>
<template>
  <Modal :title="replacing ? 'Kuryerni almashtirish' : 'Kuryer tanlang'" :sub="replacing ? 'Tanlangan kuryer joriy kuryer o\'rniga biriktiriladi, eskisi bo\'shaydi.' : 'Tanlangach buyurtma kuryerga biriktiriladi. Band kuryer bo\'lsa navbatga qo\'yiladi.'" @close="emit('close')">
    <input v-model="q" class="inp" style="width:100%" placeholder="Ism, telefon yoki ID bo'yicha qidirish…" />
    <div v-if="err" class="e">{{ err }}</div>
    <div class="list">
      <Skeleton v-if="loading" :h="46" :n="4" />
      <button v-for="c in list" v-else :key="c.id" class="it" :disabled="!c.selectable || !!busy" @click="pick(c)">
        <Avatar :seed="c.avatar_seed" :female="c.is_female" :size="34" />
        <div class="mid">
          <b>{{ c.name }} <small class="faint">#{{ c.number }}</small></b>
          <div class="meta"><Pill :tone="c.status_tone">{{ c.status_label }}</Pill>
            <span :class="{ red: c.balance < 0 }" class="num">{{ money(c.balance) }} so'm</span><span>{{ c.vehicle }}</span><Tag v-if="c.over_limit">naqd limiti oshgan</Tag></div>
        </div>
        <div class="r num"><b v-if="c.eta_min != null">~{{ c.eta_min }} daq</b><span v-if="c.dist_km != null">{{ c.dist_km }} km</span></div>
      </button>
      <div v-if="!loading && !list.length" class="muted" style="padding:18px;text-align:center">Mos kuryer topilmadi</div>
    </div>
    <template #footer><Btn @click="emit('close')">Bekor</Btn></template>
  </Modal>
</template>
<style scoped>
.list{margin-top:10px;display:flex;flex-direction:column;gap:2px;max-height:48vh;overflow:auto}
.it{display:flex;align-items:center;gap:10px;text-align:left;border:0;background:transparent;padding:8px 8px;border-radius:10px;width:100%}
.it:hover:not(:disabled){background:var(--brand-soft)}.it:disabled{opacity:.5;cursor:default}
.mid{flex:1;min-width:0}.mid b{font-size:14px}.meta{display:flex;gap:8px;align-items:center;font-size:12px;color:var(--muted);margin-top:3px;flex-wrap:wrap}
.r{text-align:right;display:flex;flex-direction:column;font-size:12px;color:var(--muted)}.r b{color:var(--ink);font-size:13px}
.e{color:var(--red);font-size:12.5px;margin-top:8px}
</style>
