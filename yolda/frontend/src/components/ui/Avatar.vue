<script setup lang="ts">
import { computed } from 'vue'
const p = withDefaults(defineProps<{ seed?: number; female?: boolean; size?: number }>(), { seed: 0, size: 34 })
const BG = ['#FDE7A6', '#CFE8DD', '#D8E3FA', '#F4D6D2', '#E4DAF6', '#E2EAD0']
const SKIN = ['#F1C9A5', '#E0AC82', '#C98E63', '#A86F4C']
const HAIR = ['#2B1D14', '#3B2A1E', '#151515', '#5A3B22']
const c = computed(() => ({ bg: BG[p.seed % 6], skin: SKIN[Math.floor(p.seed / 6) % 4], hair: HAIR[Math.floor(p.seed / 24) % 4] }))
</script>
<template>
  <svg :width="size" :height="size" viewBox="0 0 40 40" style="border-radius:50%;flex:none">
    <rect width="40" height="40" :fill="c.bg" />
    <path d="M6 40c0-9 6-13 14-13s14 4 14 13z" fill="#F5B301" />
    <rect x="17" y="22" width="6" height="7" :fill="c.skin" />
    <path v-if="female" d="M10 20c0-9 4-13 10-13s10 4 10 13v10h-5V18H15v12h-5z" :fill="c.hair" />
    <circle cx="20" cy="17" r="7.5" :fill="c.skin" />
    <path v-if="female" d="M12.5 16c1-6 4-8 7.5-8s6.5 2 7.5 8c-3-2-5-3-7.5-3s-4.5 1-7.5 3z" :fill="c.hair" />
    <path v-else d="M12.5 15.5c0-5 3-8 7.5-8s7.5 3 7.5 8c-2-2-4-3-7.5-3s-5.5 1-7.5 3z" :fill="c.hair" />
  </svg>
</template>
