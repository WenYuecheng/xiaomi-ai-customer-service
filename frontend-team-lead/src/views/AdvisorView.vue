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
      <div><span>EVIDENCE-BASED PRODUCT ADVISOR</span><h1>选得明白，也有依据</h1><p>把预算、用途和偏好转化为可核验的产品对比。参数来自当前知识库，缺失信息会明确标记。</p></div>
      <div class="pipeline-badge"><i></i><b>可信选购流水线</b><span>理解需求 → 检索证据 → 比较权衡 → 给出建议</span></div>
    </header>
    <el-alert v-if="advisor.error.value" :title="advisor.error.value" type="error" show-icon closable @close="advisor.error.value = ''" />
    <div class="lab-layout">
      <div class="lab-main">
        <AdvisorBriefForm :knowledge-bases="advisor.knowledgeBases.value" :busy="advisor.busy.value" @submit="advisor.submit" />
        <AiTracePanel v-if="advisor.trace.value.length" :steps="advisor.trace.value" class="lab-trace" />
        <AdvisorPlanCard v-if="advisor.plan.value" :plan="advisor.plan.value" :sources="advisor.sources.value" @follow-up="advisor.followUp" />
        <div v-else class="result-stage" :class="{ running: advisor.busy.value }"><div class="stage-core">MI</div><strong>{{ advisor.busy.value ? '正在检索并核对产品证据' : '你的对比方案将在这里展开' }}</strong><p>展示候选产品、关键差异、适配理由、取舍和原始来源。</p><div class="stage-steps"><span>需求解释</span><i /><span>知识检索</span><i /><span>多维比较</span><i /><span>推荐结论</span></div></div>
      </div>
      <AdvisorHistory :sessions="advisor.sessions.value" :active-id="advisor.activeSessionId.value" @select="advisor.selectSession" @delete="advisor.deleteSession" />
    </div>
  </section>
</template>

<style scoped>
.advisor-page{margin:0 auto;max-width:1180px}.lab-hero{align-items:flex-end;display:flex;gap:30px;justify-content:space-between;margin-bottom:26px}.lab-hero>div:first-child>span{color:var(--mi-orange);font-family:var(--font-mono);font-size:10px;font-weight:700;letter-spacing:.16em}.lab-hero h1{font-size:clamp(40px,5vw,64px);letter-spacing:-.06em;line-height:.98;margin:10px 0 13px}.lab-hero p{color:var(--ink-muted);line-height:1.7;margin:0;max-width:680px}.pipeline-badge{background:#1d1c1a;border:1px solid #33312e;border-radius:16px;color:white;display:grid;flex:0 0 290px;gap:5px;padding:17px 19px;position:relative}.pipeline-badge i{animation:lab-pulse 1.3s infinite;background:#31b678;border-radius:50%;height:7px;position:absolute;right:16px;top:16px;width:7px}.pipeline-badge b{font-size:15px}.pipeline-badge span{color:#999590;font-size:9px}.lab-layout{align-items:start;display:grid;gap:16px;grid-template-columns:minmax(0,1fr) 230px}.lab-main{display:grid;gap:16px;min-width:0}.lab-trace{margin:0}.result-stage{align-items:center;background:#fff;border:1px solid var(--line);border-radius:20px;color:var(--ink-muted);display:flex;flex-direction:column;justify-content:center;min-height:300px;text-align:center}.stage-core{background:var(--mi-orange);border-radius:15px;box-shadow:0 14px 32px rgba(255,105,0,.2);color:white;display:grid;font-size:13px;font-weight:800;height:54px;margin-bottom:16px;place-items:center;width:54px}.result-stage strong{color:var(--ink);font-size:18px}.result-stage p{font-size:11px}.result-stage.running .stage-core{animation:stage-orbit 1.4s infinite ease-in-out}.stage-steps{align-items:center;display:flex;gap:7px;margin-top:18px}.stage-steps span{background:#f4f2ef;border-radius:999px;color:var(--ink-soft);font-size:9px;padding:6px 9px}.stage-steps i{background:#d8d4ce;height:1px;width:12px}
@keyframes lab-pulse { 50% { box-shadow: 0 0 0 7px rgba(49,182,120,.12); } } @keyframes stage-orbit { 50% { transform: translateY(-8px) rotate(8deg); } }
@media (max-width: 860px) { .lab-layout { grid-template-columns: 1fr; }.lab-hero { align-items: flex-start; flex-direction: column; }.pipeline-badge { align-self: stretch; flex-basis: auto; }.lab-layout>aside { order: -1; } }
@media (prefers-reduced-motion: reduce) { .pipeline-badge i,.result-stage.running .stage-core { animation: none; } }
</style>
<style scoped>
.pipeline-badge{background:#fff;border-color:var(--line);box-shadow:var(--shadow-sm);color:var(--ink)}.pipeline-badge span{color:var(--ink-muted)}.stage-core{background:#fff3e9;border:1px solid #ffdbc0;box-shadow:none;color:var(--mi-orange)}
</style>
