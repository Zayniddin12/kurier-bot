<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { get, post, patch, errMsg } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import { useRestaurantsStore } from '@/stores/restaurants'
import { useLoad } from '@/utils/useLoad'
import { agoSec, dmyhm } from '@/utils/format'
import PromptModal from '@/components/modals/PromptModal.vue'
import EditRestaurantModal from '@/components/modals/EditRestaurantModal.vue'
import IntegrationModal from '@/components/modals/IntegrationModal.vue'
import RestaurantMenuModal from '@/components/modals/RestaurantMenuModal.vue'

const route = useRoute(), router = useRouter(), ui = useUiStore(), auth = useAuthStore(), rs = useRestaurantsStore()
const id = computed(() => Number(route.params.id))
const { data: d, loading, error, reload } = useLoad<any>(() => get(`/restaurants/${id.value}`), [id], ['restaurant.updated', 'order.created', 'order.updated'])
const r = computed(() => d.value?.restaurant)
const modal = ref<'' | 'edit' | 'hours' | 'pause' | 'integ' | 'menu'>('')
const tags = computed(() => (r.value?.cuisine || '').split(',').map((x: string) => x.trim()).filter(Boolean))
const open = computed(() => r.value?.status !== 'paused')
const closesAt = computed(() => { const m = (r.value?.hours || '').split(/[–-]/); return m.length > 1 ? m[1].trim() : '' })

async function run(fn: () => Promise<any>, msg: string) {
  try { await fn(); ui.toast(msg); reload(true); rs.load() } catch (e) { ui.toast(errMsg(e), 'var(--red)') }
}
function toggle() { if (!auth.canManage) return; if (open.value) modal.value = 'pause'; else run(() => post(`/restaurants/${id.value}/resume`), 'Restoran faollashtirildi') }
const pause = (reason: string) => { modal.value = ''; run(() => post(`/restaurants/${id.value}/pause`, { reason }), "Restoran pauzaga qo'yildi") }
const saveHours = (v: string) => { modal.value = ''; run(() => patch(`/restaurants/${id.value}`, { hours: v }), 'Ish vaqti saqlandi') }
const soon = (t: string) => ui.toast(`${t} — bu bo'lim hali ulanmagan`, 'var(--side)')

const actions = computed(() => [
  { l: 'Tahrirlash', i: 'edit', f: () => (modal.value = 'edit') },
  { l: 'Ish vaqtlari', i: 'clock', f: () => (modal.value = 'hours') },
  { l: 'Integratsiya', i: 'monitor', f: () => (modal.value = 'integ') },
  { l: 'Badge', i: 'tag', f: () => soon('Badge') },
  { l: 'Barcha mahsulotlar', i: 'box', f: () => soon('Barcha mahsulotlar') },
  { l: 'Menyu metrikalari', i: 'chart', f: () => soon('Menyu metrikalari') },
  { l: 'Bannerlar', i: 'image', f: () => soon('Bannerlar') },
  { l: 'Menejerlar', i: 'user', f: () => soon('Menejerlar') },
  { l: 'Menyu', i: 'folder', f: () => (modal.value = 'menu') },
  { l: 'Hisobot', i: 'file', f: () => router.push({ path: '/orders', query: { r: id.value } }) },
  { l: 'Komissiya', i: 'dollar', f: () => ui.toast('Joriy komissiya: 0%', 'var(--side)') },
  { l: 'POS uchun barcha mahsulotlar', i: 'monitor', f: () => soon('POS mahsulotlari') },
  { l: "POS mahsulotlarini ko'rish", i: 'monitor', f: () => soon("POS mahsulotlarini ko'rish") },
  { l: 'Markirovka mahsulotlari', i: 'layers', f: () => soon('Markirovka mahsulotlari') },
  { l: "O'zgarishlar tarixi", i: 'history', f: () => soon("O'zgarishlar tarixi") },
  { l: "O'chirish", i: 'trash', f: () => soon("O'chirish"), muted: true },
])
</script>

