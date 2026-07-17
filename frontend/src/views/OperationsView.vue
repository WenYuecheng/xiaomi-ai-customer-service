<script setup lang="ts">
import { onMounted, ref, shallowRef } from 'vue'

import { api } from '@/api/client'

interface Topic { term: string; count: number; score: number }
interface Training { version: string; status: string; precision_at_k: number; recall_at_k: number }
const topics = ref<Topic[]>([])
const logs = ref<Record<string, unknown>[]>([])
const training = shallowRef<Training>()
const busy = shallowRef(false)

onMounted(async () => {
  topics.value = (await api.get('/operations/hot-topics?window=week')).data.items
  logs.value = (await api.get('/operations/logs')).data
})

async function train(): Promise<void> {
  busy.value = true
  try { training.value = (await api.post('/recommendation/training-runs')).data }
  finally { busy.value = false }
}
</script>

<template>
  <section>
    <header class="operations-heading"><div><span>SERVICE SIGNALS</span><h1>运营洞察</h1><p>把咨询行为转成热词、画像与可评估的推荐模型。</p></div><el-button type="primary" :loading="busy" @click="train">训练推荐模型</el-button></header>
    <div class="metric-grid">
      <el-card shadow="never"><strong>本周热词</strong><div class="topic-cloud"><span v-for="topic in topics" :key="topic.term">{{ topic.term }} <small>{{ topic.count }}</small></span></div></el-card>
      <el-card shadow="never"><strong>最近训练</strong><div v-if="training" class="training"><b>{{ training.version }}</b><span>Precision@K {{ training.precision_at_k.toFixed(3) }}</span><span>Recall@K {{ training.recall_at_k.toFixed(3) }}</span></div><el-empty v-else description="尚未在本次会话训练" /></el-card>
    </div>
    <el-table :data="logs" class="log-table"><el-table-column prop="question" label="用户问题" /><el-table-column prop="answer" label="机器人回答" /><el-table-column prop="intent" label="意图" width="130" /><el-table-column prop="latency_ms" label="耗时(ms)" width="110" /></el-table>
  </section>
</template>

<style scoped>
.operations-heading { align-items: end; display: flex; justify-content: space-between; }.operations-heading span { color: var(--mi-orange); font-family: var(--font-mono); font-size: 11px; letter-spacing: .16em; }.operations-heading h1 { font-size: 38px; margin: 8px 0; }.operations-heading p { color: var(--ink-muted); }
.metric-grid { display: grid; gap: 18px; grid-template-columns: 1.2fr .8fr; margin: 32px 0; }.topic-cloud { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 22px; }.topic-cloud span { background: #fff2e9; border-radius: 999px; color: #a94712; padding: 8px 12px; }.topic-cloud small { opacity: .6; }.training { display: grid; gap: 8px; margin-top: 22px; }.training span { color: var(--ink-muted); }.log-table { border-radius: 12px; }
@media (max-width: 720px) { .metric-grid { grid-template-columns: 1fr; } }
</style>

