<script setup lang="ts">
import { useUiStore } from '@/stores/ui'
const ui = useUiStore()
const bg = (c: string) => (c === 'var(--brand)' ? 'var(--side)' : c === 'var(--teal)' ? 'var(--primary)' : c)
</script>
<template>
  <div class="tw">
    <div v-for="t in ui.toasts" :key="t.id" class="toast" :style="{ background: bg(t.color) }">{{ t.text }}</div>
  </div>
</template>
<style scoped>
.tw{position:fixed;left:50%;transform:translateX(-50%);top:calc(16px + env(safe-area-inset-top));display:flex;flex-direction:column;align-items:center;gap:8px;z-index:200;pointer-events:none;width:max-content;max-width:calc(100vw - 24px)}
.toast{color:#fff;border-radius:8px;padding:10px 16px;font-size:14px;font-weight:600;min-width:240px;max-width:520px;animation:up .25s;box-shadow:0 6px 20px rgba(0,0,0,.18)}
@keyframes up{from{transform:translateY(-10px);opacity:0}}
</style>
