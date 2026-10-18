<script setup lang="ts">
defineProps<{ icon: string; title?: string }>()
</script>
<template><button class="ib" :title="title" :aria-label="title"><Icon :name="icon" /></button></template>
<style scoped>.ib{width:36px;height:36px;border-radius:9px;border:1px solid var(--line);background:var(--surface);display:inline-flex;align-items:center;justify-content:center;color:var(--ink);flex:none}.ib:hover{background:var(--surface-2)}</style>
