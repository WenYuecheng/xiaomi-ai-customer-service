<script setup lang="ts">
import OperationsDashboard from '@/components/operations/OperationsDashboard.vue'
</script>

<template>
  <section>
    <header class="operations-heading"><span>SERVICE SIGNALS</span><h1>运营洞察</h1><p>把咨询行为转成热词、反馈、工单、审计与可评估推荐模型。</p></header>
    <OperationsDashboard />
  </section>
</template>

<style scoped>
.operations-heading { margin-bottom: 24px; }.operations-heading span { background: linear-gradient(90deg,#6c4ddd,#d855ac); background-clip: text; color: transparent; font-family: var(--font-mono); font-size: 11px; letter-spacing: .16em; }.operations-heading h1 { font-size: 42px; margin: 8px 0; }.operations-heading p { color: var(--ink-muted); }
</style>
