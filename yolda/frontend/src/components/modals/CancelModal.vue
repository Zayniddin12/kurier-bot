<script setup lang="ts">
import { ref } from 'vue'
import { post, errMsg } from '@/api/client'
import { useUiStore } from '@/stores/ui'
const p = defineProps<{ orderId: number }>()
const emit = defineEmits<{ close: []; done: [] }>()
const ui = useUiStore()
const reason = ref(''), err = ref('')
async function go() {
  if (!reason.value.trim()) { err.value = 'Sababni kiriting'; return }
  try {
    const r = await post(`/orders/${p.orderId}/cancel`, { reason: reason.value })
    ui.toast(`Buyurtma #${p.orderId} bekor qilindi${r.refunded ? " · to'lov mijozga qaytarildi" : ''}`, 'var(--red)')
    emit('done'); emit('close')
  } catch (e) { err.value = errMsg(e) }
}
</script>
<template>
  <Modal :title="`#${orderId} ni bekor qilish`" sub="Bekor qilish sababini kiriting" @close="emit('close')">
    <div class="field"><label>Sabab</label><textarea v-model="reason" class="inp" rows="3" /><span v-if="err" class="err">{{ err }}</span></div>
    <template #footer><Btn @click="emit('close')">Yopish</Btn><Btn variant="dark" @click="go">Bekor qilish</Btn></template>
  </Modal>
</template>
