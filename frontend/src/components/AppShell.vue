<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChatDotRound, DataAnalysis, Files, House, ShoppingCart, UserFilled } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const pageName = computed(() => ({ chat: '智能问答', advisor: '选购顾问', knowledge: '知识中心', operations: '运营中心', profile: '个人中心' })[String(route.name)] ?? '服务台')
function logout(): void { auth.logout(); void router.push({ name: 'login' }) }
</script>

<template>
  <div class="app-frame">
    <aside class="sidebar">
      <RouterLink class="brand" to="/chat" aria-label="小米智能客服首页">
        <span class="brand__mark">mi</span><span><b>小米智能客服</b><small>AI SERVICE DESK</small></span>
      </RouterLink>
      <nav class="side-nav" aria-label="主导航">
        <span class="side-nav__label">服务</span>
        <RouterLink to="/chat"><el-icon><ChatDotRound /></el-icon><span>智能问答</span></RouterLink>
        <RouterLink to="/advisor"><el-icon><ShoppingCart /></el-icon><span>选购顾问</span></RouterLink>
        <template v-if="auth.canOperate">
          <span class="side-nav__label side-nav__label--space">运营</span>
          <RouterLink to="/knowledge"><el-icon><Files /></el-icon><span>知识中心</span></RouterLink>
          <RouterLink to="/operations"><el-icon><DataAnalysis /></el-icon><span>运营中心</span></RouterLink>
        </template>
      </nav>
      <div class="trust-card"><i>✓</i><div><b>可信回答模式</b><small>回答基于知识库并提供来源</small></div></div>
      <details class="account-menu">
        <summary><i :data-avatar="auth.user?.avatar_key">{{ auth.user?.display_name?.slice(0, 1).toUpperCase() }}</i><span><b>{{ auth.user?.display_name }}</b><small>{{ auth.user?.role === 'user' ? '普通用户' : '运营人员' }}</small></span></summary>
        <div><RouterLink to="/profile">个人资料</RouterLink><button type="button" @click="logout">退出登录</button></div>
      </details>
    </aside>
    <section class="workspace">
      <header class="topbar"><div><small>小米智能客服 /</small><b>{{ pageName }}</b></div><span class="service-status"><i /> 服务正常</span></header>
      <main class="workspace__content"><slot /></main>
    </section>
    <nav class="mobile-nav" aria-label="移动端主导航">
      <RouterLink to="/chat"><el-icon><ChatDotRound /></el-icon><span>问答</span></RouterLink>
      <RouterLink to="/advisor"><el-icon><ShoppingCart /></el-icon><span>选购</span></RouterLink>
      <RouterLink to="/profile"><el-icon><UserFilled /></el-icon><span>我的</span></RouterLink>
      <RouterLink v-if="auth.canOperate" to="/knowledge"><el-icon><House /></el-icon><span>知识</span></RouterLink>
    </nav>
  </div>
</template>

