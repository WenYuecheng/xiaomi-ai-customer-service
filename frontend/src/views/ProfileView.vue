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
      <header class="page-title"><span>MY XIAOMI AI UNIVERSE ✦</span><h2>AI 数字空间</h2><p>你的每一次咨询、选择与反馈，都在这里组成独一无二的探索轨迹。</p></header>
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

<style scoped>.profile-page{display:grid;gap:0}.page-title{margin-bottom:24px}.page-title span{background:linear-gradient(90deg,#7658df,#d35dcc,#ff6900);background-clip:text;color:transparent;font-family:var(--font-mono);font-size:10px;letter-spacing:.18em}.page-title h2{font-size:clamp(34px,5vw,52px);letter-spacing:-.055em;margin:7px 0}.page-title p{color:#81778e;margin:0}.profile-grid{display:grid;gap:17px;grid-template-columns:1fr 1fr;margin-bottom:17px}.profile-loading{display:grid;min-height:440px;place-content:center;text-align:center}.profile-loading i{animation:pulse-orbit 1.2s infinite;border:2px solid #d8cef0;border-radius:50%;border-top-color:#7658df;height:38px;margin:auto;width:38px}.profile-loading p{color:#8b8197;font-size:12px}@keyframes pulse-orbit{to{transform:rotate(360deg)}}@media(max-width:800px){.profile-grid{grid-template-columns:1fr}}@media(prefers-reduced-motion:reduce){.profile-loading i{animation:none}}</style>
