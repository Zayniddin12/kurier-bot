<script setup lang="ts">
defineProps<{ on?: boolean; dot?: string; n?: number }>()
</script>
<template><button class="chip" :class="{ on }"><i v-if="dot" :style="{ background: dot }" /><slot /><b v-if="n != null">{{ n }}</b></button></template>
<style scoped>
.chip{height:26px;border-radius:999px;padding:0 10px;font-size:13px;font-weight:500;border:1px solid var(--line);background:var(--surface);color:var(--ink);display:inline-flex;align-items:center;gap:6px;white-space:nowrap}
.chip b{font-weight:500;font-size:12px;color:var(--muted)}
.chip:hover{background:var(--surface-2)}
.chip.on{background:var(--side);color:#fff;border-color:var(--side)}.chip.on b{color:rgba(255,255,255,.75)}i{width:7px;height:7px;border-radius:50%}
</style>
