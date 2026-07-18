<script setup lang="ts">
import * as echarts from 'echarts/core'
import { RadarChart } from 'echarts/charts'
import { LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { computed, nextTick, onBeforeUnmount, onMounted, useTemplateRef, watch } from 'vue'

import type { AdvisorCandidate } from '@/types'

echarts.use([RadarChart, LegendComponent, TooltipComponent, CanvasRenderer])

const props = defineProps<{ candidates: AdvisorCandidate[] }>()
const chartElement = useTemplateRef<HTMLDivElement>('chart')
let chart: echarts.ECharts | undefined
let observer: ResizeObserver | undefined

const dimensionLabels: Record<string, string> = {
  battery: '续航', camera: '影像', performance: '性能', screen: '屏幕', portability: '便携',
  productivity: '生产力', health: '健康', sports: '运动', comfort: '舒适', connectivity: '连接',
  cleaning_power: '清洁力', navigation: '导航', obstacle_avoidance: '避障', self_cleaning: '自清洁',
  '综合匹配': '综合匹配',
}

const dimensions = computed(() => {
  const keys = new Set(props.candidates.flatMap((item) => Object.keys(item.dimension_scores)))
  return [...keys].slice(0, 6)
})

async function renderChart(): Promise<void> {
  await nextTick()
  if (!chartElement.value || dimensions.value.length < 2) return
  chart ??= echarts.init(chartElement.value)
  chart.setOption({
    color: ['#7657e8', '#ff6900', '#34a6c9', '#d94fa7'],
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, textStyle: { color: '#6d6480', fontSize: 10 } },
    radar: {
      radius: '62%', center: ['50%', '45%'], splitNumber: 4,
      indicator: dimensions.value.map((key) => ({ name: dimensionLabels[key] ?? key, max: 100 })),
      axisName: { color: '#625678', fontSize: 11 },
      splitArea: { areaStyle: { color: ['rgba(118,87,232,.03)', 'rgba(255,255,255,.52)'] } },
      splitLine: { lineStyle: { color: '#e3dcf4' } },
      axisLine: { lineStyle: { color: '#ddd4ef' } },
    },
    series: [{
      type: 'radar', symbolSize: 5,
      data: props.candidates.map((item) => ({
        name: item.model,
        value: dimensions.value.map((key) => item.dimension_scores[key] ?? 0),
        areaStyle: { opacity: .08 },
      })),
    }],
  })
}

watch(() => props.candidates, renderChart, { deep: true })
onMounted(() => {
  void renderChart()
  if (chartElement.value && typeof ResizeObserver !== 'undefined') {
    observer = new ResizeObserver(() => chart?.resize())
    observer.observe(chartElement.value)
  }
})
onBeforeUnmount(() => { observer?.disconnect(); chart?.dispose() })
</script>

<template>
  <div v-if="dimensions.length >= 2" ref="chart" class="advisor-radar" role="img" aria-label="候选产品 AI 需求匹配雷达图" />
  <div v-else class="advisor-radar advisor-radar--empty">更多维度资料入库后显示雷达图</div>
</template>

<style scoped>
.advisor-radar { height: 310px; min-width: 0; width: 100%; }
.advisor-radar--empty { align-items: center; color: #8a809e; display: flex; font-size: 12px; justify-content: center; }
</style>
