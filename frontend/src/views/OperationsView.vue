<script setup lang="ts">
import OperationsDashboard from '@/components/operations/OperationsDashboard.vue'
</script>

<template>
  <section>
    <header class="operations-heading"><div><span>SERVICE OPERATIONS CENTER</span><h1>让每一次咨询都形成改进信号</h1><p>统一查看可信回答率、用户反馈、热点趋势、人工工单、安全审计与推荐模型评估。</p></div><aside><b>运营闭环</b><span>服务使用 → 反馈收集 → 缺口识别 → 知识补齐</span></aside></header>
    <OperationsDashboard />
  </section>
</template>

<style scoped>
.operations-heading{align-items:flex-end;display:flex;justify-content:space-between;margin-bottom:24px}.operations-heading>div{max-width:760px}.operations-heading>div>span{color:var(--mi-orange);font-family:var(--font-mono);font-size:10px;font-weight:700;letter-spacing:.16em}.operations-heading h1{font-size:clamp(36px,5vw,54px);letter-spacing:-.05em;margin:8px 0}.operations-heading p{color:var(--ink-muted);line-height:1.65;margin:0}.operations-heading aside{background:#1d1c1a;border-radius:14px;color:white;display:grid;gap:4px;max-width:280px;padding:13px 15px}.operations-heading aside b{font-size:12px}.operations-heading aside span{color:#999590;font-size:9px}@media(max-width:850px){.operations-heading{align-items:flex-start;flex-direction:column;gap:14px}.operations-heading aside{max-width:none;width:100%}}
</style>
<style scoped>
.operations-heading aside{background:#fff;border:1px solid var(--line);box-shadow:var(--shadow-sm);color:var(--ink)}.operations-heading aside span{color:var(--ink-muted)}
</style>
