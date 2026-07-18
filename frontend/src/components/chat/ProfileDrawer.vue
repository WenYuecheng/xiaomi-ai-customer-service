<script setup lang="ts">
import { computed } from 'vue'

interface Profile {
  product_preferences: string[]
  intent_distribution: Record<string, number>
  feedback_summary: Record<string, number>
  event_count: number
}

const props = defineProps<{ open: boolean; profile?: Profile }>()
const emit = defineEmits<{ close: []; clear: [] }>()
const intentLabels: Record<string, string> = {
  knowledge_query: '产品知识', human_transfer: '人工服务', order_query: '订单物流', troubleshooting: '故障排查',
}
const intentItems = computed(() => {
  const entries = Object.entries(props.profile?.intent_distribution ?? {})
  const total = entries.reduce((sum, [, count]) => sum + count, 0) || 1
  return entries.map(([key, count]) => ({ key, label: intentLabels[key] ?? '其他咨询', count, percent: Math.round(count / total * 100) }))
})
const helpful = computed(() => props.profile?.feedback_summary.up ?? 0)
const improve = computed(() => props.profile?.feedback_summary.down ?? 0)
const feedbackTotal = computed(() => helpful.value + improve.value)
</script>

<template>
  <el-drawer class="profile-drawer" :model-value="open" title="我的咨询画像" size="min(480px, 94vw)" @close="emit('close')">
    <div v-if="profile" class="profile-content">
      <section class="profile-hero"><span>累计咨询</span><strong>{{ profile.event_count }}</strong><p>画像只使用产品偏好和互动信号，不包含敏感信息。</p></section>
      <section><h3>偏好产品</h3><div class="preference-list"><span v-for="(item, index) in profile.product_preferences" :key="item" :style="{ '--delay': `${index * 45}ms` }">{{ item }}</span><p v-if="!profile.product_preferences.length">多咨询几个具体型号后，这里会形成你的偏好。</p></div></section>
      <section><h3>咨询主题</h3><div v-if="intentItems.length" class="intent-list"><div v-for="item in intentItems" :key="item.key"><div><span>{{ item.label }}</span><b>{{ item.count }} 次 · {{ item.percent }}%</b></div><div class="bar"><i :style="{ width: `${item.percent}%` }" /></div></div></div><p v-else class="empty-copy">暂无足够的咨询主题数据。</p></section>
      <section><h3>回答反馈</h3><div class="feedback-summary"><div class="positive"><span>👍 有帮助</span><b>{{ helpful }}</b></div><div class="negative"><span>💡 需改进</span><b>{{ improve }}</b></div></div><p v-if="!feedbackTotal" class="empty-copy">评价回答后，这里会显示反馈趋势。</p></section>
      <el-button class="clear-profile" type="danger" plain @click="emit('clear')">清除我的演示数据</el-button>
    </div>
  </el-drawer>
</template>

<style scoped>
.profile-content { display: grid; gap: 24px; }.profile-content section { background: rgba(255,255,255,.76); border: 1px solid #ebe7fa; border-radius: 18px; padding: 18px; }.profile-content h3 { font-size: 14px; margin: 0 0 14px; }.profile-hero { background: linear-gradient(135deg, #6f55ed, #a34cf0) !important; color: white; }.profile-hero span { font-size: 12px; opacity: .8; }.profile-hero strong { display: block; font-size: 42px; line-height: 1.1; margin: 6px 0; }.profile-hero p { font-size: 12px; margin: 0; opacity: .78; }.preference-list { display: flex; flex-wrap: wrap; gap: 8px; }.preference-list span { animation: chip-in .35s both; animation-delay: var(--delay); background: linear-gradient(135deg, #eee9ff, #fcecff); border: 1px solid #ded3ff; border-radius: 999px; color: #5b43bd; padding: 7px 11px; }.preference-list p,.empty-copy { color: var(--ink-muted); font-size: 13px; margin: 0; }.intent-list { display: grid; gap: 13px; }.intent-list > div > div:first-child { display: flex; font-size: 13px; justify-content: space-between; }.intent-list b { color: var(--ink-muted); font-weight: 500; }.bar { background: #eeeef5; border-radius: 999px; height: 8px; margin-top: 7px; overflow: hidden; }.bar i { background: linear-gradient(90deg, #6e52ed, #d45ed8); border-radius: inherit; display: block; height: 100%; }.feedback-summary { display: grid; gap: 10px; grid-template-columns: 1fr 1fr; }.feedback-summary div { border-radius: 14px; padding: 14px; }.feedback-summary span { display: block; font-size: 12px; }.feedback-summary b { display: block; font-size: 24px; margin-top: 4px; }.positive { background: #e9f9f2; color: #147454; }.negative { background: #fff2e9; color: #aa4d16; }.clear-profile { width: 100%; }.profile-drawer :deep(.el-drawer__body) { background: radial-gradient(circle at 90% 0, #e9ddff, transparent 30%), #f8f7fd; overscroll-behavior: contain; }
@keyframes chip-in { from { opacity: 0; transform: translateY(5px); } }
@media (prefers-reduced-motion: reduce) { .preference-list span { animation: none; } }
</style>
