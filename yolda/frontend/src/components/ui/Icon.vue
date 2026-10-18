<script setup lang="ts">
import { computed } from 'vue'
import * as L from 'lucide-vue-next'
const props = withDefaults(defineProps<{ name: string; size?: number }>(), { size: 18 })
const map: Record<string, any> = {
  gauge: L.LayoutDashboard, map: L.Map, bike: L.Bike, orders: L.ClipboardList, store: L.Store, chart: L.ChartNoAxesColumn,
  bell: L.Bell, calendar: L.CalendarDays, chevron: L.ChevronDown, search: L.Search, x: L.X, moon: L.Moon, sun: L.Sun,
  menu: L.Menu, home: L.House, pin: L.MapPin, dollar: L.CircleDollarSign, download: L.Download, phone: L.Phone,
  msg: L.MessageSquare, plus: L.Plus, minus: L.Minus, scan: L.Scan, link: L.Link, card: L.CreditCard, user: L.User,
  logout: L.LogOut, up: L.ArrowUp, down: L.ArrowDown, updown: L.ArrowUpDown, check: L.Check, copy: L.Copy,
  alert: L.TriangleAlert, clock: L.Clock, utensils: L.Utensils, star: L.Star, building: L.Building2, box: L.Package,
  chevleft: L.ChevronLeft, chevright: L.ChevronRight, key: L.KeyRound, volume: L.Volume2, mute: L.VolumeOff, refresh: L.RefreshCw,
}
const C = computed(() => map[props.name] || L.Circle)
</script>
<template><component :is="C" :size="size" :stroke-width="1.8" /></template>
