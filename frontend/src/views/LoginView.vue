<script setup lang="ts">
import { reactive, shallowRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const form = reactive({ username: '', password: '' })
const busy = shallowRef(false)
const error = shallowRef('')

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
</script>

<template>
  <main class="login">
    <section class="login__intro">
      <span class="login__mark">MI / AI SERVICE</span>
      <h1>每个答案，<br /><em>都有依据。</em></h1>
      <p>面向小米产品资料的可信智能客服。检索、引用、兜底与连续追问，在同一个工作台完成。</p>
    </section>
    <el-card class="login__card" shadow="never">
      <h2>进入工作台</h2>
      <p>使用课程演示账号登录</p>
      <el-alert v-if="error" :title="error" type="error" :closable="false" />
      <el-form :model="form" label-position="top" @submit.prevent="submit">
        <el-form-item label="用户名"><el-input v-model="form.username" autocomplete="username" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="form.password" type="password" show-password autocomplete="current-password" /></el-form-item>
        <el-button type="primary" :loading="busy" native-type="submit">登录</el-button>
      </el-form>
    </el-card>
  </main>
</template>

<style scoped>
.login { background: var(--paper); display: grid; grid-template-columns: 1.2fr .8fr; gap: 8vw; min-height: 100vh; padding: 10vh 10vw; }
.login__intro { align-self: center; }
.login__mark { color: var(--mi-orange); font-family: var(--font-mono); font-size: 12px; letter-spacing: .18em; }
.login h1 { color: var(--ink); font-family: var(--font-display); font-size: clamp(52px, 7vw, 92px); letter-spacing: -.06em; line-height: .98; margin: 28px 0; }
.login h1 em { color: var(--mi-orange); font-style: normal; }
.login__intro p { color: var(--ink-soft); font-size: 17px; line-height: 1.8; max-width: 560px; }
.login__card { align-self: center; border: 0; border-radius: 18px; box-shadow: 0 24px 70px rgba(22,24,29,.1); padding: 18px; }
.login__card h2 { font-size: 26px; margin-bottom: 4px; }
.login__card > p { color: var(--ink-muted); margin-bottom: 28px; }
.login__card .el-button { margin-top: 12px; width: 100%; }
@media (max-width: 800px) { .login { grid-template-columns: 1fr; padding: 7vh 7vw; } .login__intro p { display: none; } }
</style>

