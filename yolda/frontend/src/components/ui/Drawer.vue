<script setup lang="ts">
defineProps<{ title: string }>()
defineEmits<{ close: [] }>()
</script>
<template>
  <aside class="dr">
    <header><b>{{ title }}</b><IconBtn icon="x" title="Yopish" @click="$emit('close')" /></header>
    <div class="body"><slot /></div>
    <footer v-if="$slots.footer"><slot name="footer" /></footer>
  </aside>
</template>
<style scoped>
.dr{position:fixed;top:0;right:0;bottom:0;width:420px;max-width:100%;background:var(--surface);border-left:1px solid var(--line);box-shadow:var(--shadow);z-index:60;display:flex;flex-direction:column;animation:in .28s cubic-bezier(.2,.8,.2,1)}
@keyframes in{from{transform:translateX(105%)}to{transform:none}}
header{display:flex;align-items:center;justify-content:space-between;padding:12px 18px;border-bottom:1px solid var(--line);font-size:14px}
.body{flex:1;overflow:auto;padding:18px}
footer{padding:12px 18px calc(12px + env(safe-area-inset-bottom));border-top:1px solid var(--line);display:flex;gap:8px;flex-wrap:wrap;align-items:center}
</style>
