<script setup lang="ts">
defineProps<{ tone?: string }>()
</script>
<template><span class="pill" :class="'p-' + (tone || 'grey')"><slot /></span></template>
<style scoped>
.pill{display:inline-flex;align-items:center;border-radius:6px;padding:2px 10px;font-size:12px;font-weight:500;white-space:nowrap;line-height:1.5}
.p-teal{background:var(--teal-soft);color:var(--teal)}.p-blue{background:var(--blue-soft);color:var(--blue)}.p-amber{background:var(--amber-soft);color:var(--amber)}
.p-red{background:var(--red-soft);color:var(--red)}.p-grey{background:var(--grey-soft);color:var(--grey)}.p-violet{background:var(--violet-soft);color:var(--violet)}
</style>