<template>
  <div class="page rp">
    <nav class="bc"><RouterLink to="/"><Icon name="home" :size="15" /></RouterLink><Icon name="chevright" :size="13" /><RouterLink to="/restaurants">Restoranlar</RouterLink><Icon name="chevright" :size="13" /><b>{{ r?.name || '…' }}</b></nav>

    <ErrorBox v-if="error && !d" :message="error" @retry="reload()" />
    <template v-else-if="loading && !d"><Skeleton :h="190" /><Skeleton :h="90" /><Skeleton :h="300" /></template>
    <template v-else-if="r">
      <section class="box head">
        <div class="hrow">
          <span class="logo" :style="{ background: r.color }">{{ r.name.split(/\s+/).slice(0, 2).map((w: string) => w[0]).join('').toUpperCase() }}</span>
          <div class="hinfo">
            <div class="nm"><h2>{{ r.name }}</h2><span class="kind">Restoran</span></div>
            <div class="loc"><Icon name="pin" :size="14" />{{ r.district || '—' }}</div>
            <div class="tg"><span v-for="t in tags" :key="t">{{ t }}</span></div>
          </div>
          <div class="sw">
            <span class="swl">BUYURTMA QABUL QILISH</span>
            <button class="tgl" :class="{ on: open, ro: !auth.canManage }" @click="toggle"><i /><span>{{ open ? 'Ochiq' : 'Pauzada' }}</span></button>
          </div>
        </div>
        <div class="acts">
          <button v-for="a in actions" :key="a.l" class="ab" :class="{ muted: a.muted }" @click="a.f()"><Icon :name="a.i" :size="15" />{{ a.l }}</button>
        </div>
      </section>

      <section class="stats">
        <div class="st"><span class="ic a"><Icon name="orders" :size="20" /></span><div><b class="num">{{ r.today }}</b><small>Bugungi buyurtmalar · faol {{ r.active }}</small></div></div>
        <div class="st"><span class="ic b"><Icon name="dollar" :size="20" /></span><div><b class="num">0%</b><small>Joriy komissiya</small></div></div>
        <div class="st"><span class="ic c"><Icon name="user" :size="20" /></span><div><b class="num">{{ r.manager ? 1 : 0 }}</b><small>Menejerlar</small></div></div>
        <div class="st"><span class="ic d"><Icon name="monitor" :size="20" /></span><div><b>{{ r.pos_system || r.integration_type }}</b><small>POS integratsiyasi</small></div></div>
      </section>

      <div class="cols">
        <section class="card">
          <header><Icon name="file" :size="16" />Asosiy ma'lumotlar</header>
          <dl>
            <dt>ID</dt><dd>{{ r.id }}</dd>
            <dt>Nomi</dt><dd>{{ r.name }}</dd>
            <dt>Oshxona turi</dt><dd>{{ r.cuisine || '—' }}</dd>
            <dt>Integratsiya turi</dt><dd>{{ r.integration_type }}</dd>
            <dt>POS tizimi</dt><dd>{{ r.pos_system || '—' }}</dd>
            <dt>Tayyorlash vaqti</dt><dd>{{ r.prep_minutes }} daq</dd>
            <dt>Reyting</dt><dd>★ {{ r.rating }}</dd>
            <dt>Ulangan vaqti</dt><dd>{{ dmyhm(r.connected_at) }}</dd>
            <dt>Oxirgi sinxronlash</dt><dd>{{ agoSec(r.last_sync_at) }}</dd>
          </dl>
        </section>
        <div class="rcol">
          <section class="card">
            <header><Icon name="phone" :size="16" />Kontaktlar</header>
            <dl>
              <dt>Restoran manzili</dt><dd>{{ r.address || '—' }}</dd>
              <dt>Tuman</dt><dd>{{ r.district || '—' }}</dd>
              <dt>Boshqaruvchi</dt><dd>{{ r.manager || '—' }}</dd>
              <dt>Buyurtma qabul qiluvchi raqami</dt><dd><a v-if="r.phone" :href="`tel:${r.phone}`">{{ r.phone }}</a><template v-else>—</template></dd>
              <dt>Webhook URL</dt><dd class="brk">{{ r.webhook_url || '—' }}</dd>
              <dt>Vaqtinchalik yopiq</dt><dd><span v-if="!open" class="pl am">Pauzada{{ r.pause_reason ? ': ' + r.pause_reason : '' }}</span><span v-else class="pl gr">Yopiq emas</span></dd>
            </dl>
          </section>
          <section class="card">
            <header><Icon name="clock" :size="16" />Ish vaqtlari</header>
            <div class="hr"><b>Har kuni</b><span class="num">{{ r.hours }}</span></div>
            <div class="hs" :class="{ am: !open }"><Icon name="clock" :size="14" />{{ open ? (closesAt ? `${closesAt} gacha ochiq` : 'Ochiq') : 'Hozir buyurtma qabul qilmayapti' }}</div>
          </section>
        </div>
      </div>

      <EditRestaurantModal v-if="modal === 'edit'" :r="r" @close="modal = ''" @done="ui.toast('Saqlandi'); reload(true); rs.load()" />
      <IntegrationModal v-if="modal === 'integ'" :r="r" @close="modal = ''" @done="reload(true)" />
      <RestaurantMenuModal v-if="modal === 'menu'" :r="r" @close="modal = ''" />
      <PromptModal v-if="modal === 'pause'" title="Restoranni pauzaga qo'yish" sub="Pauza davomida yangi buyurtma qabul qilinmaydi" label="Sabab" ok="Pauza" @close="modal = ''" @submit="pause" />
      <PromptModal v-if="modal === 'hours'" title="Ish vaqtlari" label="Ish vaqti (masalan 09:00–22:00)" ok="Saqlash" :initial="r.hours" @close="modal = ''" @submit="saveHours" />
    </template>
  </div>
</template>

