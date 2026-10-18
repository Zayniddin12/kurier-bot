<script setup lang="ts">
defineProps<{ on?: boolean; dot?: string; n?: number }>()
</script>
<template><button class="chip" :class="{ on }"><i v-if="dot" :style="{ background: dot }" /><slot /><b v-if="n != null">{{ n }}</b></button></template>
<style scoped>
.chip{border-radius:999px;padding:3px 10px;font-size:12px;font-weight:600;border:1px solid var(--line);background:var(--surface);color:var(--ink);display:inline-flex;align-items:center;gap:5px;white-space:nowrap}
.chip.on{background:var(--ink);color:var(--surface);border-color:var(--ink)}i{width:7px;height:7px;border-radius:50%}
</style>
