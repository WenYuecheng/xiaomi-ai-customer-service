<script setup lang="ts">
import { computed } from 'vue'

import type { AdvisorPlan, Source } from '@/types'
import SourceRail from '@/components/chat/SourceRail.vue'

import AdvisorRadar from './AdvisorRadar.vue'

const props = defineProps<{ plan: AdvisorPlan; sources: readonly Source[] }>()
const emit = defineEmits<{ followUp: [question: string] }>()

const models = computed(() => props.plan.candidates.map((item) => item.model))
const scoreTone = (score: number): string => score >= 85 ? 'excellent' : score >= 70 ? 'good' : 'fair'
</script>

<template>
  <section class="advisor-plan">
    <header class="plan-heading">
      <div><span>AI SHOPPING BRIEF</span><h2>{{ plan.title }}</h2><p>{{ plan.interpreted_need }}</p></div>
      <div class="trust-mark"><b>3×</b><small>DeepSeek<br>结构化调用</small></div>
    </header>

    <div class="candidate-grid">
      <article v-for="candidate in plan.candidates" :key="candidate.model" class="candidate-card">
        <div class="score-orbit" :class="`is-${scoreTone(candidate.fit_score)}`" :style="{ '--score': `${candidate.fit_score}%` }">
          <strong>{{ candidate.fit_score }}%</strong><span>需求匹配</span>
        </div>
        <div class="candidate-copy">
          <h3>{{ candidate.model }}</h3>
          <span class="price" :class="{ 'has-evidence': candidate.price.status === 'evidence' }">{{ candidate.price.display }}</span>
          <ul class="highlights"><li v-for="item in candidate.highlights" :key="item">{{ item }}</li></ul>
          <ul class="tradeoffs"><li v-for="item in candidate.tradeoffs" :key="item">{{ item }}</li></ul>
        </div>
      </article>
    </div>

    <div class="analysis-grid">
      <article class="radar-panel"><div class="panel-label"><b>AI 需求匹配评分</b><span>不是官方性能跑分</span></div><AdvisorRadar :candidates="plan.candidates" /></article>
      <article class="recommendation-panel">
        <span>AI RECOMMENDATION</span>
        <h3>优先考虑 {{ plan.recommendation.primary_model }}</h3>
        <p>{{ plan.recommendation.summary }}</p>
        <ul><li v-for="reason in plan.recommendation.reasons" :key="reason">{{ reason }}</li></ul>
        <div v-if="plan.recommendation.caveats.length" class="caveats">{{ plan.recommendation.caveats.join(' · ') }}</div>
      </article>
    </div>

    <div v-if="plan.comparison_rows.length" class="comparison-table-wrap">
      <table class="comparison-table">
        <thead><tr><th>对比维度</th><th v-for="model in models" :key="model">{{ model }}</th></tr></thead>
        <tbody><tr v-for="row in plan.comparison_rows" :key="row.dimension"><th>{{ row.dimension }}</th><td v-for="model in models" :key="model">{{ row.values[model] ?? '资料未明确' }}</td></tr></tbody>
      </table>
    </div>

    <SourceRail v-if="sources.length" :sources="sources" />
    <footer v-if="plan.follow_up_suggestions.length" class="follow-ups">
      <span>继续让 AI 调整方案</span>
      <button v-for="question in plan.follow_up_suggestions" :key="question" data-testid="advisor-follow-up" type="button" @click="emit('followUp', question)">{{ question }}</button>
    </footer>
  </section>
</template>

