<script setup lang="ts">
import { onBeforeUnmount, onMounted, useTemplateRef, watch } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([LineChart, GridComponent, TooltipComponent, CanvasRenderer])
const props = defineProps<{ points: readonly { date: string; count: number }[] }>()
const chartElement = useTemplateRef<HTMLDivElement>('chart')
let chart: echarts.ECharts | undefined

function render(): void {
  if (!chartElement.value) return
  chart ??= echarts.init(chartElement.value)
  chart.setOption({ grid:{left:24,right:16,top:24,bottom:22},tooltip:{trigger:'axis'},xAxis:{type:'category',data:props.points.map(item=>item.date.slice(5)),axisLine:{show:false},axisTick:{show:false},axisLabel:{color:'#958aa4',fontSize:9}},yAxis:{type:'value',minInterval:1,axisLine:{show:false},splitLine:{lineStyle:{color:'#eae5f2'}},axisLabel:{show:false}},series:[{type:'line',data:props.points.map(item=>item.count),smooth:true,symbolSize:7,lineStyle:{width:3,color:'#7657de'},itemStyle:{color:'#ff6900',borderColor:'#fff',borderWidth:2},areaStyle:{color:{type:'linear',x:0,y:0,x2:0,y2:1,colorStops:[{offset:0,color:'rgba(120,87,222,.3)'},{offset:1,color:'rgba(120,87,222,0)'}]}}}] })
}
function resize():void{chart?.resize()}
onMounted(()=>{render();window.addEventListener('resize',resize)})
watch(()=>props.points,render,{deep:true})
onBeforeUnmount(()=>{window.removeEventListener('resize',resize);chart?.dispose()})
</script>

<template><section class="trend-card"><header><div><span>14 DAY SIGNAL</span><h2>活跃轨迹</h2></div><p>问答、选购与反馈</p></header><div ref="chart" class="trend-chart" role="img" aria-label="最近十四天活动趋势图" /></section></template>
<style scoped>.trend-card{background:rgba(255,255,255,.82);border:1px solid #e5dff0;border-radius:24px;padding:22px}.trend-card header{align-items:flex-end;display:flex;justify-content:space-between}.trend-card span{color:#ff6900;font-family:var(--font-mono);font-size:9px;letter-spacing:.16em}.trend-card h2{font-size:23px;margin:5px 0}.trend-card p{color:#978da3;font-size:11px}.trend-chart{height:260px}</style>
