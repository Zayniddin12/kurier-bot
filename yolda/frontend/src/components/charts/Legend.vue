<script setup lang="ts">
defineProps<{ items: { label: string; color: string; dashed?: boolean }[] }>()
</script>
<template><div class="lg"><span v-for="i in items" :key="i.label"><i :style="{ background: i.color }" />{{ i.label }}</span></div></template>
<style scoped>.lg{display:flex;gap:12px;flex-wrap:wrap;font-size:12px;color:var(--muted)}span{display:inline-flex;align-items:center;gap:6px}i{width:10px;height:10px;border-radius:3px}</style>
