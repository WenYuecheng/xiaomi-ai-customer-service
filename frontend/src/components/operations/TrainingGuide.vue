<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { Aim, DataAnalysis, TrendCharts } from '@element-plus/icons-vue'

export interface TrainingRun {
  id: string
  version: string
  status: string
  precision_at_k?: number
  recall_at_k?: number
  artifact_filename?: string
  target?: 'balanced' | 'precision' | 'recall'
  k?: number
  dataset_name?: string
  sample_count?: number
  product_count?: number
  changed?: boolean
  metric_delta?: Record<string, number | null>
  explanation?: string
}

defineProps<{ runs: TrainingRun[]; busy: boolean }>()
const emit = defineEmits<{ train: [target: 'balanced' | 'precision' | 'recall'] }>()
const target = shallowRef<'balanced' | 'precision' | 'recall'>('balanced')
const goals = [
  { value: 'balanced' as const, title: '均衡推荐', icon: DataAnalysis, copy: '兼顾推荐准确度与覆盖范围，适合日常运营。' },
  { value: 'precision' as const, title: '优先准确', icon: Aim, copy: '减少无关推荐，让有限推荐位更精准。' },
  { value: 'recall' as const, title: '扩大召回', icon: TrendCharts, copy: '尽量找回用户可能喜欢的产品，适合探索偏好。' },
]
const selected = computed(() => goals.find((item) => item.value === target.value) ?? goals[0])
const percent = (value?: number): string => value == null ? '—' : `${Math.round(value * 100)}%`
</script>

<template>
  <section class="training-guide">
    <div class="guide-heading"><div><span>RECOMMENDATION LAB</span><h2>推荐模型训练室</h2><p>选择优化目标，系统会根据咨询行为重新评估产品偏好。</p></div><el-tag effect="dark" round>离线 SVD · 演示环境</el-tag></div>
    <div class="goal-grid" role="radiogroup" aria-label="训练优化目标">
      <button v-for="goal in goals" :key="goal.value" type="button" :data-testid="`goal-${goal.value}`" :class="{ selected: target === goal.value }" role="radio" :aria-checked="target === goal.value" @click="target = goal.value"><component :is="goal.icon" aria-hidden="true" /><b>{{ goal.title }}</b><span>{{ goal.copy }}</span></button>
    </div>
    <div class="selection-copy"><b>你的选择：{{ selected.title }}</b><span>{{ selected.copy }}</span></div>
    <div v-if="runs[0]" class="latest-run">
      <div><small>最近版本</small><strong>{{ runs[0].version }}</strong><span>{{ runs[0].dataset_name === 'observed-user-behavior' ? '真实咨询行为' : '明确标记的演示数据' }} · {{ runs[0].sample_count ?? 0 }} 位用户 · {{ runs[0].product_count ?? 0 }} 个产品</span></div>
      <div class="metric"><small>推荐准确率</small><strong>{{ percent(runs[0].precision_at_k) }}</strong><span>Precision@{{ runs[0].k ?? 3 }}</span></div>
      <div class="metric"><small>偏好召回率</small><strong>{{ percent(runs[0].recall_at_k) }}</strong><span>Recall@{{ runs[0].k ?? 3 }}</span></div>
    </div>
    <el-empty v-else description="尚未训练；选择目标后开始第一次评估" :image-size="70" />
    <div class="guide-footer"><p>指标来自“每位用户留出 1 个已咨询产品”的验证方式；没有新增行为时，系统会明确提示数据未变化。</p><el-button data-testid="start-training" type="primary" size="large" :loading="busy" @click="emit('train', target)">按“{{ selected.title }}”开始训练</el-button></div>
  </section>
</template>

<style scoped>
.training-guide { background: radial-gradient(circle at 90% 0, rgba(177,116,255,.3), transparent 32%), linear-gradient(135deg,#fff,#f6f1ff); border: 1px solid #e4dafa; border-radius: 24px; padding: 22px; }.guide-heading { align-items: start; display: flex; justify-content: space-between; }.guide-heading span { color: #7659de; font-family: var(--font-mono); font-size: 10px; letter-spacing: .13em; }.guide-heading h2 { font-size: 23px; margin: 6px 0; }.guide-heading p { color: var(--ink-muted); margin: 0; }.goal-grid { display: grid; gap: 10px; grid-template-columns: repeat(3,1fr); margin: 20px 0 12px; }.goal-grid button { background: rgba(255,255,255,.72); border: 1px solid #e6dff6; border-radius: 16px; color: var(--ink-soft); cursor: pointer; display: grid; gap: 6px; min-height: 126px; padding: 15px; text-align: left; transition: border-color .18s ease, box-shadow .18s ease, transform .18s ease; }.goal-grid button:hover { border-color: #9e85ed; transform: translateY(-2px); }.goal-grid button.selected { background: linear-gradient(145deg,#7658e9,#a74de8); border-color: transparent; box-shadow: 0 14px 28px rgba(108,72,205,.22); color: white; }.goal-grid svg { height: 23px; width: 23px; }.goal-grid b { font-size: 14px; }.goal-grid span { font-size: 11px; line-height: 1.5; opacity: .76; }.selection-copy { background: #eee8ff; border-radius: 12px; color: #563cae; display: flex; flex-wrap: wrap; font-size: 12px; gap: 8px; padding: 10px 12px; }.latest-run { display: grid; gap: 12px; grid-template-columns: 1.5fr .7fr .7fr; margin: 16px 0; }.latest-run > div { background: rgba(255,255,255,.8); border: 1px solid #ebe5f8; border-radius: 15px; padding: 14px; }.latest-run small,.latest-run span { color: var(--ink-muted); display: block; font-size: 10px; }.latest-run strong { display: block; font-size: 16px; margin: 5px 0; }.latest-run .metric strong { color: #6649cf; font-size: 28px; font-variant-numeric: tabular-nums; }.guide-footer { align-items: center; display: flex; gap: 20px; justify-content: space-between; }.guide-footer p { color: var(--ink-muted); font-size: 11px; line-height: 1.6; margin: 0; max-width: 520px; }
@media(max-width:760px){.goal-grid,.latest-run{grid-template-columns:1fr}.guide-footer{align-items:stretch;flex-direction:column}}
@media(prefers-reduced-motion:reduce){.goal-grid button{transition:none}}
</style>
