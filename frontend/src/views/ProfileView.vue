<script setup lang="ts">
import { computed, onMounted, shallowRef } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import ActivityTimeline from '@/components/account/ActivityTimeline.vue'
import ActivityTrend from '@/components/account/ActivityTrend.vue'
import ChangePasswordDialog from '@/components/account/ChangePasswordDialog.vue'
import InterestGalaxy from '@/components/account/InterestGalaxy.vue'
import ProfileHero from '@/components/account/ProfileHero.vue'
import ProfileSettingsDrawer from '@/components/account/ProfileSettingsDrawer.vue'
import ProfileStats from '@/components/account/ProfileStats.vue'
import { useAccountDashboard } from '@/composables/useAccountDashboard'
import { useAuthStore } from '@/stores/auth'
import type { AccountActivity } from '@/types'

const auth = useAuthStore()
const router = useRouter()
const account = useAccountDashboard()
const settingsOpen = shallowRef(false)
const passwordOpen = shallowRef(false)
const actionBusy = shallowRef(false)
const actionError = shallowRef('')
const hasMore = computed(() => Boolean(account.nextCursor.value))

function openActivity(activity: AccountActivity): void {
  if (activity.type === 'advisor') {
    void router.push({ name: 'advisor', query: { session_id: activity.resource_id } })
  } else {
    void router.push({ name: 'chat', query: { conversation_id: activity.resource_id } })
  }
}

async function saveProfile(payload: Parameters<typeof account.saveProfile>[0]): Promise<void> {
  actionBusy.value = true
  actionError.value = ''
  try {
    await account.saveProfile(payload)
    settingsOpen.value = false
    ElMessage.success('数字身份已更新')
  } catch (reason) {
    actionError.value = reason instanceof Error ? reason.message : '资料保存失败'
  } finally { actionBusy.value = false }
}

async function changePassword(payload: Parameters<typeof account.changePassword>[0]): Promise<void> {
  actionBusy.value = true
  actionError.value = ''
  try {
    await account.changePassword(payload)
    ElMessage.success('密码已更新，请重新登录')
    await router.replace({ name: 'login' })
  } catch (reason) {
    actionError.value = reason instanceof Error ? reason.message : '密码更新失败'
  } finally { actionBusy.value = false }
}

onMounted(account.load)
</script>

<template>
  <section class="profile-page">
      <header class="page-title"><div><span>ACCOUNT & SERVICE HISTORY</span><h2>个人中心</h2><p>管理身份与安全设置，查看咨询、选购和反馈形成的服务记录。</p></div><aside><b>数据说明</b><span>画像只基于本系统内的咨询行为生成，可随时清除。</span></aside></header>
      <el-alert v-if="account.error.value" :title="account.error.value" type="error" show-icon />
      <div v-if="account.loading.value" class="profile-loading"><i /><p>正在读取你的数字星系…</p></div>
      <template v-else-if="account.dashboard.value && auth.user">
        <ProfileHero :user="auth.user" :dashboard="account.dashboard.value" @edit="settingsOpen = true; actionError = ''" @password="passwordOpen = true; actionError = ''" />
        <ProfileStats :stats="account.dashboard.value.stats" />
        <div class="profile-grid"><InterestGalaxy :products="account.dashboard.value.interests.product_preferences" :intents="account.dashboard.value.interests.intent_distribution" /><ActivityTrend :points="account.dashboard.value.trend" /></div>
        <ActivityTimeline :items="account.activities.value" :has-more="hasMore" :loading-more="account.loadingMore.value" @select="openActivity" @load-more="account.loadAllActivities" />
        <ProfileSettingsDrawer :open="settingsOpen" :user="auth.user" :busy="actionBusy" :error="actionError" @close="settingsOpen = false" @save="saveProfile" />
        <ChangePasswordDialog :open="passwordOpen" :busy="actionBusy" :error="actionError" @close="passwordOpen = false" @change-password="changePassword" />
      </template>
  </section>
</template>

<style scoped>.profile-page{display:grid;gap:0}.page-title{align-items:flex-end;display:flex;justify-content:space-between;margin-bottom:24px}.page-title>div>span{color:var(--mi-orange);font-family:var(--font-mono);font-size:10px;font-weight:700;letter-spacing:.18em}.page-title h2{font-size:clamp(36px,5vw,54px);letter-spacing:-.055em;margin:7px 0}.page-title p{color:var(--ink-muted);margin:0}.page-title aside{background:#fff;border:1px solid var(--line);border-radius:13px;display:grid;gap:4px;max-width:300px;padding:12px 14px}.page-title aside b{font-size:11px}.page-title aside span{color:var(--ink-muted);font-size:9px;line-height:1.5}.profile-grid{display:grid;gap:14px;grid-template-columns:1fr 1fr;margin-bottom:14px}.profile-loading{display:grid;min-height:440px;place-content:center;text-align:center}.profile-loading i{animation:pulse-orbit 1.2s infinite;border:2px solid #e2ddd7;border-radius:50%;border-top-color:var(--mi-orange);height:38px;margin:auto;width:38px}.profile-loading p{color:var(--ink-muted);font-size:12px}@keyframes pulse-orbit{to{transform:rotate(360deg)}}@media(max-width:800px){.page-title{align-items:flex-start;flex-direction:column;gap:14px}.page-title aside{max-width:none}.profile-grid{grid-template-columns:1fr}}@media(prefers-reduced-motion:reduce){.profile-loading i{animation:none}}</style>
