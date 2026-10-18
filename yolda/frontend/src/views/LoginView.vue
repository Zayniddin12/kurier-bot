<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { errMsg } from '@/api/client'
const email = ref(''), password = ref(''), err = ref(''), busy = ref(false)
const auth = useAuthStore(), router = useRouter()
async function submit() {
  err.value = ''; busy.value = true
  try { await auth.login(email.value, password.value); router.replace('/') }
  catch (e) { err.value = errMsg(e) } finally { busy.value = false }
}
</script>
<template>
  <div class="wrap">
    <form class="card" @submit.prevent="submit">
      <div class="brand"><span class="logo"><Icon name="bike" :size="22" /></span><div><b>Yo'lda</b><small>Operator paneli</small></div></div>
      <div class="field"><label>Email</label><input v-model="email" class="inp lg" type="email" autocomplete="username" required /></div>
      <div class="field"><label>Parol</label><input v-model="password" class="inp lg" type="password" autocomplete="current-password" required /></div>
      <div v-if="err" class="err">{{ err }}</div>
      <Btn variant="primary" type="submit" :disabled="busy" style="height:40px">Kirish</Btn>
    </form>
  </div>
</template>
<style scoped>
.wrap{min-height:100%;display:flex;align-items:center;justify-content:center;padding:16px}
.card{width:380px;max-width:100%;background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:28px;display:flex;flex-direction:column;gap:14px;box-shadow:var(--shadow)}
.brand{display:flex;gap:10px;align-items:center;margin-bottom:6px}.brand b{font-size:21px;font-weight:800;display:block}.brand small{color:var(--muted);font-size:12px}
.logo{width:38px;height:38px;border-radius:11px;background:var(--brand);color:#16201A;display:flex;align-items:center;justify-content:center}
.err{color:var(--red);font-size:12px}
</style>
