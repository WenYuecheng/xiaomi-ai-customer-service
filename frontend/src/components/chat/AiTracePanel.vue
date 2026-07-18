<script setup lang="ts">
import { computed } from 'vue'

import type { AiTraceStep } from '@/types'

const props = defineProps<{ steps: AiTraceStep[] }>()

const orderedSteps = computed(() => {
  const order: AiTraceStep['stage'][] = ['understanding', 'retrieval', 'generation', 'grounding']
  return [...props.steps].sort((left, right) => order.indexOf(left.stage) - order.indexOf(right.stage))
})

const stageLabels: Record<AiTraceStep['stage'], string> = {
  understanding: 'DeepSeek 调用 1/2 · 理解问题',
  retrieval: 'BGE · 检索知识',
  generation: 'DeepSeek 调用 2/2 · 生成回答',
  grounding: '引用校验 · 确认答案有依据',
}

const statusLabels: Record<AiTraceStep['status'], string> = {
  running: '进行中',
  completed: '已完成',
  skipped: '已跳过',
  degraded: '已降级',
  failed: '失败',
}
</script>

<template>
  <details class="ai-trace" open>
    <summary>
      <span class="ai-trace__spark">✦</span>
      <span><b>AI 执行轨迹</b><small>可验证的模型与知识检索过程</small></span>
      <span class="ai-trace__count">{{ steps.length }}/4 阶段</span>
    </summary>
    <ol class="ai-trace__steps">
      <li v-for="step in orderedSteps" :key="step.stage" :class="[`is-${step.status}`, `is-${step.stage}`]">
        <span class="ai-trace__node" aria-hidden="true"></span>
        <div class="ai-trace__main">
          <div class="ai-trace__heading">
            <strong>{{ stageLabels[step.stage] }}</strong>
            <span class="ai-trace__status">{{ statusLabels[step.status] }}</span>
            <time v-if="step.duration_ms !== null && step.duration_ms !== undefined">{{ step.duration_ms }} ms</time>
          </div>
          <p>{{ step.summary }}</p>
          <code>{{ step.engine }} · {{ step.model }}</code>
        </div>
      </li>
    </ol>
  </details>
</template>

<style scoped>
.ai-trace { background: linear-gradient(135deg,rgba(244,241,255,.9),rgba(255,245,251,.86)); border: 1px solid #ded6f5; border-radius: 15px; margin: 14px 0 4px; overflow: hidden; }
.ai-trace summary { align-items: center; cursor: pointer; display: flex; gap: 10px; list-style: none; padding: 11px 13px; user-select: none; }.ai-trace summary::-webkit-details-marker { display: none; }
.ai-trace summary > span:nth-child(2) { display: grid; gap: 1px; }.ai-trace summary b { color: #3f316c; font-size: 13px; }.ai-trace summary small { color: #8b80a5; font-size: 10px; }
.ai-trace__spark { background: linear-gradient(135deg,#7050e7,#d85bb4); border-radius: 9px; color: white; display: grid; height: 28px; place-items: center; width: 28px; }.ai-trace__count { color: #7159c5; font-family: var(--font-mono); font-size: 10px; margin-left: auto; }
.ai-trace__steps { list-style: none; margin: 0; padding: 2px 14px 13px 26px; }.ai-trace__steps li { display: flex; gap: 10px; min-height: 58px; position: relative; }.ai-trace__steps li:not(:last-child)::before { background: #d8cff0; content: ''; height: calc(100% - 10px); left: 5px; position: absolute; top: 15px; width: 1px; }
.ai-trace__node { background: #7c62dd; border: 3px solid #ebe6fb; border-radius: 50%; flex: 0 0 auto; height: 11px; margin-top: 5px; width: 11px; z-index: 1; }.is-running .ai-trace__node { animation: trace-pulse 1.1s infinite; background: #e05ba8; }.is-skipped .ai-trace__node { background: #aaa2bb; }.is-degraded .ai-trace__node { background: #e69a31; }.is-failed .ai-trace__node { background: #d84e57; }
.ai-trace__main { min-width: 0; padding-bottom: 9px; }.ai-trace__heading { align-items: center; display: flex; flex-wrap: wrap; gap: 7px; }.ai-trace__heading strong { color: #34284f; font-size: 12px; }.ai-trace__heading time { color: #948aa8; font-family: var(--font-mono); font-size: 10px; }.ai-trace__status { background: #e9e3fb; border-radius: 999px; color: #664cb9; font-size: 9px; padding: 2px 6px; }.is-skipped .ai-trace__status { background: #eeecef; color: #77717f; }.is-degraded .ai-trace__status { background: #fff0d8; color: #a05e00; }.is-failed .ai-trace__status { background: #ffe3e5; color: #aa2832; }
.ai-trace p { color: #756b88; font-size: 11px; line-height: 1.45; margin: 4px 0; }.ai-trace code { background: rgba(255,255,255,.7); border-radius: 5px; color: #795ec9; font-family: var(--font-mono); font-size: 9px; padding: 2px 5px; }
@keyframes trace-pulse { 50% { box-shadow: 0 0 0 6px rgba(224,91,168,.12); transform: scale(.78); } }
@media (prefers-reduced-motion: reduce) { .is-running .ai-trace__node { animation: none; } }
</style>
