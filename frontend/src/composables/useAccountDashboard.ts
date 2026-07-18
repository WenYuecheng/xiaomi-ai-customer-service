import { readonly, ref, shallowRef } from 'vue'

import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { AccountActivity, AccountActivityPage, AccountDashboard, AvatarKey, User } from '@/types'

export function useAccountDashboard() {
  const auth = useAuthStore()
  const dashboard = shallowRef<AccountDashboard>()
  const activities = ref<AccountActivity[]>([])
  const nextCursor = shallowRef<string | null>(null)
  const loading = shallowRef(false)
  const loadingMore = shallowRef(false)
  const error = shallowRef('')

  async function load(): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      const result = await api.get<AccountDashboard>('/account/dashboard')
      dashboard.value = result.data
      activities.value = result.data.recent_activities
      nextCursor.value = result.data.recent_activities.length >= 5 ? 'initial' : null
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : '个人主页加载失败'
    } finally {
      loading.value = false
    }
  }

  async function loadAllActivities(): Promise<void> {
    if (loadingMore.value) return
    loadingMore.value = true
    try {
      const params = nextCursor.value && nextCursor.value !== 'initial'
        ? { cursor: nextCursor.value, limit: 20 }
        : { limit: 20 }
      const result = await api.get<AccountActivityPage>('/account/activities', { params })
      activities.value = nextCursor.value === 'initial'
        ? result.data.items
        : [...activities.value, ...result.data.items]
      nextCursor.value = result.data.next_cursor
    } finally {
      loadingMore.value = false
    }
  }

  async function saveProfile(payload: { display_name: string; avatar_key: AvatarKey }): Promise<void> {
    const result = await api.patch<User>('/account/profile', payload)
    auth.replaceUser(result.data)
  }

  async function changePassword(payload: {
    current_password: string
    new_password: string
    new_password_confirm: string
  }): Promise<void> {
    await api.post('/account/change-password', payload)
    auth.logout()
  }

  return {
    dashboard: readonly(dashboard), activities: readonly(activities), nextCursor: readonly(nextCursor),
    loading: readonly(loading), loadingMore: readonly(loadingMore), error: readonly(error),
    load, loadAllActivities, saveProfile, changePassword,
  }
}
