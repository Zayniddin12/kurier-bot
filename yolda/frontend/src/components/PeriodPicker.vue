<script setup lang="ts">
import { computed, ref } from 'vue'
import { useUiStore, type Period } from '@/stores/ui'
import { dm, iso } from '@/utils/format'
const ui = useUiStore()
const open = ref(false)
const opts: { v: Period; l: string }[] = [
  { v: 'today', l: 'Bugun' }, { v: 'yesterday', l: 'Kecha' }, { v: 'week', l: 'Oxirgi 7 kun' }, { v: 'month', l: 'Oxirgi 30 kun' }, { v: 'range', l: "Sanalar oralig'i" },
]
const f = ref(ui.from), t = ref(ui.to)
const today = new Date(), min = iso(new Date(Date.now() - 29 * 864e5)), max = iso(today)
const label = computed(() => {
  const d = new Date()
  if (ui.period === 'today') return `Bugun, ${dm(d)}`
  if (ui.period === 'yesterday') return `Kecha, ${dm(new Date(Date.now() - 864e5))}`
  if (ui.period === 'week') return `${dm(new Date(Date.now() - 6 * 864e5))} — ${dm(d)}`
  if (ui.period === 'month') return `${dm(new Date(Date.now() - 29 * 864e5))} — ${dm(d)}`
  return ui.from && ui.to ? `${dm(ui.from)} — ${dm(ui.to)}` : "Sanalar oralig'i"
})
function pick(v: Period) { if (v !== 'range') { ui.period = v; open.value = false } else ui.period = 'range' }
function apply() { if (f.value && t.value) { ui.from = f.value; ui.to = t.value; ui.period = 'range'; open.value = false } }
</script>
<template>
  <div class="pp">
    <button class="btn" @click="open = !open"><Icon name="calendar" /><span><small>Davr</small><b>{{ label }}</b></span></button>
    <div v-if="open" class="back" @click="open = false" />
    <div v-if="open" class="pop">
      <div class="opts"><button v-for="o in opts" :key="o.v" :class="{ on: ui.period === o.v }" @click="pick(o.v)">{{ o.l }}</button></div>
      <div class="dates">
        <div class="field"><label>Dan</label><input v-model="f" type="date" class="inp" :min="min" :max="max" /></div>
        <div class="field"><label>Gacha</label><input v-model="t" type="date" class="inp" :min="min" :max="max" /></div>
      </div>
      <Btn variant="primary" style="width:100%;margin-top:10px" @click="apply">Qo'llash</Btn>
    </div>
  </div>
</template>
<style scoped>
.pp{position:relative}
.btn{height:42px;background:var(--surface-2);border:1px solid var(--line);border-radius:10px;padding:0 12px;display:flex;align-items:center;gap:9px;text-align:left}
.btn span{display:flex;flex-direction:column;line-height:1.15}.btn small{font-size:11px;color:var(--muted)}.btn b{font-size:13px;font-weight:600;white-space:nowrap}
.back{position:fixed;inset:0;z-index:40}
.pop{position:absolute;top:48px;right:0;width:300px;background:var(--surface);border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow);padding:12px;z-index:50}
.opts{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.opts button{border:1px solid var(--line);background:var(--surface);border-radius:8px;padding:7px;font-size:12.5px;font-weight:600}
.opts button.on{background:var(--ink);color:var(--surface);border-color:var(--ink)}
.dates{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}
@media (max-width:860px){.btn small{display:none}.pop{right:-60px}}
</style>
