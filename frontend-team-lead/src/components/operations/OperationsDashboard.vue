<script setup lang="ts">
import { computed, onMounted, shallowRef } from 'vue'
import { CircleCheckFilled, Clock, Opportunity, Promotion, WarningFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import { api } from '@/api/client'

import TopicVisualization from './TopicVisualization.vue'
import TrainingGuide from './TrainingGuide.vue'
import type { TrainingRun } from './TrainingGuide.vue'

interface Topic { term: string; count: number; score: number }
interface HeatCell { date: string; count: number }
interface Log { message_id: string; question: string; answer: string; intent?: string; fallback: boolean; latency_ms?: number; created_at: string }
interface Feedback { id: string; message_id: string; rating: string; correction?: string; created_at: string }
interface Ticket { id: string; product_model?: string; summary: string; priority: string; status: string; created_at: string }
interface Audit { id: string; event_type: string; payload: Record<string, unknown>; created_at: string }

const topics = shallowRef<Topic[]>([])
const heatmap = shallowRef<HeatCell[]>([])
const logs = shallowRef<Log[]>([])
const feedback = shallowRef<Feedback[]>([])
const tickets = shallowRef<Ticket[]>([])
const audit = shallowRef<Audit[]>([])
const trainingRuns = shallowRef<TrainingRun[]>([])
const busy = shallowRef(false)
const query = shallowRef('')
const windowName = shallowRef<'day' | 'week' | 'month'>('week')
const rating = shallowRef('')
const filteredLogs = computed(() => logs.value.filter((item) => !query.value || `${item.question} ${item.answer} ${item.intent}`.toLowerCase().includes(query.value.toLowerCase())))
const filteredFeedback = computed(() => feedback.value.filter((item) => !rating.value || item.rating === rating.value))
const groundedRate = computed(() => logs.value.length ? Math.round(logs.value.filter((item) => !item.fallback).length / logs.value.length * 100) : 0)
const helpfulRate = computed(() => feedback.value.length ? Math.round(feedback.value.filter((item) => item.rating === 'up').length / feedback.value.length * 100) : 0)
const openTickets = computed(() => tickets.value.filter((item) => !['resolved', 'closed'].includes(item.status)).length)
const averageLatency = computed(() => { const values = logs.value.map((item) => item.latency_ms).filter((value): value is number => typeof value === 'number'); return values.length ? Math.round(values.reduce((sum, value) => sum + value, 0) / values.length) : 0 })
const intentLabels: Record<string, string> = { knowledge_query: '产品知识', human_transfer: '人工服务', order_query: '订单物流', troubleshooting: '故障排查' }
const priorityMeta: Record<string, { label: string; type: 'info'|'primary'|'warning'|'danger'; icon: typeof Clock }> = {
  low: { label: '低优先级', type: 'info', icon: Clock }, normal: { label: '普通', type: 'primary', icon: Opportunity }, high: { label: '优先处理', type: 'warning', icon: Promotion }, urgent: { label: '紧急', type: 'danger', icon: WarningFilled },
}
const statusMeta: Record<string, { label: string; type: 'info'|'primary'|'warning'|'success'; icon: typeof Clock }> = {
  open: { label: '待处理', type: 'warning', icon: Clock }, in_progress: { label: '处理中', type: 'primary', icon: Promotion }, resolved: { label: '已解决', type: 'success', icon: CircleCheckFilled }, closed: { label: '已关闭', type: 'info', icon: CircleCheckFilled },
}

async function load(): Promise<void> {
  const [topicResult, logResult, feedbackResult, ticketResult, auditResult, trainingResult] = await Promise.all([
    api.get(`/operations/hot-topics?window=${windowName.value}`), api.get('/operations/logs'), api.get('/operations/feedback'),
    api.get('/tickets'), api.get('/operations/audit'), api.get('/recommendation/training-runs'),
  ])
  topics.value = topicResult.data.items; heatmap.value = topicResult.data.heatmap ?? []; logs.value = logResult.data; feedback.value = feedbackResult.data
  tickets.value = ticketResult.data; audit.value = auditResult.data; trainingRuns.value = trainingResult.data
}

async function loadTopics(): Promise<void> {
  const result = await api.get(`/operations/hot-topics?window=${windowName.value}`)
  topics.value = result.data.items; heatmap.value = result.data.heatmap ?? []
}

async function train(target: 'balanced' | 'precision' | 'recall'): Promise<void> {
  busy.value = true
  try {
    const result = await api.post('/recommendation/training-runs', { target })
    if (result.data.changed) ElMessage.success('推荐模型训练完成，已生成新的评估版本')
    else ElMessage.info('咨询数据没有变化，已沿用当前模型和指标')
    await load()
  } finally { busy.value = false }
}

async function updateTicket(ticket: Ticket, field: 'status' | 'priority', value: string): Promise<void> {
  await api.patch(`/tickets/${ticket.id}`, { [field]: value })
  ElMessage.success('工单状态已更新')
  await load()
}

function formatDate(value: string): string { return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value)) }
onMounted(load)
</script>

