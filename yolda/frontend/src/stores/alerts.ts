import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { get } from '@/api/client'
import { asArr } from './restaurants'
import { useUiStore } from './ui'

export const useAlertsStore = defineStore('alerts', () => {
  const items = ref<any[]>([])
  const count = computed(() => items.value.length)
  async function load() {
    const ui = useUiStore()
    items.value = asArr(await get('/alerts', { restaurant_id: ui.restaurantId || undefined }))
  }
  return { items, count, load }
})
