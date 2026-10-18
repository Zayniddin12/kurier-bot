<script setup lang="ts">
withDefaults(defineProps<{ h?: number; n?: number }>(), { h: 18, n: 1 })
</script>
<template><div style="display:flex;flex-direction:column;gap:8px"><div v-for="i in n" :key="i" class="skeleton" :style="{ height: h + 'px' }" /></div></template>
