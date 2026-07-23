<script setup lang="ts">
import { computed } from 'vue'
import type { DeepReadonly } from 'vue'

import type { AccountDashboard, User } from '@/types'

const props = defineProps<{ user: User; dashboard: DeepReadonly<AccountDashboard> }>()
const emit = defineEmits<{ edit: []; password: [] }>()
const roleLabels = { admin: '管理员', operator: '知识运营', user: '普通用户' } as const
const greeting = computed(() => {
  const hour = new Date().getHours()
  return hour < 6 ? '夜深了' : hour < 12 ? '早上好' : hour < 18 ? '下午好' : '晚上好'
})
</script>

<template>
  <section class="profile-hero">
    <div class="profile-hero__noise" aria-hidden="true" />
    <header><span>XIAOMI SERVICE ACCOUNT / {{ user.avatar_key.toUpperCase() }}</span><b>账户状态正常 ●</b></header>
    <div class="profile-hero__main">
      <div class="avatar" :data-avatar="user.avatar_key">{{ user.display_name.slice(0, 1).toUpperCase() }}</div>
      <div><p>{{ greeting }}，</p><h1>{{ user.display_name }}</h1><div class="identity"><span>{{ roleLabels[user.role] }}</span><span>已加入 {{ dashboard.joined_days }} 天</span><span>服务等级 Lv.{{ dashboard.growth_level }}</span></div></div>
    </div>
    <div class="profile-hero__actions"><button type="button" @click="emit('edit')">编辑个人资料</button><button type="button" @click="emit('password')">修改登录密码</button></div>
    <div class="orb orb--one" aria-hidden="true" /><div class="orb orb--two" aria-hidden="true" />
  </section>
</template>

<style scoped>
.profile-hero { background: radial-gradient(circle at 85% 0,rgba(172,114,255,.42),transparent 30%),radial-gradient(circle at 10% 100%,rgba(255,105,0,.2),transparent 34%),linear-gradient(145deg,#17112c,#2b1b52); border: 1px solid rgba(173,139,255,.28); border-radius: 30px; box-shadow: 0 30px 80px rgba(39,25,76,.24); color: white; min-height: 300px; overflow: hidden; padding: 27px 31px; position: relative; }.profile-hero header { display: flex; font-family: var(--font-mono); font-size: 10px; justify-content: space-between; letter-spacing: .14em; opacity: .65; position: relative; z-index: 2; }.profile-hero header b { color: #bca8ff; font-weight: 500; }.profile-hero__main { align-items: center; display: flex; gap: 22px; margin-top: 55px; position: relative; z-index: 2; }.avatar { background: linear-gradient(135deg,#ff6900,#ce5bdb); border: 1px solid #ffffff47; border-radius: 25px; box-shadow: 0 17px 42px rgba(185,75,224,.35); display: grid; font-size: 35px; font-weight: 760; height: 84px; place-items: center; width: 84px; }.avatar[data-avatar='ocean']{background:linear-gradient(135deg,#128ddd,#51d0c4)}.avatar[data-avatar='mint']{background:linear-gradient(135deg,#0ca98a,#a4df86)}.avatar[data-avatar='sunset']{background:linear-gradient(135deg,#ff5d6c,#ffb45d)}.avatar[data-avatar='cosmos']{background:linear-gradient(135deg,#6547d8,#d45ac7)}.avatar[data-avatar='ember']{background:linear-gradient(135deg,#c83c28,#ff8a38)}.profile-hero__main p { color: #c9bfda; margin: 0; }.profile-hero__main h1 { font-size: clamp(36px,5vw,58px); letter-spacing: -.055em; line-height: 1; margin: 6px 0 14px; }.identity { display: flex; flex-wrap: wrap; gap: 7px; }.identity span { background: #ffffff12; border: 1px solid #ffffff1f; border-radius: 999px; color: #dcd3ea; font-size: 11px; padding: 6px 9px; }.profile-hero__actions { bottom: 28px; display: flex; gap: 8px; position: absolute; right: 30px; z-index: 3; }.profile-hero__actions button { background: #ffffff11; border: 1px solid #ffffff2b; border-radius: 12px; color: white; cursor: pointer; padding: 9px 12px; backdrop-filter: blur(12px); }.orb { animation: float-orb 6s ease-in-out infinite; border: 1px solid #b88dff55; border-radius: 50%; height: 150px; position: absolute; right: 8%; top: 22%; width: 150px; }.orb--two { animation-delay: -2s; height: 62px; right: 22%; top: 64%; width: 62px; }.profile-hero__noise { background-image:radial-gradient(#ffffff18 1px,transparent 1px);background-size:18px 18px;inset:0;mask-image:linear-gradient(90deg,transparent,#000);position:absolute}@keyframes float-orb{50%{transform:translateY(-10px) rotate(12deg)}}@media(max-width:700px){.profile-hero{min-height:390px;padding:22px}.profile-hero__main{align-items:flex-start;margin-top:40px}.profile-hero__actions{bottom:22px;left:22px;right:auto}.avatar{height:66px;width:66px}.profile-hero header b{display:none}}@media(prefers-reduced-motion:reduce){.orb{animation:none}}
</style>
<style scoped>
.profile-hero{background:radial-gradient(circle at 85% 0,rgba(255,105,0,.22),transparent 32%),#1d1c1a;border-color:#33312e;border-radius:20px;box-shadow:0 24px 60px rgba(30,27,24,.16);min-height:280px}.profile-hero header b{color:#70d6a3}.avatar{background:var(--mi-orange);border-radius:20px;box-shadow:0 17px 42px rgba(255,105,0,.24)}.profile-hero__main p{color:#aaa7a2}.identity span{color:#d8d4cf}.profile-hero__actions button{border-radius:10px}.profile-hero__actions button:hover{border-color:#ff9b59}.orb{border-color:#ff95552b}
</style>
<style scoped>
.profile-hero{background:#fff;border-color:var(--line);box-shadow:var(--shadow-sm);color:var(--ink)}.profile-hero header{color:var(--ink-muted)}.profile-hero header b{color:var(--success)}.profile-hero__main p{color:var(--ink-muted)}.identity span{background:#f7f5f2;border-color:var(--line);color:var(--ink-soft)}.profile-hero__actions button{background:#fff;border-color:var(--line);color:var(--ink)}.profile-hero__actions button:hover{background:#fff7f0}.profile-hero__noise{opacity:.25}.orb{border-color:#ffdcc4}
</style>