<style scoped>
.app-frame{display:grid;grid-template-columns:248px minmax(0,1fr);min-height:100vh}.sidebar{background:#1d1c1a;color:#fff;display:flex;flex-direction:column;padding:24px 16px;position:fixed;inset:0 auto 0 0;width:248px;z-index:20}.brand{align-items:center;display:flex;gap:12px;padding:0 8px 28px;text-decoration:none}.brand__mark{background:var(--mi-orange);border-radius:11px;display:grid;font-size:18px;font-weight:800;height:40px;place-items:center;width:40px}.brand b,.brand small{display:block}.brand b{font-size:15px}.brand small{color:#8f8c87;font-family:var(--font-mono);font-size:9px;letter-spacing:.12em;margin-top:4px}.side-nav{display:grid;gap:5px}.side-nav__label{color:#77746f;font-size:10px;font-weight:700;letter-spacing:.14em;padding:8px 12px;text-transform:uppercase}.side-nav__label--space{margin-top:18px}.side-nav a{align-items:center;border-radius:11px;color:#aaa7a2;display:flex;font-size:14px;gap:12px;padding:11px 12px;text-decoration:none;transition:.18s}.side-nav a:hover{background:#292825;color:#fff}.side-nav a.router-link-active{background:#fff;color:#191816;font-weight:700}.side-nav a.router-link-active .el-icon{color:var(--mi-orange)}.trust-card{align-items:flex-start;background:#272623;border:1px solid #34322f;border-radius:14px;display:flex;gap:10px;margin:auto 0 14px;padding:13px}.trust-card>i{background:#193b2c;border-radius:50%;color:#67d49e;display:grid;font-style:normal;height:22px;place-items:center;width:22px}.trust-card b,.trust-card small{display:block}.trust-card b{font-size:12px}.trust-card small{color:#8f8c87;font-size:10px;line-height:1.5;margin-top:3px}.account-menu{position:relative}.account-menu summary{align-items:center;border-top:1px solid #32312e;cursor:pointer;display:flex;gap:10px;list-style:none;padding:16px 8px 0}.account-menu summary>i{background:#3b3935;border-radius:10px;display:grid;font-style:normal;height:36px;place-items:center;width:36px}.account-menu b,.account-menu small{display:block}.account-menu b{font-size:12px}.account-menu small{color:#85827d;font-size:10px;margin-top:3px}.account-menu>div{background:#fff;border:1px solid var(--line);border-radius:12px;bottom:52px;box-shadow:var(--shadow-lg);display:grid;left:0;min-width:180px;padding:6px;position:absolute}.account-menu a,.account-menu button{background:none;border:0;border-radius:8px;color:var(--ink);cursor:pointer;font-size:12px;padding:9px;text-align:left;text-decoration:none}.account-menu a:hover,.account-menu button:hover{background:var(--surface-soft)}.workspace{grid-column:2;min-width:0}.topbar{align-items:center;background:rgba(246,245,243,.88);border-bottom:1px solid var(--line);display:flex;height:64px;justify-content:space-between;padding:0 32px;position:sticky;top:0;z-index:10;backdrop-filter:blur(18px)}.topbar div{display:flex;gap:7px}.topbar small{color:var(--ink-muted)}.service-status{align-items:center;background:#edf7f1;border:1px solid #d8ede0;border-radius:999px;color:#28734f;display:flex;font-size:11px;gap:7px;padding:6px 10px}.service-status i{background:#31a86f;border-radius:50%;height:6px;width:6px}.workspace__content{margin:0 auto;max-width:1320px;padding:34px 38px 64px}.mobile-nav{display:none}@media(max-width:850px){.app-frame{display:block}.sidebar{display:none}.workspace{grid-column:auto}.topbar{height:56px;padding:0 18px}.workspace__content{padding:24px 16px 88px}.mobile-nav{background:rgba(29,28,26,.95);border:1px solid #3b3935;border-radius:18px;bottom:14px;display:flex;justify-content:space-around;left:14px;padding:9px 4px;position:fixed;right:14px;z-index:100;backdrop-filter:blur(18px)}.mobile-nav a{align-items:center;color:#9d9a95;display:flex;flex-direction:column;font-size:10px;gap:3px;min-width:56px;text-decoration:none}.mobile-nav a .el-icon{font-size:19px}.mobile-nav a.router-link-active{color:#fff}.mobile-nav a.router-link-active .el-icon{color:var(--mi-orange)}}
</style>
<style scoped>
.sidebar{background:rgba(252,251,249,.94);border-right:1px solid var(--line);color:var(--ink);backdrop-filter:blur(20px)}.brand{border-bottom:1px solid var(--line);margin:0 4px 20px;padding:0 4px 20px}.brand__mark{border-radius:9px;font-size:15px;height:36px;width:36px}.brand small{color:#aaa49d}.side-nav__label{color:#aaa49d}.side-nav a{color:#6e6963}.side-nav a:hover{background:#f3f1ed;color:var(--ink)}.side-nav a.router-link-active{background:#fff3e9;box-shadow:inset 0 0 0 1px #ffe0c8;color:#bd5109}.trust-card{background:#f7f6f3;border-color:var(--line)}.trust-card>i{background:#e7f6ee;color:#25805a}.trust-card b{color:var(--ink)}.trust-card small{color:var(--ink-muted)}.account-menu summary{border-top-color:var(--line)}.account-menu summary>i{background:#eeeae5;color:var(--ink)}.account-menu small{color:var(--ink-muted)}.topbar{background:rgba(252,251,249,.9)}
@media(max-width:850px){.mobile-nav{background:rgba(255,255,255,.94);border-color:var(--line);box-shadow:0 14px 40px rgba(60,54,48,.12)}.mobile-nav a{color:#8c8781}.mobile-nav a.router-link-active{color:var(--ink)}}
</style>
