<script setup lang="ts">
import * as echarts from 'echarts/core'
import { GraphChart } from 'echarts/charts'
import { LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { nextTick, onBeforeUnmount, shallowRef, ref, useTemplateRef, watch } from 'vue'
import { Collection, Connection, Document, Finished } from '@element-plus/icons-vue'

import { api } from '@/api/client'

echarts.use([GraphChart, LegendComponent, TooltipComponent, CanvasRenderer])

interface Analytics {
  document_count: number
  chunk_count: number
  product_count: number
  ready_count: number
  failed_count: number
  source_coverage: number
  categories: { name: string; count: number }[]
}
interface GraphNode { id: string; label: string; kind: string; value: number; category?: string }
interface GraphEdge { source: string; target: string; relation: string }

const props = defineProps<{ knowledgeBaseId: string }>()
const analytics = shallowRef<Analytics>()
const graph = shallowRef<{ nodes: GraphNode[]; edges: GraphEdge[] }>({ nodes: [], edges: [] })
const loading = shallowRef(false)
const docCount = ref(0)
const chunkCount = ref(0)
const prodCount = ref(0)
const covPercent = ref(0)

function startCountUp(target: import('vue').Ref<number>, endValue: number) {
  const startTime = performance.now()
  const duration = 1500
  function update(time: number) {
    const progress = Math.min((time - startTime) / duration, 1)
    const easeOut = 1 - Math.pow(1 - progress, 3)
    target.value = Math.floor(endValue * easeOut)
    if (progress < 1) requestAnimationFrame(update)
  }
  requestAnimationFrame(update)
}
const chartElement = useTemplateRef<HTMLDivElement>('chart')
let chartInstance: echarts.ECharts | undefined
let resizeObserver: ResizeObserver | undefined
const colors: Record<string, string> = {
  knowledge_base: '#704fe8', category: '#3e9be8', product: '#e75ab0', document: '#ff9b5a',
}

function renderGraph(): void {
  if (!chartElement.value) return
  chartInstance ??= echarts.init(chartElement.value)
  const categories = ['knowledge_base', 'category', 'product', 'document'].map((name) => ({ name }))
  chartInstance.setOption({
    backgroundColor: 'transparent',
    tooltip: { formatter: (item: { data?: { name?: string; relation?: string } }) => item.data?.relation ?? item.data?.name ?? '' },
    legend: [{ bottom: 4, data: ['知识库', '品类', '产品', '文档'] }],
    animationDuration: 2000,
    animationEasingUpdate: 'quinticInOut',
    series: [{
      type: 'graph', layout: 'force', roam: true, draggable: true,
      force: { repulsion: 180, edgeLength: [70, 150], gravity: 0.08, layoutAnimation: true },
      categories,
      data: graph.value.nodes.map((node) => ({
        id: node.id, name: node.label, value: node.value,
        category: ['knowledge_base', 'category', 'product', 'document'].indexOf(node.kind),
        symbolSize: node.kind === 'knowledge_base' ? 62 : node.kind === 'category' ? 46 : node.kind === 'product' ? 35 : 20,
        itemStyle: { color: colors[node.kind] ?? '#8c86a5' },
        label: { show: node.kind !== 'document', color: '#2b2445', fontSize: 11 },
      })),
      links: graph.value.edges.map((edge) => ({ source: edge.source, target: edge.target, relation: edge.relation })),
      lineStyle: { color: '#bcb2de', curveness: .08, opacity: .7 },
      emphasis: { focus: 'adjacency', lineStyle: { width: 2.5, opacity: 1 } },
    }],
  })
  if (!resizeObserver && typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => chartInstance?.resize())
    resizeObserver.observe(chartElement.value)
  }
}

async function load(): Promise<void> {
  if (!props.knowledgeBaseId) { analytics.value = undefined; graph.value = { nodes: [], edges: [] }; return }
  loading.value = true
  try {
    const [analyticsResult, graphResult] = await Promise.all([
      api.get(`/knowledge-bases/${props.knowledgeBaseId}/analytics`),
      api.get(`/knowledge-bases/${props.knowledgeBaseId}/graph`),
    ])
    analytics.value = analyticsResult.data
    startCountUp(docCount, analytics.value?.document_count ?? 0)
    startCountUp(chunkCount, analytics.value?.chunk_count ?? 0)
    startCountUp(prodCount, analytics.value?.product_count ?? 0)
    startCountUp(covPercent, Math.round((analytics.value?.source_coverage ?? 0) * 100))

    graph.value = graphResult.data
    await nextTick()
    renderGraph()
  } finally { loading.value = false }
}

