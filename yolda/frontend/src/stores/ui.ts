import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type Period = 'today' | 'yesterday' | 'week' | 'month' | 'range'
export interface Toast { id: number; text: string; color: string }

const safeGet = (k: string) => { try { return localStorage.getItem(k) } catch { return null } }
const safeSet = (k: string, v: string) => { try { localStorage.setItem(k, v) } catch { /* ignore */ } }

export const useUiStore = defineStore('ui', () => {
  const theme = ref<'light' | 'dark'>((safeGet('yolda-theme') as any) || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'))
  const restaurantId = ref<number | null>(null)
  const sidebarOpen = ref(false)
  const toasts = ref<Toast[]>([])
  const sound = ref(safeGet('yolda-sound') !== '0')
  const period = ref<Period>('today')
  const from = ref('')
  const to = ref('')
  const mapFocus = ref<{ courierId?: number; filter?: string } | null>(null)
  let tid = 0

  const apply = () => document.documentElement.setAttribute('data-theme', theme.value)
  apply()
  watch(theme, (v) => { safeSet('yolda-theme', v); apply() })
  watch(sound, (v) => safeSet('yolda-sound', v ? '1' : '0'))

  const toggleTheme = () => { theme.value = theme.value === 'dark' ? 'light' : 'dark' }
  function toast(text: string, color = 'var(--teal)') {
    const id = ++tid
    toasts.value.push({ id, text, color })
    setTimeout(() => { toasts.value = toasts.value.filter((t) => t.id !== id) }, 5000)
  }
  function beep() {
    if (!sound.value) return
    try {
      const ac = new AudioContext(); const o = ac.createOscillator(); const g = ac.createGain()
      o.frequency.value = 880; g.gain.value = 0.05; o.connect(g); g.connect(ac.destination)
      o.start(); o.stop(ac.currentTime + 0.12)
    } catch { /* ignore */ }
  }
  return { theme, restaurantId, sidebarOpen, toasts, sound, period, from, to, mapFocus, toggleTheme, toast, beep }
})
