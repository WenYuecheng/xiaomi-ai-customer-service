<script setup lang="ts">
import { reactive, shallowRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import RegisterForm from '@/components/auth/RegisterForm.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const form = reactive({ username: '', password: '' })
const busy = shallowRef(false)
const error = shallowRef('')
const mode = shallowRef<'login' | 'register'>('login')
const welcome = shallowRef(false)

async function submit(): Promise<void> {
  busy.value = true
  error.value = ''
  try {
    await auth.login(form.username, form.password)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/chat'
    await router.push(redirect)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '登录失败'
  } finally {
    busy.value = false
  }
}

async function register(payload: { username: string; password: string; passwordConfirm: string }): Promise<void> {
  busy.value = true
  error.value = ''
  try {
    await auth.register(payload.username, payload.password, payload.passwordConfirm)
    welcome.value = true
    await new Promise((resolve) => setTimeout(resolve, 520))
    await router.push('/profile')
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '注册失败，请稍后再试'
  } finally {
    busy.value = false
  }
}

function switchMode(nextMode: 'login' | 'register'): void {
  mode.value = nextMode
  error.value = ''
}
</script>

<template>
  <main class="login">
    <section class="login__intro">
      <span class="login__mark">MI / AI SERVICE</span>
      <h1>每个答案，<br /><em>都有依据。</em></h1>
      <p>面向小米产品资料的可信智能客服。检索、引用、兜底与连续追问，在同一个工作台完成。</p>
    </section>
    <section class="auth-card" :class="`auth-card--${mode}`">
      <div class="auth-tabs" role="tablist" aria-label="账户入口">
        <button type="button" :class="{ active: mode === 'login' }" @click="switchMode('login')">登录</button>
        <button type="button" :class="{ active: mode === 'register' }" @click="switchMode('register')">创建账号</button>
      </div>
      <Transition name="auth-swap" mode="out-in">
        <div v-if="mode === 'login'" key="login" class="auth-panel">
          <span class="auth-eyebrow">WELCOME BACK</span><h2>继续你的探索</h2><p>使用已有账号进入可信 AI 工作台</p>
          <el-alert v-if="error" :title="error" type="error" :closable="false" />
          <el-form :model="form" label-position="top" @submit.prevent="submit">
            <el-form-item label="用户名"><el-input v-model="form.username" autocomplete="username" /></el-form-item>
            <el-form-item label="密码"><el-input v-model="form.password" type="password" show-password autocomplete="current-password" /></el-form-item>
            <el-button type="primary" :loading="busy" native-type="submit">进入工作台</el-button>
          </el-form>
        </div>
        <div v-else key="register" class="auth-panel">
          <span class="auth-eyebrow">CREATE YOUR SPACE</span><h2>建立你的 AI 档案</h2><p>从第一次咨询开始，让兴趣星系慢慢生长。</p>
          <RegisterForm :busy="busy" :api-error="error" @register="register" />
        </div>
      </Transition>
      <div class="auth-orbit" aria-hidden="true"><i /><i /><i /></div>
    </section>
    <Transition name="welcome"><div v-if="welcome" class="welcome-burst"><span>✦</span><strong>AI 空间创建成功</strong></div></Transition>
  </main>
</template>

<style scoped>
.login { background: radial-gradient(circle at 8% 10%,rgba(124,92,229,.12),transparent 28%),radial-gradient(circle at 92% 88%,rgba(255,105,0,.11),transparent 30%),var(--paper); display: grid; grid-template-columns: 1.15fr .85fr; gap: 8vw; min-height: 100vh; overflow: hidden; padding: 8vh 9vw; position: relative; }
.login__intro { align-self: center; }
.login__mark { color: var(--mi-orange); font-family: var(--font-mono); font-size: 12px; letter-spacing: .18em; }
.login h1 { color: var(--ink); font-family: var(--font-display); font-size: clamp(52px, 7vw, 92px); letter-spacing: -.06em; line-height: .98; margin: 28px 0; }
.login h1 em { color: var(--mi-orange); font-style: normal; }
.login__intro p { color: var(--ink-soft); font-size: 17px; line-height: 1.8; max-width: 560px; }
.auth-card { align-self: center; background: rgba(255,255,255,.82); border: 1px solid rgba(222,214,239,.9); border-radius: 28px; box-shadow: 0 34px 90px rgba(50,35,90,.15); min-height: 520px; overflow: hidden; padding: 20px 25px 26px; position: relative; backdrop-filter: blur(24px); }
.auth-tabs { background: #f1edf8; border-radius: 14px; display: grid; grid-template-columns: 1fr 1fr; padding: 4px; position: relative; z-index: 2; }.auth-tabs button { background: transparent; border: 0; border-radius: 11px; color: #857b94; cursor: pointer; font-weight: 650; padding: 10px; transition: .22s; }.auth-tabs button.active { background: white; box-shadow: 0 7px 18px rgba(66,47,112,.1); color: #5e43be; }
.auth-panel { padding: 28px 5px 0; position: relative; z-index: 2; }.auth-panel h2 { font-size: 27px; margin: 6px 0; }.auth-panel > p { color: var(--ink-muted); font-size: 13px; margin: 0 0 22px; }.auth-eyebrow { color: #7b60df; font-family: var(--font-mono); font-size: 10px; letter-spacing: .17em; }.auth-panel .el-button { height: 47px; margin-top: 8px; width: 100%; }
.auth-orbit { bottom: -85px; height: 210px; opacity: .28; position: absolute; right: -80px; width: 210px; }.auth-orbit i { animation: orbit 8s linear infinite; border: 1px solid #8d69e5; border-radius: 50%; inset: 0; position: absolute; }.auth-orbit i:nth-child(2) { inset: 30px; animation-direction: reverse; animation-duration: 6s; }.auth-orbit i:nth-child(3) { background: linear-gradient(135deg,#ff6a00,#a45bea); border: 0; inset: 78px; }
.auth-swap-enter-active,.auth-swap-leave-active { transition: opacity .2s,transform .2s; }.auth-swap-enter-from { opacity: 0; transform: translateX(18px); }.auth-swap-leave-to { opacity: 0; transform: translateX(-18px); }
.welcome-burst { align-items: center; background: rgba(30,20,54,.94); border: 1px solid #8f72e9; border-radius: 22px; box-shadow: 0 25px 70px rgba(46,29,90,.36); color: white; display: flex; gap: 12px; left: 50%; padding: 18px 24px; position: fixed; top: 50%; transform: translate(-50%,-50%); z-index: 20; }.welcome-burst span { color: #ff9d55; font-size: 26px; }.welcome-enter-active,.welcome-leave-active { transition: .3s; }.welcome-enter-from,.welcome-leave-to { opacity: 0; transform: translate(-50%,-45%) scale(.86); }
@keyframes orbit { to { transform: rotate(360deg); } }
@media (max-width: 800px) { .login { grid-template-columns: 1fr; padding: 7vh 7vw; } .login__intro p { display: none; } }
@media (prefers-reduced-motion: reduce) { .auth-orbit i { animation: none; }.auth-swap-enter-active,.auth-swap-leave-active,.welcome-enter-active,.welcome-leave-active { transition: none; } }
</style>
