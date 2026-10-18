<script setup lang="ts">
import { hm } from '@/utils/format'
defineProps<{ steps: { key: string; label: string; at?: string; state: string }[] }>()
</script>
<template>
  <div class="st">
    <div v-for="s in steps" :key="s.key" class="s" :class="s.state">
      <i /><span>{{ s.label }}</span><span class="sp" /><small class="num">{{ s.at ? hm(s.at) : '' }}</small>
    </div>
  </div>
</template>
<style scoped>
.st{display:flex;flex-direction:column;gap:10px}
.s{display:flex;align-items:center;gap:10px;font-size:13px;color:var(--faint)}
.s i{width:9px;height:9px;border-radius:50%;background:var(--line)}
.s.done{color:var(--ink)}.s.done i{background:var(--teal)}
.s.current{color:var(--ink);font-weight:700}.s.current i{background:var(--brand)}
.s.cancelled{color:var(--red);font-weight:600}.s.cancelled i{background:var(--red)}
small{color:var(--muted)}
</style>
