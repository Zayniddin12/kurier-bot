<script setup lang="ts">
defineProps<{ variant?: 'primary' | 'dark' | 'ghost' | 'danger'; sm?: boolean; icon?: string; type?: 'button' | 'submit'; disabled?: boolean }>()
</script>
<template>
  <button :type="type || 'button'" :disabled="disabled" class="btn" :class="[variant, { sm }]">
    <Icon v-if="icon" :name="icon" :size="sm ? 14 : 16" /><slot />
  </button>
</template>
<style scoped>
.btn{height:36px;padding:0 14px;border-radius:8px;border:1px solid var(--line);background:var(--surface);font-size:13.5px;font-weight:600;display:inline-flex;align-items:center;justify-content:center;gap:6px;white-space:nowrap;color:var(--ink)}
.btn:hover{background:var(--surface-2)}
.btn:disabled{opacity:.55;cursor:default}
.primary{background:var(--primary);border-color:var(--primary);color:var(--primary-ink)}.primary:hover{background:var(--primary);filter:brightness(.94)}
.dark{background:var(--side);border-color:var(--side);color:#fff}.dark:hover{background:var(--side);opacity:.92}
.ghost{background:transparent;border-color:transparent}
.danger{color:var(--red);border-color:color-mix(in srgb,var(--red) 35%,var(--line))}
.sm{height:26px;padding:0 10px;font-size:12.5px;font-weight:500;border-radius:6px}
.sm.danger{border-radius:999px;padding:0 11px}
</style>
