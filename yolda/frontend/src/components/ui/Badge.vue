<script setup lang="ts">
defineProps<{ n?: number }>()
</script>
<template><span v-if="n" class="badge">{{ n }}</span></template>
<style scoped>.badge{min-width:20px;height:20px;padding:0 6px;border-radius:10px;background:var(--red);color:#fff;font-size:11px;font-weight:700;display:inline-flex;align-items:center;justify-content:center}</style>
