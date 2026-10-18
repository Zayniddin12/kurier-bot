<script setup lang="ts">
defineProps<{ tone?: string }>()
</script>
<template><span class="pill" :class="'p-' + (tone || 'grey')"><i /><slot /></span></template>
<style scoped>
.pill{display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:2px 9px 2px 8px;font-size:12px;font-weight:600;white-space:nowrap}
i{width:6px;height:6px;border-radius:50%;background:currentColor}
.p-teal{background:var(--teal-soft);color:var(--teal)}.p-blue{background:var(--blue-soft);color:var(--blue)}.p-amber{background:var(--amber-soft);color:var(--amber)}
.p-red{background:var(--red-soft);color:var(--red)}.p-grey{background:var(--grey-soft);color:var(--grey)}.p-violet{background:var(--violet-soft);color:var(--violet)}
</style>