watch(() => props.knowledgeBaseId, () => void load(), { immediate: true })
onBeforeUnmount(() => { resizeObserver?.disconnect(); chartInstance?.dispose() })
</script>

<template>
  <section v-loading="loading" class="knowledge-analytics">
    <div class="analytics-heading"><div><span>KNOWLEDGE CONSTELLATION</span><h2>知识生态图谱</h2><p>把文档、产品和品类之间的关系变成可探索的知识网络。</p></div><div class="legend"><i />拖动节点 · 滚轮缩放 · 悬停查看关系</div></div>
    <div v-if="analytics" class="stat-grid">
      <article><Document /><div><strong>{{ docCount }}</strong><span>官方文档</span></div></article>
      <article><Connection /><div><strong>{{ chunkCount }}</strong><span>知识片段</span></div></article>
      <article><Collection /><div><strong>{{ prodCount }}</strong><span>覆盖产品</span></div></article>
      <article><Finished /><div><strong>{{ covPercent }}%</strong><span>来源完整度</span></div></article>
    </div>
    <div class="visual-grid">
      <div ref="chart" data-testid="knowledge-graph" class="graph-canvas" role="img" aria-label="知识库、品类、产品与文档关系图" />
      <aside class="category-panel"><h3>品类覆盖</h3><div v-for="item in analytics?.categories ?? []" :key="item.name"><span>{{ item.name }}</span><b>{{ item.count }} 个产品</b></div><el-empty v-if="!analytics?.categories.length" description="入库后显示品类关系" :image-size="72" /></aside>
    </div>
  </section>
</template>

<style scoped>
.knowledge-analytics { background: radial-gradient(circle at 85% 0, rgba(177,141,255,.28), transparent 34%), linear-gradient(135deg, rgba(255,255,255,.9), rgba(244,241,255,.88)); border: 1px solid #e5def8; border-radius: 24px; box-shadow: 0 24px 60px rgba(67,48,130,.09); margin-bottom: 20px; overflow: hidden; padding: 24px; }.analytics-heading { align-items: end; display: flex; justify-content: space-between; }.analytics-heading > div > span { color: #795de1; font-family: var(--font-mono); font-size: 10px; letter-spacing: .14em; }.analytics-heading h2 { font-size: 25px; margin: 6px 0; }.analytics-heading p { color: var(--ink-muted); margin: 0; }.legend { color: var(--ink-muted); font-size: 12px; }.legend i { background: #8e70ef; border-radius: 50%; display: inline-block; height: 7px; margin-right: 6px; width: 7px; }.stat-grid { display: grid; gap: 12px; grid-template-columns: repeat(4,1fr); margin: 20px 0 12px; }.stat-grid article { align-items: center; background: rgba(255,255,255,.72); border: 1px solid #ebe6fa; border-radius: 16px; display: flex; gap: 12px; padding: 15px; }.stat-grid svg { color: #7659df; height: 23px; width: 23px; }.stat-grid strong { display: block; font-size: 24px; font-variant-numeric: tabular-nums; }.stat-grid span { color: var(--ink-muted); font-size: 11px; }.visual-grid { display: grid; gap: 14px; grid-template-columns: minmax(0,1fr) 220px; }.graph-canvas { background: rgba(255,255,255,.6); border: 1px solid #e9e4f7; border-radius: 18px; height: 390px; min-width: 0; }.category-panel { background: rgba(255,255,255,.72); border: 1px solid #e9e4f7; border-radius: 18px; padding: 16px; }.category-panel h3 { font-size: 14px; margin: 0 0 14px; }.category-panel > div { border-bottom: 1px solid #eeeaf8; display: flex; justify-content: space-between; padding: 10px 0; }.category-panel span { font-size: 13px; }.category-panel b { color: #7159c8; font-size: 11px; }
@media(max-width:800px){.analytics-heading{align-items:start;flex-direction:column;gap:10px}.stat-grid{grid-template-columns:1fr 1fr}.visual-grid{grid-template-columns:1fr}.category-panel{display:none}.graph-canvas{height:330px}}
</style>
