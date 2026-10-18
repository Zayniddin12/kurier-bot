<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { get, post, errMsg } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import { useRestaurantsStore } from '@/stores/restaurants'
import { useDrawer } from '@/utils/drawer'
import { useLoad } from '@/utils/useLoad'
import { agoSec, dmy } from '@/utils/format'
import { REST_STATUS } from '@/constants/statuses'
import PromptModal from '@/components/modals/PromptModal.vue'
import NewRestaurantModal from '@/components/modals/NewRestaurantModal.vue'
const router = useRouter(), ui = useUiStore(), auth = useAuthStore(), rs = useRestaurantsStore(), drawer = useDrawer()
const q = ref(''), st = ref('all')
const { data, loading, error, reload } = useLoad<any>(() => get('/restaurants', { q: q.value || undefined, status: st.value }), [q, st], ['restaurant.updated', 'order.created', 'order.updated'])
const c = computed(() => data.value?.counts || { all: 0, open: 0, paused: 0 })
const pauseFor = ref<number | null>(null), adding = ref(false)
async function pause(reason: string) {
  const id = pauseFor.value!; pauseFor.value = null
  try { await post(`/restaurants/${id}/pause`, { reason }); ui.toast('Restoran pauzaga qo\'yildi'); reload(true); rs.load() } catch (e) { ui.toast(errMsg(e), 'var(--red)') }
}
async function resume(id: number) { try { await post(`/restaurants/${id}/resume`); ui.toast('Restoran faollashtirildi'); reload(true); rs.load() } catch (e) { ui.toast(errMsg(e), 'var(--red)') } }
function onMap(id: number) { ui.restaurantId = id; router.push({ path: '/map', query: { r: id } }) }
</script>

<template>
  <div class="page">
    <div class="row" style="flex-wrap:wrap">
      <SearchInput v-model="q" placeholder="Nomi, tuman yoki oshxona turi" style="width:280px;max-width:100%" />
      <Seg v-model="st" :options="[{ value: 'all', label: `Hammasi ${c.all}` }, { value: 'open', label: `Qabul qilmoqda ${c.open}` }, { value: 'paused', label: `Pauzada ${c.paused}` }]" />
      <span class="sp" /><Btn v-if="auth.canManage" variant="primary" icon="plus" @click="adding = true">Restoran ulash</Btn>
    </div>
    <ErrorBox v-if="error && !data" :message="error" @retry="reload()" />
    <div v-else-if="loading && !data" class="grid"><Skeleton v-for="i in 6" :key="i" :h="220" /></div>
    <div v-else-if="data?.items.length" class="grid">
      <article v-for="r in data.items" :key="r.id" class="card" :class="{ sel: ui.restaurantId === r.id }" @click="drawer.open('restaurant', r.id)">
        <div class="row" style="gap:12px"><RestLogo lg :name="r.name" :color="r.color" /><div><b style="font-size:16px">{{ r.name }}</b><div class="sub">{{ r.cuisine }} · {{ r.district }}</div></div></div>
        <div class="row" style="flex-wrap:wrap;gap:6px"><Pill :tone="REST_STATUS[r.status].tone">{{ REST_STATUS[r.status].label }}</Pill><Tag>{{ r.integration_type }}<template v-if="r.pos_system"> · {{ r.pos_system }}</template></Tag><Tag>{{ r.hours }}</Tag></div>
        <div class="stats">
          <div><b class="num">{{ r.today }}</b><span>Bugun</span></div><div><b class="num">{{ r.active }}</b><span>Faol</span></div>
          <div><b class="num">{{ r.prep_minutes }} daq</b><span>Tayyorlash</span></div><div><b class="num">★ {{ r.rating }}</b><span>Reyting</span></div>
        </div>
        <div class="sub row" style="gap:6px"><Icon name="link" :size="14" />Oxirgi sinxronlash {{ agoSec(r.last_sync_at) }} · ulangan {{ dmy(r.connected_at) }}</div>
        <div class="row" style="gap:6px" @click.stop>
          <Btn variant="dark" @click="router.push({ path: '/orders', query: { r: r.id } })">Buyurtmalari</Btn><Btn @click="onMap(r.id)">Xaritada</Btn>
          <template v-if="auth.canManage"><Btn v-if="r.status === 'paused'" variant="primary" @click="resume(r.id)">Faollashtirish</Btn><Btn v-else @click="pauseFor = r.id">Pauza</Btn></template>
        </div>
      </article>
    </div>
    <Empty v-else title="Restoran topilmadi" text="Qidiruvni o'zgartiring" />
    <PromptModal v-if="pauseFor" title="Restoranni pauzaga qo'yish" label="Sabab" ok="Pauza" @close="pauseFor = null" @submit="pause" />
    <NewRestaurantModal v-if="adding" @close="adding = false" @done="reload(true); rs.load()" />
  </div>
</template>

<style scoped>
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:16px;display:flex;flex-direction:column;gap:12px;cursor:pointer}
.card.sel{border-color:var(--brand)}
.stats{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid var(--line-2);border-bottom:1px solid var(--line-2);padding:10px 0;text-align:center}
.stats b{display:block;font-size:14px}.stats span{font-size:11.5px;color:var(--muted)}
</style>
