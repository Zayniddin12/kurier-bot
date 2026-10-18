<script setup lang="ts">
defineProps<{ modelValue: string; placeholder?: string }>()
defineEmits<{ 'update:modelValue': [string] }>()
</script>
<template>
  <div class="s"><Icon name="search" :size="16" /><input class="inp" :value="modelValue" :placeholder="placeholder" @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)" /></div>
</template>
<style scoped>
.s{position:relative;display:block}.s :deep(svg){position:absolute;left:10px;top:50%;transform:translateY(-50%);color:var(--faint)}
.inp{padding-left:32px!important;width:100%}
</style>
