<script setup lang="ts">
defineProps<{ title: string; sub?: string; wide?: boolean }>()
defineEmits<{ close: [] }>()
</script>
<template>
  <Teleport to="body">
    <div class="ov" @mousedown.self="$emit('close')">
      <div class="m" :class="{ wide }" role="dialog" aria-modal="true">
        <header><div><h3>{{ title }}</h3><p v-if="sub">{{ sub }}</p></div><IconBtn icon="x" title="Yopish" @click="$emit('close')" /></header>
        <div class="b"><slot /></div>
        <footer v-if="$slots.footer"><slot name="footer" /></footer>
      </div>
    </div>
  </Teleport>
</template>
<style scoped>
.ov{position:fixed;inset:0;background:rgba(10,15,12,.45);z-index:100;display:flex;align-items:center;justify-content:center;padding:16px}
.m{background:var(--surface);border-radius:16px;width:560px;max-width:100%;max-height:86vh;display:flex;flex-direction:column;box-shadow:var(--shadow)}
.m.wide{width:880px}
header{display:flex;justify-content:space-between;gap:12px;padding:18px 20px 10px}
h3{font-size:17px;font-weight:700}p{font-size:13px;color:var(--muted);margin-top:2px}
.b{padding:6px 20px 16px;overflow:auto}
footer{padding:12px 20px 16px;display:flex;justify-content:flex-end;gap:8px;align-items:center;border-top:1px solid var(--line-2)}
</style>
