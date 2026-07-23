<script setup lang="ts">
import { computed, reactive } from 'vue'

interface RegisterPayload {
  username: string
  password: string
  passwordConfirm: string
}

withDefaults(defineProps<{ busy?: boolean; apiError?: string }>(), {
  busy: false,
  apiError: '',
})

const emit = defineEmits<{ register: [payload: RegisterPayload] }>()
const form = reactive({ username: '', password: '', passwordConfirm: '' })
const errors = reactive({ username: '', password: '', passwordConfirm: '' })

const passwordStrength = computed(() => {
  const value = form.password
  let score = 0
  if (value.length >= 8) score += 1
  if (/[a-z]/.test(value) && /[A-Z]/.test(value)) score += 1
  if (/\d/.test(value)) score += 1
  if (/[^A-Za-z0-9]/.test(value) || value.length >= 12) score += 1
  return score <= 1 ? '较弱' : score === 2 ? '适中' : '较强'
})

function validate(): boolean {
  const username = form.username.trim().toLowerCase()
  errors.username = /^[a-z0-9_]{3,32}$/.test(username)
    ? ''
    : '请输入 3–32 位字母、数字或下划线'
  const bytes = new TextEncoder().encode(form.password).length
  errors.password = bytes < 8 || bytes > 72 || !/[A-Za-z]/.test(form.password) || !/\d/.test(form.password)
    ? '密码需为 8–72 字节，并同时包含字母和数字'
    : ''
  errors.passwordConfirm = form.password === form.passwordConfirm ? '' : '两次输入的密码不一致'
  return !errors.username && !errors.password && !errors.passwordConfirm
}

function submit(): void {
  if (!validate()) return
  emit('register', {
    username: form.username.trim().toLowerCase(),
    password: form.password,
    passwordConfirm: form.passwordConfirm,
  })
}
</script>

<template>
  <form class="register-form" novalidate @submit.prevent="submit">
    <p v-if="apiError" class="form-error" role="alert">{{ apiError }}</p>
    <label class="field">
      <span>用户名</span>
      <input v-model="form.username" name="username" autocomplete="username" placeholder="字母、数字或下划线" />
      <small :class="{ 'field-error': errors.username }">{{ errors.username || '登录后仍可设置更有个性的显示名称' }}</small>
    </label>
    <label class="field">
      <span>密码</span>
      <input v-model="form.password" name="password" type="password" autocomplete="new-password" placeholder="至少 8 位，包含字母和数字" />
      <div class="strength" :data-strength="passwordStrength"><i /><i /><i /><span>密码强度：{{ passwordStrength }}</span></div>
      <small v-if="errors.password" class="field-error">{{ errors.password }}</small>
    </label>
    <label class="field">
      <span>确认密码</span>
      <input v-model="form.passwordConfirm" name="password-confirm" type="password" autocomplete="new-password" placeholder="再次输入密码" />
      <small v-if="errors.passwordConfirm" class="field-error">{{ errors.passwordConfirm }}</small>
    </label>
    <el-button class="register-submit" type="primary" native-type="submit" :loading="busy">创建我的 AI 空间</el-button>
    <p class="privacy-copy">注册即表示你了解：画像只使用产品偏好与互动信号，不保存支付信息。</p>
  </form>
</template>

<style scoped>
.register-form { display: grid; gap: 17px; }
.field { display: grid; gap: 7px; }
.field > span { color: #332a46; font-size: 13px; font-weight: 650; }
.field input { background: rgba(247, 244, 255, .88); border: 1px solid #ded6ef; border-radius: 13px; box-sizing: border-box; color: #231a36; font: inherit; height: 46px; outline: none; padding: 0 14px; transition: border-color .2s, box-shadow .2s, transform .2s; width: 100%; }
.field input:focus { border-color: #7c5ce5; box-shadow: 0 0 0 4px rgba(124, 92, 229, .12); transform: translateY(-1px); }
.field small { color: #8d839d; font-size: 11px; line-height: 1.4; min-height: 15px; }
.field .field-error,.form-error { color: #c83d5a; }
.form-error { background: #fff0f3; border: 1px solid #ffd0da; border-radius: 11px; font-size: 12px; margin: 0; padding: 10px 12px; }
.strength { align-items: center; display: grid; gap: 5px; grid-template-columns: repeat(3, 1fr) auto; }
.strength i { background: #e8e4ef; border-radius: 99px; height: 4px; transition: background .25s, transform .25s; }
.strength span { color: #877e96; font-size: 10px; margin-left: 4px; }
.strength[data-strength='较弱'] i:first-child,.strength[data-strength='适中'] i:nth-child(-n+2),.strength[data-strength='较强'] i { background: linear-gradient(90deg,#ff7a34,#9c5cf2); transform: scaleY(1.35); }
.register-submit { height: 47px; margin-top: 2px; width: 100%; }
.privacy-copy { color: #948b9f; font-size: 10px; line-height: 1.6; margin: 0; text-align: center; }
@media (prefers-reduced-motion: reduce) { .field input,.strength i { transition: none; } }
</style>
