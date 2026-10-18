<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
export interface BarSeries { name: string; values: number[]; color: string }
const p = withDefaults(defineProps<{ series: BarSeries[]; labels: string[]; height?: number; every?: number }>(), { height: 190, every: 1 })
const W = ref(700)
const host = ref<HTMLElement>()
let ro: ResizeObserver | undefined
onMounted(() => { ro = new ResizeObserver(() => { if (host.value && host.value.clientWidth) W.value = host.value.clientWidth }); ro.observe(host.value!) })
onBeforeUnmount(() => ro?.disconnect())
const padL = 34, padR = 6, padT = 8, padB = 22
const niceMax = (m: number) => { if (m <= 0) return 4; const e = 10 ** Math.floor(Math.log10(m)); const f = m / e; return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * e }
const max = computed(() => niceMax(Math.max(...p.series.flatMap((s) => s.values), 0)))
const nl = computed(() => Math.max(p.labels.length, 1))
const slot = computed(() => (W.value - padL - padR) / nl.value)
const bw = computed(() => Math.min(24, (slot.value * 0.72) / p.series.length))
const H = computed(() => p.height - padT - padB)
const bars = computed(() => p.series.flatMap((s, si) => s.values.map((v, i) => {
  const h = (v / max.value) * H.value
  const x = padL + i * slot.value + (slot.value - bw.value * p.series.length) / 2 + si * bw.value
  return { x, y: padT + H.value - h, h, c: s.color, t: `${p.labels[i]} — ${s.name}: ${v}`, k: si + '-' + i }
})))
const grid = computed(() => [0, 1, 2, 3, 4].map((k) => (max.value * k) / 4))
const yy = (v: number) => padT + (1 - v / max.value) * H.value
</script>
<template>
  <div ref="host" style="width:100%"><svg :viewBox="`0 0 ${W} ${height}`" width="100%" :height="height" style="display:block">
    <g v-for="g in grid" :key="g">
      <line :x1="padL" :x2="W - padR" :y1="yy(g)" :y2="yy(g)" stroke="var(--line-2)" />
      <text :x="padL - 6" :y="yy(g) + 4" text-anchor="end" font-size="11" fill="var(--faint)">{{ Math.round(g * 10) / 10 }}</text>
    </g>
    <template v-for="(l, i) in labels" :key="i">
      <text v-if="i % every === 0" :x="padL + i * slot + slot / 2" :y="height - 6" text-anchor="middle" font-size="11" fill="var(--faint)">{{ l }}</text>
    </template>
    <path v-for="b in bars.filter((b) => b.h > 0)" :key="b.k" :fill="b.c"
      :d="`M${b.x} ${b.y + b.h}V${b.y + Math.min(3, b.h)}Q${b.x} ${b.y} ${b.x + Math.min(3, bw / 2)} ${b.y}H${b.x + bw - Math.min(3, bw / 2)}Q${b.x + bw} ${b.y} ${b.x + bw} ${b.y + Math.min(3, b.h)}V${b.y + b.h}Z`">
      <title>{{ b.t }}</title>
    </path>
  </svg></div>
</template>
