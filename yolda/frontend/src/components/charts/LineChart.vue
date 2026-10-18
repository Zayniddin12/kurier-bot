<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
export interface Series { name: string; values: (number | null)[]; color?: string; dashed?: boolean; fill?: boolean }
const p = withDefaults(defineProps<{ series: Series[]; labels: string[]; every?: number; height?: number; fmt?: (n: number) => string }>(), { every: 1, height: 230 })
const W = ref(700)
const host = ref<HTMLElement>()
let ro: ResizeObserver | undefined
onMounted(() => { ro = new ResizeObserver(() => { if (host.value && host.value.clientWidth) W.value = host.value.clientWidth }); ro.observe(host.value!) })
onBeforeUnmount(() => ro?.disconnect())
const padL = 38, padR = 8, padT = 10, padB = 24
const niceMax = (m: number) => { if (m <= 0) return 1; const e = 10 ** Math.floor(Math.log10(m)); const f = m / e; return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * e }
const max = computed(() => niceMax(Math.max(...p.series.flatMap((s) => s.values.filter((v): v is number => v != null)), 0)))
const n = computed(() => Math.max(p.labels.length, 2))
const x = (i: number) => padL + (i * (W.value - padL - padR)) / (n.value - 1)
const y = (v: number) => padT + (1 - v / max.value) * (p.height - padT - padB)
const f = (v: number) => (p.fmt ? p.fmt(v) : String(Math.round(v * 10) / 10))
const grid = computed(() => [0, 1, 2, 3, 4].map((k) => (max.value * k) / 4))
const paths = computed(() => p.series.map((s) => {
  const pts = s.values.map((v, i) => (v == null ? null : [x(i), y(v)] as [number, number])).filter(Boolean) as [number, number][]
  const d = pts.map((q, i) => `${i ? 'L' : 'M'}${q[0].toFixed(1)} ${q[1].toFixed(1)}`).join(' ')
  const area = pts.length ? `${d} L${pts[pts.length - 1][0]} ${p.height - padB} L${pts[0][0]} ${p.height - padB}Z` : ''
  return { s, d, area, pts }
}))
</script>
<template>
  <div ref="host" style="width:100%"><svg :viewBox="`0 0 ${W} ${height}`" width="100%" :height="height" style="display:block">
    <g v-for="g in grid" :key="g">
      <line :x1="padL" :x2="W - padR" :y1="y(g)" :y2="y(g)" stroke="var(--line-2)" />
      <text :x="padL - 6" :y="y(g) + 4" text-anchor="end" font-size="11" fill="var(--faint)">{{ f(g) }}</text>
    </g>
    <template v-for="(q, i) in labels" :key="i">
      <text v-if="i % every === 0" :x="x(i)" :y="height - 6" text-anchor="middle" font-size="11" fill="var(--faint)">{{ q }}</text>
    </template>
    <g v-for="(pp, k) in paths" :key="k">
      <path v-if="pp.s.fill" :d="pp.area" :fill="pp.s.color || 'var(--brand)'" opacity=".16" />
      <path :d="pp.d" fill="none" :stroke="pp.s.color || 'var(--brand)'" stroke-width="2.2" stroke-linejoin="round" :stroke-dasharray="pp.s.dashed ? '5 4' : undefined" />
      <circle v-for="(q, i) in pp.pts" :key="i" :cx="q[0]" :cy="q[1]" r="7" fill="transparent">
        <title>{{ labels[Math.round(((q[0] - padL) / (W - padL - padR)) * (n - 1))] }} — {{ pp.s.name }}: {{ f(((p.height - padB - q[1]) / (p.height - padT - padB)) * max) }}</title>
      </circle>
    </g>
  </svg></div>
</template>
