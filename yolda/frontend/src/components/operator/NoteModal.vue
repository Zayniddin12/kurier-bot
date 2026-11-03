<script setup lang="ts">
import { ref } from 'vue'
const p = defineProps<{ title: string; sub?: string; label: string; ok: string; initial?: string; required?: boolean; danger?: boolean }>()
const emit = defineEmits<{ close: []; submit: [string] }>()
const v = ref(p.initial || ''), err = ref('')
function go() {
  if (p.required && !v.value.trim()) { err.value = "Maydonni to'ldiring"; return }
  emit('submit', v.value.trim())
}
</script>
<template>
  <Modal :title="title" :sub="sub" @close="emit('close')">
    <div class="field"><label>{{ label }}</label><textarea v-model="v" class="inp" rows="4" maxlength="500" autofocus /><span v-if="err" class="err">{{ err }}</span></div>
    <template #footer><Btn @click="emit('close')">Bekor qilish</Btn><Btn :variant="danger ? 'dark' : 'primary'" @click="go">{{ ok }}</Btn></template>
  </Modal>
</template>
