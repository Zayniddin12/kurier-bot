<script setup lang="ts">
import { useUiStore } from '@/stores/ui'
const p = defineProps<{ apiKey?: string | null; secret?: string; title?: string }>()
const emit = defineEmits<{ close: [] }>()
const ui = useUiStore()
async function copy(t: string) { try { await navigator.clipboard.writeText(t); ui.toast('Nusxalandi') } catch { ui.toast('Nusxalab bo\'lmadi', 'var(--red)') } }
</script>
<template>
  <Modal :title="title || 'API kalit'" sub="Integratsiya uchun kalit" @close="emit('close')">
    <div class="box red" style="margin-bottom:12px">Bu ma'lumot qayta ko'rsatilmaydi — hozir nusxalab oling.</div>
    <div v-if="apiKey" class="field"><label>API kalit</label><div class="row"><code class="k">{{ apiKey }}</code><Btn sm icon="copy" @click="copy(apiKey)">Nusxalash</Btn></div></div>
    <div v-if="secret" class="field" style="margin-top:10px"><label>Webhook secret</label><div class="row"><code class="k">{{ secret }}</code><Btn sm icon="copy" @click="copy(secret)">Nusxalash</Btn></div></div>
    <template #footer><Btn variant="primary" @click="emit('close')">Tushunarli</Btn></template>
  </Modal>
</template>
<style scoped>.k{flex:1;background:var(--surface-2);border:1px solid var(--line);border-radius:9px;padding:8px 10px;font-size:12.5px;word-break:break-all}</style>
