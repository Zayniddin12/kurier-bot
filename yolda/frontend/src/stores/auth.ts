import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { get, post } from '@/api/client'

export interface User { id: number; email: string; full_name: string; role: 'platform_admin' | 'operator' | 'restaurant_staff'; restaurant_id: number | null; role_label?: string }

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('yolda-token') || '')
  const user = ref<User | null>(null)
  const isStaff = computed(() => user.value?.role === 'restaurant_staff')
  const canManage = computed(() => !!user.value && user.value.role !== 'restaurant_staff')
  const roleLabel = computed(() => (user.value?.role === 'platform_admin' ? 'Administrator' : user.value?.role === 'operator' ? 'Smena operatori' : 'Restoran xodimi'))

  async function login(email: string, password: string) {
    const r = await post<{ access_token: string; user: User }>('/auth/login', { email, password })
    token.value = r.access_token
    localStorage.setItem('yolda-token', r.access_token)
    user.value = r.user
  }
  async function fetchMe() {
    user.value = await get<User>('/auth/me')
  }
  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('yolda-token')
  }
  return { token, user, isStaff, canManage, roleLabel, login, fetchMe, logout }
})
