<script setup lang="ts">
import logo from "@/assets/logo.png"
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
      <div class="brand"><span class="logo"><img :src="logo" alt="Tez-yetkaz" /></span><small>Operator paneli</small></div>
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
.brand{display:flex;flex-direction:column;gap:8px;align-items:center;margin-bottom:6px}.brand small{color:var(--muted);font-size:12px}
.logo{background:#12292F;border-radius:12px;padding:12px 22px;display:flex;align-items:center;justify-content:center}.logo img{height:26px;width:auto;display:block}
.err{color:var(--red);font-size:12px}
</style>
