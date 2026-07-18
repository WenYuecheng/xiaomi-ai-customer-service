<script setup lang="ts">
import { onMounted } from 'vue'

import AdvisorBriefForm from '@/components/advisor/AdvisorBriefForm.vue'
import AdvisorHistory from '@/components/advisor/AdvisorHistory.vue'
import AdvisorPlanCard from '@/components/advisor/AdvisorPlanCard.vue'
import AiTracePanel from '@/components/chat/AiTracePanel.vue'
import { useAdvisorLab } from '@/composables/useAdvisorLab'

const advisor = useAdvisorLab()
onMounted(() => {
  void advisor.load().then(async () => {
    const sessionId = new URLSearchParams(window.location.search).get('session_id')
    if (sessionId) await advisor.selectSession(sessionId)
  }).catch((reason) => { advisor.error.value = reason instanceof Error ? reason.message : '加载失败' })
})
</script>

<template>
  <section class="advisor-page">
    <header class="lab-hero">
      <div><span>DEEPSEEK × BGE / PRODUCT INTELLIGENCE</span><h1>AI 智能选购实验室</h1><p>把预算、用途和偏好交给三段 AI 流水线，得到有真实知识来源的产品对比方案。</p></div>
      <div class="pipeline-badge"><i></i><b>3 次 DeepSeek</b><span>需求理解 · 证据重排 · 方案生成</span></div>
    </header>
    <el-alert v-if="advisor.error.value" :title="advisor.error.value" type="error" show-icon closable @close="advisor.error.value = ''" />
    <div class="lab-layout">
      <div class="lab-main">
        <AdvisorBriefForm :knowledge-bases="advisor.knowledgeBases.value" :busy="advisor.busy.value" @submit="advisor.submit" />
        <AiTracePanel v-if="advisor.trace.value.length" :steps="advisor.trace.value" class="lab-trace" />
        <AdvisorPlanCard v-if="advisor.plan.value" :plan="advisor.plan.value" :sources="advisor.sources.value" @follow-up="advisor.followUp" />
        <div v-else class="result-stage" :class="{ running: advisor.busy.value }"><div class="stage-core">✦</div><strong>{{ advisor.busy.value ? 'AI 正在组装可信方案' : '方案将在这里展开' }}</strong><p>运行时会实时展示每一次模型调用和检索过程。</p></div>
      </div>
      <AdvisorHistory :sessions="advisor.sessions.value" :active-id="advisor.activeSessionId.value" @select="advisor.selectSession" @delete="advisor.deleteSession" />
    </div>
  </section>
</template>

<style scoped>
.advisor-page { margin: 0 auto; max-width: 1180px; }.lab-hero { align-items: end; display: flex; gap: 30px; justify-content: space-between; margin-bottom: 26px; }.lab-hero>div:first-child>span { color: #7759df; font-family: var(--font-mono); font-size: 10px; letter-spacing: .16em; }.lab-hero h1 { font-size: clamp(38px,5vw,62px); letter-spacing: -.055em; line-height: .98; margin: 10px 0 13px; }.lab-hero p { color: #756c85; line-height: 1.65; margin: 0; max-width: 680px; }.pipeline-badge { background: linear-gradient(145deg,#1a1527,#34234f); border-radius: 18px; color: white; display: grid; flex: 0 0 270px; gap: 4px; padding: 16px 18px; position: relative; }.pipeline-badge i { animation: lab-pulse 1.3s infinite; background: #a87aff; border-radius: 50%; height: 7px; position: absolute; right: 15px; top: 15px; width: 7px; }.pipeline-badge b { font-size: 16px; }.pipeline-badge span { color: #baafca; font-size: 9px; }.lab-layout { align-items: start; display: grid; gap: 16px; grid-template-columns: minmax(0,1fr) 220px; }.lab-main { display: grid; gap: 16px; min-width: 0; }.lab-trace { margin: 0; }.result-stage { align-items: center; background: radial-gradient(circle at 50% 0,rgba(155,116,244,.18),transparent 55%),rgba(255,255,255,.62); border: 1px dashed #cfc4e7; border-radius: 27px; color: #7d738d; display: flex; flex-direction: column; min-height: 290px; justify-content: center; text-align: center; }.stage-core { background: linear-gradient(135deg,#7558e5,#d453ae); border-radius: 20px; box-shadow: 0 18px 40px rgba(112,76,203,.24); color: white; display: grid; font-size: 24px; height: 66px; margin-bottom: 16px; place-items: center; width: 66px; }.result-stage strong { color: #40364f; font-size: 18px; }.result-stage p { font-size: 11px; }.result-stage.running .stage-core { animation: stage-orbit 1.4s infinite ease-in-out; }
@keyframes lab-pulse { 50% { box-shadow: 0 0 0 7px rgba(168,122,255,.12); } } @keyframes stage-orbit { 50% { transform: translateY(-8px) rotate(8deg); } }
@media (max-width: 860px) { .lab-layout { grid-template-columns: 1fr; }.lab-hero { align-items: flex-start; flex-direction: column; }.pipeline-badge { align-self: stretch; flex-basis: auto; }.lab-layout>aside { order: -1; } }
@media (prefers-reduced-motion: reduce) { .pipeline-badge i,.result-stage.running .stage-core { animation: none; } }
</style>
