import { ref, watch, onMounted, type WatchSource, shallowRef } from 'vue'
import { errMsg } from '@/api/client'
import { onLive } from '@/stores/live'
import { useUiStore } from '@/stores/ui'

export function useLoad<T>(fn: () => Promise<T>, sources: WatchSource[] = [], liveTypes: string[] = []) {
  const data = shallowRef<T | null>(null)
  const loading = ref(true)
  const error = ref('')
  let seq = 0, timer: any
  async function reload(silent = false) {
    const my = ++seq
    if (!silent) loading.value = true
    try { const r = await fn(); if (my === seq) { data.value = r; error.value = '' } }
    catch (e) { if (my === seq) error.value = errMsg(e) }
    finally { if (my === seq) loading.value = false }
  }
  const soft = () => { clearTimeout(timer); timer = setTimeout(() => reload(true), 1200) }
  onMounted(() => reload())
  if (sources.length) watch(sources, () => reload())
  liveTypes.forEach((t) => onLive(t, soft))
  return { data, loading, error, reload }
}

/** Davr + restoran parametrlari */
export function usePeriodParams() {
  const ui = useUiStore()
  return () => ({
    period: ui.period,
    from: ui.period === 'range' ? ui.from || undefined : undefined,
    to: ui.period === 'range' ? ui.to || undefined : undefined,
    restaurant_id: ui.restaurantId || undefined,
  })
}