<template>
  <div class="operations-dashboard">
    <section class="ops-kpis"><article><span>可信回答率</span><strong>{{ groundedRate }}%</strong><small>{{ logs.length }} 次已记录咨询</small></article><article><span>用户认可率</span><strong>{{ helpfulRate }}%</strong><small>{{ feedback.length }} 条显式反馈</small></article><article><span>待处理工单</span><strong>{{ openTickets }}</strong><small>需要人工协同的问题</small></article><article><span>平均响应时间</span><strong>{{ averageLatency }}<em>ms</em></strong><small>已完成回答统计</small></article></section>
    <div class="toolbar"><div><b>洞察周期</b><span>切换后同步更新词云与热力图</span></div><el-segmented v-model="windowName" :options="[{ label: '今日', value: 'day' }, { label: '本周', value: 'week' }, { label: '本月', value: 'month' }]" @change="loadTopics" /></div>
    <TopicVisualization :topics="topics" :heatmap="heatmap" />
    <TrainingGuide :runs="trainingRuns" :busy="busy" @train="train" />
    <el-tabs class="data-tabs">
      <el-tab-pane label="对话日志">
        <el-input v-model="query" clearable placeholder="搜索问题、回答或咨询类型…" class="table-filter" aria-label="筛选对话日志" />
        <el-table :data="filteredLogs" empty-text="暂无对话日志"><el-table-column prop="question" label="用户问题" min-width="180" /><el-table-column prop="answer" label="机器人回答" min-width="240" show-overflow-tooltip /><el-table-column label="咨询类型" width="120"><template #default="scope"><el-tag round>{{ intentLabels[scope.row.intent] ?? '其他咨询' }}</el-tag></template></el-table-column><el-table-column label="回答状态" width="110"><template #default="scope"><el-tag :type="scope.row.fallback ? 'warning' : 'success'" round>{{ scope.row.fallback ? '已兜底' : '有依据' }}</el-tag></template></el-table-column><el-table-column prop="latency_ms" label="耗时（毫秒）" width="120" /></el-table>
      </el-tab-pane>
      <el-tab-pane label="回答反馈">
        <el-select v-model="rating" clearable placeholder="全部评价" class="table-filter" aria-label="筛选回答评价"><el-option label="👍 有帮助" value="up" /><el-option label="💡 需改进" value="down" /></el-select>
        <el-table :data="filteredFeedback" empty-text="暂无回答反馈"><el-table-column label="评价" width="130"><template #default="scope"><el-tag :type="scope.row.rating === 'up' ? 'success' : 'warning'" effect="light" round><CircleCheckFilled v-if="scope.row.rating === 'up'" class="tag-icon" /><WarningFilled v-else class="tag-icon" />{{ scope.row.rating === 'up' ? '有帮助' : '需改进' }}</el-tag></template></el-table-column><el-table-column prop="correction" label="改进建议" min-width="300"><template #default="scope">{{ scope.row.correction || '用户未填写文字建议' }}</template></el-table-column><el-table-column label="提交时间" min-width="180"><template #default="scope">{{ formatDate(scope.row.created_at) }}</template></el-table-column></el-table>
      </el-tab-pane>
      <el-tab-pane label="人工工单">
        <el-table :data="tickets" empty-text="暂无人工工单"><el-table-column prop="product_model" label="相关型号" width="140"><template #default="scope">{{ scope.row.product_model || '未识别型号' }}</template></el-table-column><el-table-column prop="summary" label="对话摘要" min-width="300" show-overflow-tooltip /><el-table-column label="优先级" width="170"><template #default="scope"><el-select :model-value="scope.row.priority" @change="updateTicket(scope.row as Ticket, 'priority', $event)"><el-option v-for="(meta,key) in priorityMeta" :key="key" :label="meta.label" :value="key"><el-tag :type="meta.type" round><component :is="meta.icon" class="tag-icon" />{{ meta.label }}</el-tag></el-option></el-select></template></el-table-column><el-table-column label="处理状态" width="180"><template #default="scope"><el-select :model-value="scope.row.status" @change="updateTicket(scope.row as Ticket, 'status', $event)"><el-option v-for="(meta,key) in statusMeta" :key="key" :label="meta.label" :value="key"><el-tag :type="meta.type" round><component :is="meta.icon" class="tag-icon" />{{ meta.label }}</el-tag></el-option></el-select></template></el-table-column></el-table>
      </el-tab-pane>
      <el-tab-pane label="安全审计">
        <el-table :data="audit" empty-text="暂无安全审计事件"><el-table-column prop="event_type" label="事件" width="190" /><el-table-column label="脱敏载荷" min-width="300"><template #default="scope"><code>{{ JSON.stringify(scope.row.payload) }}</code></template></el-table-column><el-table-column label="发生时间" min-width="180"><template #default="scope">{{ formatDate(scope.row.created_at) }}</template></el-table-column></el-table>
      </el-tab-pane>
      <el-tab-pane label="训练历史">
        <el-table :data="trainingRuns" empty-text="暂无训练版本"><el-table-column prop="version" label="模型版本" min-width="210" /><el-table-column label="优化目标" width="120"><template #default="scope">{{ { balanced:'均衡推荐', precision:'优先准确', recall:'扩大召回' }[scope.row.target as string] ?? '均衡推荐' }}</template></el-table-column><el-table-column label="准确率" width="110"><template #default="scope">{{ scope.row.precision_at_k == null ? '—' : `${Math.round(scope.row.precision_at_k * 100)}%` }}</template></el-table-column><el-table-column label="召回率" width="110"><template #default="scope">{{ scope.row.recall_at_k == null ? '—' : `${Math.round(scope.row.recall_at_k * 100)}%` }}</template></el-table-column><el-table-column prop="artifact_filename" label="模型产物" min-width="210" /></el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.operations-dashboard{display:grid;gap:16px}.ops-kpis{display:grid;gap:10px;grid-template-columns:repeat(4,1fr)}.ops-kpis article{background:#fff;border:1px solid var(--line);border-radius:15px;padding:16px}.ops-kpis span,.ops-kpis small{display:block}.ops-kpis span{color:var(--ink-muted);font-size:10px;font-weight:650}.ops-kpis strong{display:block;font-size:30px;letter-spacing:-.04em;margin:7px 0}.ops-kpis strong em{color:var(--ink-muted);font-size:11px;font-style:normal;margin-left:3px}.ops-kpis small{color:#aaa6a0;font-size:9px}.ops-kpis article:first-child{background:#1d1c1a;color:white}.ops-kpis article:first-child strong{color:#69d69e}.toolbar{align-items:center;background:#fff;border:1px solid var(--line);border-radius:14px;display:flex;justify-content:space-between;padding:12px 14px}.toolbar b,.toolbar span{display:block}.toolbar b{font-size:13px}.toolbar span{color:var(--ink-muted);font-size:10px;margin-top:2px}.data-tabs{background:#fff;border:1px solid var(--line);border-radius:18px;padding:10px 18px 18px}.table-filter{margin-bottom:14px;max-width:360px}.tag-icon{height:13px;margin-right:4px;vertical-align:-2px;width:13px}code{white-space:pre-wrap;word-break:break-word}
@media(max-width:900px){.ops-kpis{grid-template-columns:1fr 1fr}}@media(max-width:680px){.ops-kpis{grid-template-columns:1fr 1fr}.toolbar{align-items:stretch;flex-direction:column;gap:10px}}
</style>
<style scoped>
.ops-kpis article:first-child{background:#fff7f0;border-color:#ffd9bd;color:var(--ink)}.ops-kpis article:first-child strong{color:var(--mi-orange)}
</style>
