<script setup lang="ts">
defineProps<{ modelValue: any; options: { value: any; label: string }[] }>()
defineEmits<{ 'update:modelValue': [any] }>()
</script>
<template>
  <div class="seg">
    <button v-for="o in options" :key="String(o.value)" :class="{ on: o.value === modelValue }" @click="$emit('update:modelValue', o.value)">{{ o.label }}</button>
  </div>
</template>
<style scoped>
.seg{display:inline-flex;background:var(--surface-2);border:1px solid var(--line);border-radius:10px;padding:3px;gap:2px;flex-wrap:wrap}
button{border:0;background:transparent;padding:5px 11px;border-radius:7px;font-size:12.5px;font-weight:600;color:var(--muted)}
button.on{background:var(--surface);color:var(--ink);box-shadow:0 1px 2px rgba(0,0,0,.12)}
</style>
