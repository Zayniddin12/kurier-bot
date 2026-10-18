<script setup lang="ts">
defineProps<{ title: string; text?: string }>()
</script>
<template><div class="e"><b>{{ title }}</b><p>{{ text }}</p></div></template>
<style scoped>.e{text-align:center;padding:28px 16px}.e b{display:block;font-size:15px}.e p{color:var(--muted);margin-top:3px}</style>
