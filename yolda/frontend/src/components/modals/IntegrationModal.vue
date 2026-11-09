<script setup lang="ts">
import { ref } from 'vue'
import { post, patch, errMsg } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { agoSec } from '@/utils/format'
import PromptModal from './PromptModal.vue'
import KeyModal from './KeyModal.vue'
const p = defineProps<{ r: any }>()
const emit = defineEmits<{ close: []; done: [] }>()
const ui = useUiStore()
const hook = ref(false), key = ref<{ api_key: string } | null>(null)
async function rotate() {
  if (!confirm('Eski kalit ishlamay qoladi. Davom etasizmi?')) return
  try { key.value = await post(`/restaurants/${p.r.id}/rotate-key`); ui.toast('Kalit yangilandi'); emit('done') } catch (e) { ui.toast(errMsg(e), 'var(--red)') }
}
async function saveHook(url: string) {
  hook.value = false
  try { await patch(`/restaurants/${p.r.id}`, { webhook_url: url }); ui.toast('Webhook saqlandi'); emit('done') } catch (e) { ui.toast(errMsg(e), 'var(--red)') }
}
</script>
<template>
  <Modal title="Integratsiya" :sub="r.name" @close="emit('close')">
    <dl class="kv">
      <dt>Turi</dt><dd>{{ r.integration_type }}<template v-if="r.pos_system"> · {{ r.pos_system }}</template></dd>
      <dt>Holati</dt><dd><Pill :tone="r.sync_ok ? 'teal' : 'amber'">{{ r.sync_ok ? 'Ulangan, ishlayapti' : "Aloqa yo'q" }}</Pill></dd>
      <dt>Oxirgi sinxronlash</dt><dd>{{ agoSec(r.last_sync_at) }}</dd>
      <dt>API kalit</dt><dd class="num">yl_live_••••{{ r.api_key_prefix ? ' ' + r.api_key_prefix : '' }}</dd>
      <dt>Webhook URL</dt><dd style="word-break:break-all">{{ r.webhook_url || '—' }}</dd>
    </dl>
    <template #footer><Btn icon="key" @click="rotate">Kalitni yangilash</Btn><Btn @click="hook = true">Webhook'ni sozlash</Btn></template>
    <PromptModal v-if="hook" title="Webhook sozlash" label="Webhook URL" ok="Saqlash" :initial="r.webhook_url || ''" @close="hook = false" @submit="saveHook" />
    <KeyModal v-if="key" :api-key="key.api_key" title="Yangi API kalit" @close="key = null" />
  </Modal>
</template>
