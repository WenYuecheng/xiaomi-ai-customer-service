<script setup lang="ts">
import * as echarts from 'echarts/core'
import { HeatmapChart } from 'echarts/charts'
import { CalendarComponent, TooltipComponent, VisualMapComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { computed, nextTick, onBeforeUnmount, useTemplateRef, watch } from 'vue'

interface Topic { term: string; count: number; score: number }
interface HeatCell { date: string; count: number }
const props = defineProps<{ topics: Topic[]; heatmap: HeatCell[] }>()
echarts.use([HeatmapChart, CalendarComponent, TooltipComponent, VisualMapComponent, CanvasRenderer])
const chartElement = useTemplateRef<HTMLDivElement>('heatmap')
let chart: echarts.ECharts | undefined
let observer: ResizeObserver | undefined
const maximum = computed(() => Math.max(...props.topics.map((item) => item.score), 1))
const fontSize = (score: number): string => `${12 + Math.round(score / maximum.value * 18)}px`

async function render(): Promise<void> {
  await nextTick()
  if (!chartElement.value) return
  chart ??= echarts.init(chartElement.value)
  const dates = props.heatmap.map((item) => item.date)
  const range = dates.length ? [dates[0], dates[dates.length - 1]] : undefined
  chart.setOption({
    tooltip: { formatter: (item: { value: [string, number] }) => `${item.value[0]}：${item.value[1]} 次咨询` },
    visualMap: { min: 0, max: Math.max(...props.heatmap.map((item) => item.count), 1), orient: 'horizontal', left: 'center', bottom: 0, inRange: { color: ['#fff0e5','#ffac70','#ff6900'] }, text: ['多','少'], textStyle: { color: '#77736f' } },
    calendar: { top: 20, left: 35, right: 20, bottom: 45, range, cellSize: ['auto', 20], itemStyle: { borderWidth: 4, borderColor: '#fff', borderRadius: 5 }, yearLabel: { show: false }, dayLabel: { firstDay: 1, nameMap: 'ZH' }, monthLabel: { nameMap: 'ZH' } },
    animationDuration: 1500,
    animationEasing: 'quinticInOut',
    series: [{ type: 'heatmap', coordinateSystem: 'calendar', data: props.heatmap.map((item) => [item.date, item.count]) }],
  }, true)
  if (!observer && typeof ResizeObserver !== 'undefined') { observer = new ResizeObserver(() => chart?.resize()); observer.observe(chartElement.value) }
}
watch(() => [props.topics, props.heatmap], () => void render(), { immediate: true, deep: true })
onBeforeUnmount(() => { observer?.disconnect(); chart?.dispose() })
</script>

<template>
  <section class="topic-visualization">
    <div class="visual-title"><div><span>CONVERSATION PULSE</span><h2>用户正在关注什么</h2></div><p>字号代表热度，颜色区分主题；下方显示咨询活跃日期。</p></div>
    <div class="topic-cloud" aria-label="咨询热词云"><span v-for="(topic,index) in topics" :key="topic.term" :class="`tone-${index % 5}`" :style="{ fontSize: fontSize(topic.score) }">{{ topic.term }}<small>{{ topic.count }}</small></span><el-empty v-if="!topics.length" description="产生咨询后显示热词" :image-size="70" /></div>
    <div ref="heatmap" class="heatmap" role="img" aria-label="按日期统计的咨询热力图" />
  </section>
</template>

<style scoped>
.topic-visualization{background:#fff;border:1px solid var(--line);border-radius:18px;padding:22px}.visual-title{align-items:flex-end;display:flex;justify-content:space-between}.visual-title span{color:var(--mi-orange);font-family:var(--font-mono);font-size:10px;font-weight:700;letter-spacing:.13em}.visual-title h2{font-size:22px;margin:6px 0 0}.visual-title p{color:var(--ink-muted);font-size:11px;margin:0}.topic-cloud{align-items:center;background:#faf9f7;border-radius:14px;display:flex;flex-wrap:wrap;gap:10px 15px;justify-content:center;margin-top:16px;min-height:170px;padding:20px 8px}.topic-cloud>span{cursor:default;font-weight:720;line-height:1;transition:opacity .18s ease,transform .18s ease}.topic-cloud>span:hover{opacity:.72;transform:scale(1.06)}.topic-cloud small{font-size:9px;margin-left:4px;opacity:.5}.tone-0{color:#d95a06}.tone-1{color:#202020}.tone-2{color:#247fbd}.tone-3{color:#b78218}.tone-4{color:#338f75}.heatmap{height:170px;width:100%}
@media(max-width:700px){.visual-title{align-items:start;flex-direction:column;gap:8px}.heatmap{height:190px}}
@media(prefers-reduced-motion:reduce){.topic-cloud>span{transition:none}}
</style>
