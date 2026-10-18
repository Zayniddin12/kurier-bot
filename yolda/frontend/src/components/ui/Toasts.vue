<script setup lang="ts">
import { useUiStore } from '@/stores/ui'
const ui = useUiStore()
</script>
<template>
  <div class="tw">
    <div v-for="t in ui.toasts" :key="t.id" class="toast"><i :style="{ background: t.color }" />{{ t.text }}</div>
  </div>
</template>
<style scoped>
.tw{position:fixed;right:16px;bottom:calc(16px + env(safe-area-inset-bottom));display:flex;flex-direction:column;gap:8px;z-index:200;pointer-events:none}
.toast{background:var(--ink);color:var(--surface);border-radius:11px;padding:10px 14px;font-size:13px;max-width:340px;display:flex;gap:9px;align-items:flex-start;animation:up .25s;box-shadow:var(--shadow)}
.toast i{width:8px;height:8px;border-radius:50%;flex:none;margin-top:5px}
@keyframes up{from{transform:translateY(14px);opacity:0}}
</style>
