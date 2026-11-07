<script setup lang="ts">
defineProps<{ icon: string; title?: string }>()
</script>
<template><button class="ib" :title="title" :aria-label="title"><Icon :name="icon" :size="16" /></button></template>
<style scoped>.ib{width:34px;height:34px;border-radius:8px;border:1px solid var(--line);background:var(--surface);display:inline-flex;align-items:center;justify-content:center;color:var(--ink);flex:none}.ib:hover{background:var(--surface-2)}</style>
