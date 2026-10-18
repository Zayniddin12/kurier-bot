<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRestaurantsStore } from '@/stores/restaurants'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
const rs = useRestaurantsStore(), ui = useUiStore(), auth = useAuthStore()
const open = ref(false), q = ref('')
const cur = computed(() => rs.items.find((r) => r.id === ui.restaurantId))
const list = computed(() => rs.items.filter((r) => (r.name + r.district).toLowerCase().includes(q.value.toLowerCase())))
const todayOf = (r: any) => r.today_orders ?? r.today ?? 0
const total = computed(() => rs.items.reduce((s, r) => s + todayOf(r), 0))
function pick(id: number | null) { ui.restaurantId = id; open.value = false }
</script>
<template>
  <div class="rp">
    <button class="btn" :disabled="auth.isStaff" @click="open = !open">
      <RestLogo :all="!cur" :name="cur?.name" :color="cur?.color" />
      <span class="t"><small>Restoran</small><b>{{ cur?.name || 'Barcha restoranlar' }}</b></span>
      <Icon v-if="!auth.isStaff" name="chevron" :size="16" />
    </button>
    <div v-if="open" class="back" @click="open = false" />
    <div v-if="open" class="pop">
      <SearchInput v-model="q" placeholder="Restoran qidirish" />
      <div class="list">
        <button v-if="!q" class="it" :class="{ on: !ui.restaurantId }" @click="pick(null)">
          <RestLogo all /><span class="n"><b>Barcha restoranlar</b><small>{{ rs.items.length }} ta ulangan</small></span><span class="c num">{{ total }}</span>
        </button>
        <button v-for="r in list" :key="r.id" class="it" :class="{ on: ui.restaurantId === r.id }" @click="pick(r.id)">
          <RestLogo :name="r.name" :color="r.color" />
          <span class="n"><b>{{ r.name }}</b><small>{{ r.district }}{{ r.status === 'paused' ? ' · pauzada' : '' }}</small></span><span class="c num">{{ todayOf(r) }}</span>
        </button>
      </div>
    </div>
  </div>
</template>
<style scoped>
.rp{position:relative}
.btn{height:42px;min-width:230px;background:var(--surface-2);border:1px solid var(--line);border-radius:10px;padding:0 10px;display:flex;align-items:center;gap:9px;text-align:left}
.btn:disabled{cursor:default}
.t{display:flex;flex-direction:column;line-height:1.15;flex:1;min-width:0}.t small{font-size:11px;color:var(--muted)}.t b{font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.back{position:fixed;inset:0;z-index:40}
.pop{position:absolute;top:48px;right:0;width:320px;background:var(--surface);border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow);padding:10px;z-index:50}
.list{max-height:360px;overflow:auto;margin-top:8px;display:flex;flex-direction:column;gap:2px}
.it{display:flex;align-items:center;gap:10px;border:0;background:transparent;padding:7px;border-radius:9px;text-align:left}
.it:hover,.it.on{background:var(--surface-2)}
.n{flex:1;display:flex;flex-direction:column;line-height:1.2;min-width:0}.n b{font-size:13px}.n small{font-size:12px;color:var(--muted)}.c{font-size:13px;font-weight:600}
@media (max-width:520px){.btn{min-width:0}.t{display:none}.btn :deep(svg){display:none}.pop{right:-40px;width:min(320px,92vw)}}
@media (max-width:860px){.btn{min-width:0}}
</style>
