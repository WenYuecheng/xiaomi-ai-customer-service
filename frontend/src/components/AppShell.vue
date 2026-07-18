<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ChatDotRound, DataAnalysis, Postcard, ShoppingCart, UserFilled } from '@element-plus/icons-vue'

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
        <RouterLink to="/advisor">AI 智能选购</RouterLink>
        <RouterLink v-if="auth.canOperate" to="/knowledge">知识库</RouterLink>
        <RouterLink v-if="auth.canOperate" to="/operations">运营洞察</RouterLink>
      </nav>
      <details class="account-menu">
        <summary><i :data-avatar="auth.user?.avatar_key">{{ auth.user?.display_name?.slice(0, 1).toUpperCase() }}</i><span>{{ auth.user?.display_name }}</span></summary>
        <div><RouterLink to="/profile">✦ 个人主页</RouterLink><RouterLink to="/profile">⚙ 账户设置</RouterLink><button type="button" @click="logout">退出登录</button></div>
      </details>
    </header>
    <main class="shell__content"><slot /></main>
    <nav class="mobile-nav" aria-label="移动端主导航">
      <RouterLink to="/chat"><el-icon><ChatDotRound /></el-icon><span>问答</span></RouterLink>
      <RouterLink to="/advisor"><el-icon><ShoppingCart /></el-icon><span>选购</span></RouterLink>
      <RouterLink to="/profile"><el-icon><UserFilled /></el-icon><span>我的</span></RouterLink>
      <RouterLink v-if="auth.canOperate" to="/knowledge"><el-icon><Postcard /></el-icon><span>知识库</span></RouterLink>
      <RouterLink v-if="auth.canOperate" to="/operations"><el-icon><DataAnalysis /></el-icon><span>洞察</span></RouterLink>
    </nav>
  </div>
</template>

<style scoped>
.shell { min-height: 100vh; }
.shell__header { align-items: center; background: rgba(249,247,253,.82); border-bottom: 1px solid rgba(218,210,238,.85); box-shadow: 0 8px 30px rgba(62,45,105,.05); display: grid; grid-template-columns: 1fr auto 1fr; height: 68px; padding: 0 32px; position: sticky; top: 0; z-index: 10; backdrop-filter: blur(20px); }
.brand { color: var(--ink); font-weight: 720; text-decoration: none; }
.brand span { background: linear-gradient(135deg,var(--mi-orange),#ff9852); border-radius: 10px; box-shadow: 0 8px 18px rgba(255,105,0,.2); color: white; display: inline-grid; height: 32px; margin-right: 9px; place-items: center; width: 32px; }
.nav { display: flex; gap: 28px; }
.nav a { color: var(--ink-muted); font-size: 14px; text-decoration: none; }
.nav a { border-radius: 999px; padding: 8px 11px; transition: background-color .18s ease,color .18s ease; position: relative; }
.nav a:hover { background: #eee9fb; color: #5d47b4; }
.nav a.router-link-active { background: transparent; color: #6045c7; font-weight: 650; }
.nav a.router-link-active::after { content: ''; position: absolute; bottom: 0; left: 10%; width: 80%; height: 3px; background: linear-gradient(90deg, var(--mi-orange), var(--hyper-violet)); border-radius: 3px; }
.account-menu{justify-self:end;position:relative}.account-menu summary{align-items:center;color:var(--ink-muted);cursor:pointer;display:flex;font-size:12px;gap:8px;list-style:none}.account-menu summary::-webkit-details-marker{display:none}.account-menu summary i{background:linear-gradient(135deg,#ff6900,#ca5cda);border-radius:10px;color:white;display:grid;font-style:normal;height:33px;place-items:center;width:33px}.account-menu summary i[data-avatar='ocean']{background:linear-gradient(135deg,#128ddd,#51d0c4)}.account-menu summary i[data-avatar='mint']{background:linear-gradient(135deg,#0ca98a,#a4df86)}.account-menu summary i[data-avatar='cosmos']{background:linear-gradient(135deg,#6547d8,#d45ac7)}.account-menu>div{background:rgba(255,255,255,.97);border:1px solid #e3dcef;border-radius:15px;box-shadow:0 18px 48px rgba(43,29,76,.18);display:grid;min-width:155px;padding:7px;position:absolute;right:0;top:43px}.account-menu a,.account-menu button{background:transparent;border:0;border-radius:9px;color:#665b72;cursor:pointer;font-size:12px;padding:9px 10px;text-align:left;text-decoration:none}.account-menu a:hover,.account-menu button:hover{background:#f1ecfa;color:#6144c0}
.shell__content { margin: 0 auto; max-width: 1180px; padding: 36px 28px 60px; }
.mobile-nav { display: none; }
@media (max-width: 760px) {
  .shell__header { grid-template-columns: 1fr auto; padding: 0 16px; }
  .nav { display: none; }
  .shell__content { padding: 24px 16px 90px; }
  .mobile-nav { display: flex; justify-content: space-around; position: fixed; bottom: 20px; left: 16px; right: 16px; background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(20px); border: 1px solid rgba(218, 210, 238, 0.85); border-radius: 999px; padding: 10px 0; z-index: 100; box-shadow: 0 8px 24px rgba(62, 45, 105, 0.12); }
  .mobile-nav a { display: flex; flex-direction: column; align-items: center; color: var(--ink-muted); text-decoration: none; font-size: 10px; gap: 4px; transition: color 0.2s; }
  .mobile-nav a .el-icon { font-size: 20px; }
  .mobile-nav a.router-link-active { color: var(--hyper-violet); font-weight: bold; }
}
</style>
