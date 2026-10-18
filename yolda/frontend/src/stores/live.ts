import { defineStore } from 'pinia'
import { ref } from 'vue'
import { onUnmounted } from 'vue'

type Handler = (data: any) => void

const handlers = new Map<string, Set<Handler>>()

/** Sahifalar eventlarga shu orqali obuna bo'ladi (unmount'da avtomatik uziladi). */
export function onLive(type: string, fn: Handler) {
  if (!handlers.has(type)) handlers.set(type, new Set())
  handlers.get(type)!.add(fn)
  onUnmounted(() => handlers.get(type)?.delete(fn))
}

export const useLiveStore = defineStore('live', () => {
  const connected = ref(false)
  let ws: WebSocket | null = null
  let attempt = 0
  let stopped = false
  let timer: any
  const delays = [1000, 2000, 5000, 10000]

  function connect() {
    stopped = false
    const token = localStorage.getItem('yolda-token')
    if (!token) return
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    ws = new WebSocket(`${proto}://${location.host}/ws?token=${encodeURIComponent(token)}`)
    ws.onopen = () => { connected.value = true; attempt = 0 }
    ws.onmessage = (m) => {
      try {
        const { type, data } = JSON.parse(m.data)
        handlers.get(type)?.forEach((h) => h(data))
        handlers.get('*')?.forEach((h) => h({ type, data }))
      } catch { /* ignore */ }
    }
    ws.onclose = () => {
      connected.value = false
      if (stopped) return
      timer = setTimeout(connect, delays[Math.min(attempt++, delays.length - 1)])
    }
    ws.onerror = () => ws?.close()
  }
  function disconnect() { stopped = true; clearTimeout(timer); ws?.close(); connected.value = false }
  return { connected, connect, disconnect }
})
