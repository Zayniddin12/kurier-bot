import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

/** Drawer holati URL query'da: ?drawer=order:118452 */
export function useDrawer() {
  const route = useRoute()
  const router = useRouter()
  const current = computed(() => {
    const d = route.query.drawer as string | undefined
    if (!d) return null
    const [kind, id] = d.split(':')
    return { kind: kind as 'order' | 'courier' | 'restaurant', id: Number(id) }
  })
  const open = (kind: 'order' | 'courier' | 'restaurant', id: number) =>
    router.push({ query: { ...route.query, drawer: `${kind}:${id}` } })
  const close = () => {
    const q = { ...route.query }
    delete q.drawer
    router.push({ query: q })
  }
  return { current, open, close }
}
