<script setup lang="ts">
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

function logout(): void {
  auth.logout()
  void router.push({ name: 'login' })
}
</script>

<template>
  <div class="shell">
    <header class="shell__header">
      <RouterLink class="brand" to="/chat"><span>MI</span> 小爱客服工作台</RouterLink>
      <nav class="nav" aria-label="主导航">
        <RouterLink to="/chat">可信问答</RouterLink>
        <RouterLink v-if="auth.canOperate" to="/knowledge">知识库</RouterLink>
        <RouterLink v-if="auth.canOperate" to="/operations">运营洞察</RouterLink>
      </nav>
      <button class="account" type="button" @click="logout">{{ auth.user?.username }} · 退出</button>
    </header>
    <main class="shell__content"><slot /></main>
  </div>
</template>

<style scoped>
.shell { min-height: 100vh; }
.shell__header { align-items: center; background: rgba(247,248,250,.92); border-bottom: 1px solid var(--line); display: grid; grid-template-columns: 1fr auto 1fr; height: 68px; padding: 0 32px; position: sticky; top: 0; z-index: 10; backdrop-filter: blur(18px); }
.brand { color: var(--ink); font-weight: 720; text-decoration: none; }
.brand span { background: var(--mi-orange); border-radius: 9px; color: white; display: inline-grid; height: 32px; margin-right: 9px; place-items: center; width: 32px; }
.nav { display: flex; gap: 28px; }
.nav a { color: var(--ink-muted); font-size: 14px; text-decoration: none; }
.nav a.router-link-active { color: var(--ink); font-weight: 650; }
.account { background: none; border: 0; color: var(--ink-muted); cursor: pointer; justify-self: end; }
.shell__content { margin: 0 auto; max-width: 1180px; padding: 36px 28px 60px; }
@media (max-width: 760px) { .shell__header { grid-template-columns: 1fr auto; padding: 0 16px; } .nav { display: none; } .shell__content { padding: 24px 16px 48px; } }
</style>