<style scoped>
.rp{gap:14px;max-width:1500px}
.bc{display:flex;align-items:center;gap:8px;font-size:13.5px;color:var(--faint)}.bc a{color:var(--link);display:inline-flex;align-items:center}.bc b{color:var(--ink);font-weight:600}
.box{background:var(--surface);border:1px solid var(--line);border-radius:12px}
.head{padding:22px 24px 20px}
.hrow{display:flex;gap:20px;align-items:flex-start}
.logo{width:80px;height:80px;border-radius:12px;color:#fff;font-size:26px;font-weight:800;display:flex;align-items:center;justify-content:center;flex:none}
.hinfo{flex:1;min-width:0;display:flex;flex-direction:column;gap:6px}
.nm{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.nm h2{font-size:23px;font-weight:700;line-height:1.2}
.kind{background:var(--violet-soft);color:var(--violet);font-size:12px;font-weight:600;border-radius:6px;padding:2px 10px}
.loc{display:flex;align-items:center;gap:5px;color:var(--muted);font-size:14px}
.tg{display:flex;gap:6px;flex-wrap:wrap}.tg span{background:var(--grey-soft);color:var(--muted);border-radius:6px;padding:3px 10px;font-size:12.5px}
.sw{display:flex;align-items:center;gap:14px;flex:none}
.swl{font-size:11px;font-weight:600;color:var(--faint);letter-spacing:.04em}
.tgl{display:inline-flex;align-items:center;gap:10px;height:40px;min-width:132px;padding:0 14px 0 8px;border-radius:10px;border:1px solid var(--line);background:var(--surface);font-weight:600;font-size:14px;color:var(--ink)}
.tgl i{width:36px;height:20px;border-radius:999px;background:var(--grey);position:relative;flex:none;transition:background .15s}
.tgl i::after{content:'';position:absolute;top:2px;left:2px;width:16px;height:16px;border-radius:50%;background:#fff;transition:transform .15s}
.tgl.on i{background:var(--primary)}.tgl.on i::after{transform:translateX(16px)}.tgl.ro{cursor:default}
.acts{display:flex;flex-wrap:wrap;gap:8px;margin-top:20px}
.ab{display:inline-flex;align-items:center;gap:7px;height:38px;padding:0 14px;border-radius:9px;border:1px solid var(--line);background:var(--surface);font-size:13.5px;font-weight:500;color:var(--ink)}
.ab:hover{background:var(--surface-2);border-color:var(--faint)}.ab.muted{color:var(--muted)}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
.st{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:18px 20px;display:flex;align-items:center;gap:14px;min-width:0}
.st b{display:block;font-size:24px;font-weight:700;line-height:1.15;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.st small{font-size:13px;color:var(--muted)}
.ic{width:44px;height:44px;border-radius:10px;display:flex;align-items:center;justify-content:center;flex:none}
.ic.a{background:var(--blue-soft);color:var(--blue)}.ic.b{background:var(--amber-soft);color:var(--amber)}.ic.c{background:var(--blue-soft);color:var(--blue)}.ic.d{background:var(--teal-soft);color:var(--teal)}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:14px;align-items:start}
.rcol{display:flex;flex-direction:column;gap:14px;min-width:0}
.card{background:var(--surface);border:1px solid var(--line);border-radius:12px;overflow:hidden;min-width:0}
.card header{display:flex;align-items:center;gap:9px;padding:14px 18px;background:var(--surface-2);border-bottom:1px solid var(--line);font-weight:600;font-size:14.5px}
.card header :deep(svg){color:var(--faint)}
dl{display:grid;grid-template-columns:minmax(120px,38%) 1fr;margin:0}
dt,dd{padding:13px 18px;margin:0;font-size:14px;border-bottom:1px solid var(--line-2)}
dt{color:var(--muted);font-weight:500}
dt:nth-of-type(even),dt:nth-of-type(even)+dd{background:var(--surface-2)}
dl>:nth-last-child(-n+2){border-bottom:0}
.brk{word-break:break-all}
.pl{display:inline-block;border-radius:999px;padding:2px 10px;font-size:12.5px;font-weight:600}.pl.gr{background:var(--primary-soft);color:var(--teal)}.pl.am{background:var(--amber-soft);color:var(--amber)}
.hr{display:flex;justify-content:space-between;margin:14px 18px 0;padding:12px 14px;background:var(--surface-2);border-radius:8px;font-size:14px}
.hs{display:flex;align-items:center;gap:7px;margin-top:14px;padding:12px 18px;background:var(--primary-soft);color:var(--teal);font-weight:600;font-size:13.5px}.hs.am{background:var(--amber-soft);color:var(--amber)}
@media (max-width:1100px){.stats{grid-template-columns:1fr 1fr}.cols{grid-template-columns:1fr}.hrow{flex-wrap:wrap}.sw{width:100%}}
@media (max-width:560px){.stats{grid-template-columns:1fr}.logo{width:56px;height:56px;font-size:20px}}
</style>
