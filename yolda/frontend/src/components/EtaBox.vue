<script setup lang="ts">
import { hm } from '@/utils/format'
defineProps<{ eta: any; tone?: string }>()
</script>
<template>
  <div class="eta">
    <div>
      <small>{{ eta.stage === 'pickup' ? 'Restoranga va mijozga yetib borishiga' : 'Mijozga yetib borishiga' }}</small>
      <b class="num" :class="{ late: eta.late }">{{ eta.eta_min }} daq</b>
    </div>
    <div class="r">
      <span>{{ eta.stage === 'pickup' ? 'Qolgan masofa' : 'Mijozgacha' }}: {{ eta.remaining_km.toFixed(1) }} km</span>
      <span>Jami: {{ eta.total_min }} daq<template v-if="eta.delay_min"> (+{{ eta.delay_min }} kechikish)</template></span>
      <span>Taxminan {{ hm(eta.arrive_at) }}</span>
    </div>
  </div>
  <div class="pb"><i :style="{ width: eta.bar_percent + '%', background: tone || (eta.stage === 'pickup' ? 'var(--blue)' : 'var(--teal)') }" /></div>
</template>
<style scoped>
.eta{display:flex;justify-content:space-between;gap:12px;background:var(--surface-2);border:1px solid var(--line-2);border-radius:12px;padding:12px 14px}
small{font-size:12px;color:var(--muted);display:block}b{font-size:34px;font-weight:800;line-height:1.1}b.late{color:var(--red)}
.r{display:flex;flex-direction:column;font-size:12px;color:var(--muted);text-align:right;justify-content:center;gap:2px}
.pb{height:6px;background:var(--line);border-radius:3px;margin:10px 0;overflow:hidden}.pb i{display:block;height:100%;border-radius:3px;transition:width .6s}
</style>
