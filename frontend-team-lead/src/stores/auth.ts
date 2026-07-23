import { acceptHMRUpdate, defineStore } from 'pinia'
import { computed, shallowRef } from 'vue'

import { api, TOKEN_KEY } from '@/api/client'
import type { User } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const token = shallowRef(localStorage.getItem(TOKEN_KEY))
  const user = shallowRef<User | null>(null)
  const isAuthenticated = computed(() => Boolean(token.value))
  const canOperate = computed(() => user.value?.role === 'admin' || user.value?.role === 'operator')

  async function login(username: string, password: string): Promise<void> {
    const form = new URLSearchParams({ username, password })
    const response = await api.post('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    token.value = response.data.access_token
    localStorage.setItem(TOKEN_KEY, token.value ?? '')
    await loadUser()
  }

  async function register(username: string, password: string, passwordConfirm: string): Promise<void> {
    const response = await api.post<{ access_token: string; user: User }>('/auth/register', {
      username,
      password,
      password_confirm: passwordConfirm,
    })
    token.value = response.data.access_token
    user.value = response.data.user
    localStorage.setItem(TOKEN_KEY, token.value)
  }

  async function loadUser(): Promise<void> {
    if (!token.value) return
    try {
      user.value = (await api.get<User>('/auth/me')).data
    } catch {
      logout()
    }
  }

  function logout(): void {
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
  }

  function replaceUser(nextUser: User): void {
    user.value = nextUser
  }

  return { token, user, isAuthenticated, canOperate, login, register, loadUser, replaceUser, logout }
})

if (import.meta.hot) import.meta.hot.accept(acceptHMRUpdate(useAuthStore, import.meta.hot))
