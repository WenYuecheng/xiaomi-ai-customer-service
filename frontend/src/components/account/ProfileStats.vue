<script setup lang="ts">
import type { AccountStats } from '@/types'

defineProps<{ stats: AccountStats }>()
</script>

<template>
  <section class="stats-grid" aria-label="个人数据概览">
    <article><span>累计咨询</span><strong>{{ stats.consultation_count }}</strong><small>每一次提问都沉淀为偏好信号</small></article>
    <article><span>选购方案</span><strong>{{ stats.advisor_plan_count }}</strong><small>已生成的可信 AI 决策方案</small></article>
    <article><span>互动反馈</span><strong>{{ stats.feedback_count }}</strong><small>帮助机器人持续理解你的标准</small></article>
    <article class="accent"><span>有帮助率</span><strong>{{ stats.helpful_rate === null ? '—' : `${stats.helpful_rate}%` }}</strong><small>{{ stats.helpful_rate === null ? '完成评价后开始统计' : '基于你提交的真实反馈' }}</small></article>
  </section>
</template>

<style scoped>
.stats-grid{display:grid;gap:12px;grid-template-columns:repeat(4,1fr);margin:17px 0}.stats-grid article{animation:card-rise .45s both;background:rgba(255,255,255,.8);border:1px solid #e5dff1;border-radius:19px;box-shadow:0 14px 35px rgba(66,47,112,.05);padding:18px}.stats-grid article:nth-child(2){animation-delay:.05s}.stats-grid article:nth-child(3){animation-delay:.1s}.stats-grid article:nth-child(4){animation-delay:.15s}.stats-grid span,.stats-grid small{color:#8d829e;display:block;font-size:11px}.stats-grid strong{color:#2a203b;display:block;font-size:34px;letter-spacing:-.05em;margin:6px 0}.stats-grid .accent{background:linear-gradient(135deg,#f1ebff,#ffedf6);border-color:#ded2fa}.stats-grid small{line-height:1.45}@keyframes card-rise{from{opacity:0;transform:translateY(12px)}}@media(max-width:800px){.stats-grid{grid-template-columns:1fr 1fr}}@media(prefers-reduced-motion:reduce){.stats-grid article{animation:none}}
</style>
