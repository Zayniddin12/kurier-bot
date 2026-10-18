<script setup lang="ts">
import { computed } from 'vue'
import { initials } from '@/utils/format'
const p = defineProps<{ name?: string; color?: string; lg?: boolean; all?: boolean }>()
const txt = computed(() => (p.all ? 'Hm' : initials(p.name || '?')))
</script>
<template><span class="lg" :class="{ big: lg }" :style="all ? { background: 'var(--ink)', color: 'var(--surface)' } : { background: color || '#888' }">{{ txt }}</span></template>
<style scoped>
.lg{width:30px;height:30px;border-radius:8px;color:#fff;font-size:12px;font-weight:700;display:inline-flex;align-items:center;justify-content:center;flex:none}
.big{width:44px;height:44px;border-radius:11px;font-size:15px}
</style>
