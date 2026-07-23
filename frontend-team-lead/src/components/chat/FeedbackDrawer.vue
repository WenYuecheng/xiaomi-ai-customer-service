<script setup lang="ts">
import { computed, reactive } from 'vue'
import { ChatDotRound, CircleCloseFilled, QuestionFilled, WarningFilled } from '@element-plus/icons-vue'

const props = defineProps<{ open: boolean; loading?: boolean }>()
const emit = defineEmits<{
  close: []
  submit: [payload: { reason: string; correction?: string }]
}>()
const form = reactive({ reason: '', correction: '' })
const reasons = [
  { value: 'inaccurate', label: '信息不准确', icon: WarningFilled },
  { value: 'unresolved', label: '没有解决问题', icon: CircleCloseFilled },
  { value: 'unclear', label: '表达不够清楚', icon: QuestionFilled },
  { value: 'other', label: '其他建议', icon: ChatDotRound },
]
const canSubmit = computed(() => Boolean(form.reason) && !props.loading)

function submit(): void {
  if (!canSubmit.value) return
  emit('submit', {
    reason: reasons.find((item) => item.value === form.reason)?.label ?? form.reason,
    correction: form.correction.trim() || undefined,
  })
}
</script>

<template>
  <el-drawer
    class="feedback-drawer"
    :model-value="open"
    size="min(480px, 94vw)"
    direction="rtl"
    :show-close="false"
    @close="emit('close')"
  >
    <template #header>
      <div class="feedback-heading"><span>✦</span><div><h2>帮助小爱变得更好</h2><p>选择最接近的原因，纠正内容可以留空。</p></div></div>
    </template>
    <div class="reason-grid" role="radiogroup" aria-label="需要改进的原因">
      <button
        v-for="item in reasons"
        :key="item.value"
        type="button"
        :class="{ selected: form.reason === item.value }"
        role="radio"
        :aria-checked="form.reason === item.value"
        @click="form.reason = item.value"
      ><component :is="item.icon" aria-hidden="true" /><span>{{ item.label }}</span></button>
    </div>
    <label class="correction-label" for="feedback-correction">你希望得到怎样的回答？</label>
    <el-input
      id="feedback-correction"
      v-model="form.correction"
      type="textarea"
      :rows="6"
      maxlength="2000"
      show-word-limit
      resize="none"
      placeholder="可填写正确参数、遗漏的信息或更清楚的表达…"
    />
    <div class="privacy-note">仅用于改进本次回答，不要填写账号、密码或联系方式。</div>
    <template #footer>
      <div class="drawer-actions"><el-button @click="emit('close')">暂不反馈</el-button><el-button type="primary" :loading="loading" :disabled="!canSubmit" @click="submit">提交改进建议</el-button></div>
    </template>
  </el-drawer>
</template>

<style scoped>
.feedback-heading { align-items: center; display: flex; gap: 14px; }.feedback-heading > span { background: linear-gradient(135deg, #6d53ef, #b65cff); border-radius: 14px; color: white; display: grid; font-size: 22px; height: 46px; place-items: center; width: 46px; }.feedback-heading h2 { color: var(--ink); font-size: 21px; margin: 0 0 4px; }.feedback-heading p { color: var(--ink-muted); font-size: 13px; margin: 0; }.reason-grid { display: grid; gap: 10px; grid-template-columns: 1fr 1fr; margin: 8px 0 24px; }.reason-grid button { align-items: center; background: #f7f5ff; border: 1px solid #e5dfff; border-radius: 15px; color: #4e466d; cursor: pointer; display: flex; gap: 10px; min-height: 68px; padding: 14px; text-align: left; transition: background-color .18s ease, border-color .18s ease, transform .18s ease; }.reason-grid button:hover { border-color: #9d87f4; transform: translateY(-2px); }.reason-grid button.selected { background: linear-gradient(135deg, #eee9ff, #f9ecff); border-color: #765be8; color: #4d32b7; }.reason-grid svg { height: 21px; width: 21px; }.correction-label { color: var(--ink); display: block; font-size: 14px; font-weight: 650; margin-bottom: 9px; }.privacy-note { color: var(--ink-muted); font-size: 12px; line-height: 1.6; margin-top: 12px; }.drawer-actions { display: flex; justify-content: flex-end; }.feedback-drawer :deep(.el-drawer__body) { background: radial-gradient(circle at 100% 0, #eee8ff, transparent 34%), #fff; overscroll-behavior: contain; }
@media (max-width: 520px) { .reason-grid { grid-template-columns: 1fr; } }
@media (prefers-reduced-motion: reduce) { .reason-grid button { transition: none; } }
</style>
<style scoped>
.feedback-heading>span{background:#fff2e8;border:1px solid #ffd6b7;color:var(--mi-orange)}.reason-grid button{background:#faf9f7;border-color:var(--line);color:var(--ink-soft)}.reason-grid button:hover{border-color:#ffc397}.reason-grid button.selected{background:#fff3e9;border-color:#ffb77f;color:#b84d08}.feedback-drawer :deep(.el-drawer__body){background:#fbfaf8}
</style>
