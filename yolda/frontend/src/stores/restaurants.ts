import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { get } from '@/api/client'

export const asArr = (x: any): any[] => (Array.isArray(x) ? x : x?.items || [])

export const useRestaurantsStore = defineStore('restaurants', () => {
  const items = ref<any[]>([])
  const loaded = ref(false)
  const byId = computed(() => Object.fromEntries(items.value.map((r) => [r.id, r])))
  async function load() {
    items.value = asArr(await get('/restaurants'))
    loaded.value = true
  }
  function patch(r: any) {
    const i = items.value.findIndex((x) => x.id === r.id)
    if (i >= 0) items.value[i] = { ...items.value[i], ...r }
    else items.value.push(r)
  }
  return { items, loaded, byId, load, patch }
})
