<script setup lang="ts">
defineProps<{ title?: string; flush?: boolean }>()
</script>
<template>
  <section class="panel">
    <header v-if="title || $slots.actions"><h3>{{ title }}</h3><div class="act"><slot name="actions" /></div></header>
    <div class="body" :class="{ flush }"><slot /></div>
  </section>
</template>
<style scoped>
.panel{background:var(--surface);border:1px solid var(--line);border-radius:14px;min-width:0}
header{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:14px 16px 0}
h3{font-size:15px;font-weight:700}.act{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--muted)}
.body{padding:14px 16px 16px}.body.flush{padding:0}
</style>
