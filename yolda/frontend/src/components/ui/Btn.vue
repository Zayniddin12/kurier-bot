<script setup lang="ts">
defineProps<{ variant?: 'primary' | 'dark' | 'ghost' | 'danger'; sm?: boolean; icon?: string; type?: 'button' | 'submit'; disabled?: boolean }>()
</script>
<template>
  <button :type="type || 'button'" :disabled="disabled" class="btn" :class="[variant, { sm }]">
    <Icon v-if="icon" :name="icon" :size="16" /><slot />
  </button>
</template>
<style scoped>
.btn{height:34px;padding:0 13px;border-radius:9px;border:1px solid var(--line);background:var(--surface);font-size:13px;font-weight:600;display:inline-flex;align-items:center;justify-content:center;gap:6px;white-space:nowrap;color:var(--ink)}
.btn:hover{background:var(--surface-2)}
.btn:disabled{opacity:.55;cursor:default}
.primary{background:var(--brand);border-color:var(--brand);color:var(--brand-ink)}.primary:hover{background:var(--brand);filter:brightness(.95)}
.dark{background:var(--ink);border-color:var(--ink);color:var(--surface)}.dark:hover{background:var(--ink);opacity:.9}
.ghost{background:transparent;border-color:transparent}
.danger{color:var(--red)}
.sm{height:28px;padding:0 10px;font-size:12px;border-radius:7px}
</style>
