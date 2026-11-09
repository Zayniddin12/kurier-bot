<script setup lang="ts">
import { get } from '@/api/client'
import { useLoad } from '@/utils/useLoad'
import { money } from '@/utils/format'
const p = defineProps<{ r: any }>()
defineEmits<{ close: [] }>()
const { data, loading, error } = useLoad<any>(() => get(`/operator/restaurants/${p.r.id}/menu`))
</script>
<template>
  <Modal title="Menyu" :sub="`${r.name} · statik menyu (POS integratsiyasi ulanguncha)`" @close="$emit('close')">
    <ErrorBox v-if="error" :message="error" />
    <Skeleton v-else-if="loading && !data" :h="36" :n="5" />
    <table v-else class="t"><tbody>
      <tr v-for="(m, i) in data.items" :key="m.id"><td class="faint">{{ i + 1 }}</td><td><b>{{ m.name }}</b></td><td class="r num">{{ money(m.price) }} so'm</td></tr>
    </tbody></table>
  </Modal>
</template>
<style scoped>.t{width:100%;border-collapse:collapse;font-size:13.5px}.t td{padding:9px 4px;border-bottom:1px solid var(--line-2)}.r{text-align:right;white-space:nowrap}</style>
