<script setup lang="ts">
defineProps<{ message: string }>(); defineEmits<{ retry: [] }>()
</script>
<template><div class="e"><p>{{ message }}</p><Btn sm @click="$emit('retry')">Qayta urinish</Btn></div></template>
<style scoped>.e{text-align:center;padding:24px;display:flex;flex-direction:column;gap:10px;align-items:center}.e p{color:var(--red)}</style>
