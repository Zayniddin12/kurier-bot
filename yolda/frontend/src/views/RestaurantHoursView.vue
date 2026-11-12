<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { get, patch, errMsg } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { useRestaurantsStore } from '@/stores/restaurants'
import { useLoad } from '@/utils/useLoad'
import { DAYS, parseHours } from '@/utils/schedule'

const route = useRoute(), router = useRouter(), ui = useUiStore(), rs = useRestaurantsStore()
const id = computed(() => Number(route.params.id))
const { data: d, loading, error, reload } = useLoad<any>(() => get(`/restaurants/${id.value}`), [id])
const r = computed(() => d.value?.restaurant)

// grid[day][slot] — 7 kun × 48 yacheyka (30 daqiqa)
const grid = ref<boolean[][]>(Array.from({ length: 7 }, () => Array(48).fill(false)))
watch(r, (v) => {
  if (!v) return
  const src: string[] = v.schedule || parseHours(v.hours)
  grid.value = src.map(s => Array.from(s, c => c === '1'))
}, { immediate: true })

const mode = ref<'draw' | 'erase'>('draw')
const busy = ref(false)
let dragging = false
function paint(day: number, slot: number) { grid.value[day][slot] = mode.value === 'draw' }
function down(day: number, slot: number) { dragging = true; paint(day, slot) }
function over(day: number, slot: number) { if (dragging) paint(day, slot) }
function up() { dragging = false }
window.addEventListener('mouseup', up)
onBeforeUnmount(() => window.removeEventListener('mouseup', up))

const hm = (m: number) => `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`
const label = (i: number) => `${hm(i * 30)}–${hm(i * 30 + 29)}`

async function save() {
  busy.value = true
  try {
    await patch(`/restaurants/${id.value}`, { schedule: grid.value.map(day => day.map(x => (x ? '1' : '0')).join('')) })
    ui.toast('Ish vaqti saqlandi'); rs.load(); router.push(`/restaurants/${id.value}`)
  } catch (e) { ui.toast(errMsg(e), 'var(--red)') } finally { busy.value = false }
}
</script>

<template>
  <div class="page hp">
    <nav class="bc"><RouterLink to="/"><Icon name="home" :size="15" /></RouterLink><Icon name="chevright" :size="13" /><RouterLink to="/restaurants">Restoranlar</RouterLink><Icon name="chevright" :size="13" /><RouterLink :to="`/restaurants/${id}`">{{ r?.name || '…' }}</RouterLink><Icon name="chevright" :size="13" /><b>Ish vaqtlari</b></nav>
    <ErrorBox v-if="error && !d" :message="error" @retry="reload()" />
    <Skeleton v-else-if="loading && !d" :h="500" />
    <section v-else class="card">
      <h3>Ish kunlari</h3>
      <p class="sub">Restoran ishlaydigan vaqt oraliqlarini belgilang. Diapazonni tanlash uchun bosib torting.</p>
      <div class="bar">
        <label class="rd" :class="{ on: mode === 'draw' }"><input v-model="mode" type="radio" value="draw" />Chizish</label>
        <label class="rd" :class="{ on: mode === 'erase' }"><input v-model="mode" type="radio" value="erase" />O'chirish</label>
        <Btn variant="primary" :disabled="busy" style="margin-left:auto" @click="save">Saqlash</Btn>
      </div>
      <div class="gw">
        <table class="g" @dragstart.prevent>
          <thead><tr><th /><th v-for="n in DAYS" :key="n">{{ n }}</th></tr></thead>
          <tbody>
            <tr v-for="(_, i) in 48" :key="i">
              <th class="t">{{ label(i) }}</th>
              <td v-for="dd in 7" :key="dd" :class="{ on: grid[dd - 1][i] }" @mousedown.prevent="down(dd - 1, i)" @mouseenter="over(dd - 1, i)" />
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.hp{gap:14px;max-width:1500px}
.bc{display:flex;align-items:center;gap:8px;font-size:13.5px;color:var(--faint)}.bc a{color:var(--link);display:inline-flex;align-items:center}.bc b{color:var(--ink);font-weight:600}
.card{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:24px}
h3{font-size:17px;font-weight:700;margin:0 0 6px}.sub{color:var(--muted);font-size:14px;margin:0 0 18px}
.bar{display:flex;align-items:center;gap:10px;margin-bottom:16px}
.rd{display:inline-flex;align-items:center;gap:8px;height:38px;padding:0 14px;border:1px solid var(--line);border-radius:9px;font-weight:500;font-size:14px;cursor:pointer;user-select:none}
.rd.on{border-color:var(--primary);background:var(--primary-soft)}.rd input{accent-color:var(--primary)}
.gw{border:2px solid var(--line);border-radius:6px;overflow:hidden;user-select:none}
.g{width:100%;border-collapse:collapse;table-layout:fixed}
.g th{background:var(--surface-2);font-size:12px;font-weight:600;letter-spacing:.05em;color:var(--muted);height:36px;border:2px solid var(--line)}
.g th.t{width:130px;text-align:right;padding-right:16px;font-weight:500;letter-spacing:0;font-size:13px}
.g td{height:36px;border:2px solid var(--line);cursor:pointer;background:var(--surface)}
.g td:hover{background:var(--primary-soft)}
.g td.on{background:var(--primary);border-color:var(--primary)}
</style>
