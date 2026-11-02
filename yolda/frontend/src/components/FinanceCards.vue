<script setup lang="ts">
import { comma } from '@/utils/format'
defineProps<{ summary?: { income: number; expense: number; balance: number } | null }>()
</script>
<template>
  <div class="fin-cards">
    <div class="fin-card"><span class="fin-ic in"><Icon name="down" :size="24" /></span>
      <div><b class="in">{{ comma(summary?.income ?? 0) }}</b><small>Daromad</small></div></div>
    <div class="fin-card"><span class="fin-ic out"><Icon name="up" :size="24" /></span>
      <div><b class="out">{{ comma(summary?.expense ?? 0) }}</b><small>Xarajat</small></div></div>
    <div class="fin-card"><span class="fin-ic bal"><Icon name="card" :size="24" /></span>
      <div><b>{{ comma(summary?.balance ?? 0) }}</b><small>Balans</small></div></div>
  </div>
</template>