<style scoped>
.advisor-plan { background: radial-gradient(circle at 92% 0,rgba(139,104,255,.2),transparent 31%),linear-gradient(145deg,#fff,#f8f5ff); border: 1px solid #ddd4f4; border-radius: 28px; box-shadow: 0 24px 70px rgba(72,48,135,.12); overflow: hidden; padding: 24px; }
.plan-heading { align-items: flex-start; display: flex; gap: 20px; justify-content: space-between; }.plan-heading span,.recommendation-panel>span { color: #7658dc; font-family: var(--font-mono); font-size: 10px; letter-spacing: .15em; }.plan-heading h2 { font-size: clamp(24px,3vw,36px); letter-spacing: -.04em; margin: 7px 0; }.plan-heading p { color: #746b87; line-height: 1.6; margin: 0; max-width: 680px; }.trust-mark { align-items: center; background: #171326; border-radius: 18px; color: white; display: flex; gap: 9px; padding: 12px 15px; }.trust-mark b { color: #be9cff; font-size: 27px; }.trust-mark small { font-size: 9px; line-height: 1.35; opacity: .72; }
.candidate-grid { display: grid; gap: 12px; grid-template-columns: repeat(2,minmax(0,1fr)); margin: 22px 0; }.candidate-card { align-items: flex-start; background: rgba(255,255,255,.82); border: 1px solid #e7e0f5; border-radius: 20px; display: flex; gap: 16px; padding: 17px; transition: transform .2s ease,border-color .2s ease; }.candidate-card:hover { border-color: #a995ed; transform: translateY(-3px); }.score-orbit { align-items: center; aspect-ratio: 1; background: conic-gradient(#7758e8 var(--score,90%),#eee9f8 0); border-radius: 50%; display: flex; flex: 0 0 76px; flex-direction: column; justify-content: center; position: relative; }.score-orbit::before { background: white; border-radius: 50%; content: ''; inset: 6px; position: absolute; }.score-orbit strong,.score-orbit span { position: relative; z-index: 1; }.score-orbit strong { color: #563dbb; font-size: 19px; }.score-orbit span { color: #8e85a0; font-size: 8px; }.score-orbit.is-good { background: conic-gradient(#ff7a27 78%,#eee9f8 0); }.score-orbit.is-fair { background: conic-gradient(#34a6c9 65%,#eee9f8 0); }.candidate-copy { min-width: 0; }.candidate-copy h3 { margin: 2px 0 7px; }.price { background: #f1eef6; border-radius: 999px; color: #81778f; display: inline-block; font-size: 10px; padding: 4px 8px; }.price.has-evidence { background: #e8f8f1; color: #167252; }.highlights,.tradeoffs { list-style: none; margin: 9px 0 0; padding: 0; }.highlights li,.tradeoffs li { color: #564d69; font-size: 11px; line-height: 1.5; margin-top: 4px; }.highlights li::before { color: #6c50dd; content: '✦'; margin-right: 6px; }.tradeoffs li::before { color: #d28437; content: '△'; margin-right: 6px; }
.analysis-grid { display: grid; gap: 14px; grid-template-columns: 1.15fr .85fr; }.radar-panel,.recommendation-panel { background: rgba(255,255,255,.76); border: 1px solid #e7e1f3; border-radius: 20px; min-width: 0; padding: 17px; }.panel-label { align-items: center; display: flex; justify-content: space-between; }.panel-label b { font-size: 13px; }.panel-label span { color: #968ba8; font-size: 9px; }.recommendation-panel { background: linear-gradient(150deg,#1d1731,#362457); color: white; }.recommendation-panel h3 { font-size: 22px; margin: 12px 0 7px; }.recommendation-panel p { color: #d6cce9; line-height: 1.6; }.recommendation-panel ul { padding-left: 18px; }.recommendation-panel li { color: #eee8fa; font-size: 12px; margin: 7px 0; }.caveats { border-top: 1px solid rgba(255,255,255,.14); color: #aa9cbd; font-size: 10px; line-height: 1.6; margin-top: 16px; padding-top: 11px; }
.comparison-table-wrap { margin: 18px 0; overflow-x: auto; }.comparison-table { border-collapse: separate; border-spacing: 0; min-width: 620px; width: 100%; }.comparison-table th,.comparison-table td { border-bottom: 1px solid #e8e2f3; color: #554c68; font-size: 11px; padding: 11px 13px; text-align: left; }.comparison-table thead th { background: #eee9fb; color: #4f3ba0; }.comparison-table th:first-child { font-weight: 700; }
.follow-ups { align-items: center; display: flex; flex-wrap: wrap; gap: 8px; margin-top: 17px; }.follow-ups span { color: #746a87; font-size: 11px; margin-right: 4px; }.follow-ups button { background: white; border: 1px solid #dcd3f3; border-radius: 999px; color: #6248bd; cursor: pointer; font-size: 11px; padding: 7px 11px; }.follow-ups button:hover { border-color: #7d62df; }
@media (max-width: 760px) { .candidate-grid,.analysis-grid { grid-template-columns: 1fr; }.plan-heading { flex-direction: column; }.trust-mark { align-self: stretch; justify-content: center; }.advisor-plan { padding: 17px; } }
@media (prefers-reduced-motion: reduce) { .candidate-card { transition: none; } }
</style>
