<script setup lang="ts">
import { nextTick, onMounted, reactive, ref, shallowRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { api } from '@/api/client'
import { ChatStreamError, streamChat } from '@/api/chat'
import ChatComposer from '@/components/chat/ChatComposer.vue'
import ChatMessage from '@/components/chat/ChatMessage.vue'
import FeedbackDrawer from '@/components/chat/FeedbackDrawer.vue'
import ProfileDrawer from '@/components/chat/ProfileDrawer.vue'
import KnowledgeBaseMultiSelect from '@/components/knowledge/KnowledgeBaseMultiSelect.vue'
import type { AdvisorPlan, AiTraceStep, ChatMessage as Message, KnowledgeBase, Source } from '@/types'

const STORAGE_KEY = 'xmcs_last_conversation'
const knowledgeBases = shallowRef<KnowledgeBase[]>([])
const knowledgeBaseIds = ref<string[]>([])
const conversationId = shallowRef<string>()
const messages = ref<Message[]>([])
const busy = shallowRef(false)
const error = shallowRef('')
const profileOpen = shallowRef(false)
const profile = shallowRef<{ product_preferences: string[]; intent_distribution: Record<string, number>; feedback_summary: Record<string, number>; event_count: number }>()
const recommendations = shallowRef<{ product_model: string; score: number; reason: string }[]>([])
const coldStart = shallowRef(true)
const ticketStatus = shallowRef<'idle' | 'creating' | 'created'>('idle')
const feedbackRatings = reactive<Record<string, 'up' | 'down'>>({})
const feedbackOpen = shallowRef(false)
const feedbackMessageId = shallowRef('')
const feedbackBusy = shallowRef(false)
const scrollAnchor = shallowRef<HTMLElement | null>(null)
const route = useRoute()
const router = useRouter()
let controller: AbortController | null = null
let activeRunId: string | undefined

function classifyError(reason: unknown): string {
  if (!navigator.onLine) return '网络已断开，请恢复网络后重试'
  if (reason instanceof Error && /timeout/i.test(reason.message)) return '回答超时，请缩短问题后重试'
  return reason instanceof Error ? reason.message : '回答生成失败，请重试'
}

async function restoreConversation(id: string): Promise<void> {
  try {
    const response = await api.get<{ knowledge_base_id: string; knowledge_base_ids?: string[]; messages: Message[] }>(`/conversations/${id}`)
    const restoredIds = response.data.knowledge_base_ids ?? [response.data.knowledge_base_id]
    if (restoredIds.some((id) => !knowledgeBases.value.some((item) => item.id === id))) return
    conversationId.value = id
    knowledgeBaseIds.value = restoredIds
    messages.value = response.data.messages
  } catch {
    localStorage.removeItem(STORAGE_KEY)
  }
}

async function loadInsights(): Promise<void> {
  if (!knowledgeBaseIds.value.length) return
  const [profileResult, recommendationResult] = await Promise.all([
    api.get('/operations/profile/me'),
    api.get('/recommendations', { params: { knowledge_base_id: knowledgeBaseIds.value[0] } }),
  ])
  profile.value = profileResult.data
  recommendations.value = recommendationResult.data.items
  coldStart.value = recommendationResult.data.cold_start
}

onMounted(async () => {
  try {
    const response = await api.get<{ items: KnowledgeBase[] }>('/knowledge-bases')
    knowledgeBases.value = response.data.items.filter((item) => item.status === 'active')
    const requested = new URLSearchParams(window.location.search).get('conversation_id')
    const saved = requested || localStorage.getItem(STORAGE_KEY)
    if (saved) await restoreConversation(saved)
    await loadInsights()
    const prompt = typeof route.query.prompt === 'string' ? route.query.prompt.trim() : ''
    if (prompt) {
      await router.replace({ name: 'chat' })
      await nextTick()
      await send(prompt)
    }
  } catch (reason) { error.value = classifyError(reason) }
})

async function send(message: string): Promise<void> {
  if (!knowledgeBaseIds.value.length || busy.value) return
  error.value = ''; busy.value = true; activeRunId = undefined
  controller = new AbortController()
  messages.value = [...messages.value, { id: crypto.randomUUID(), role: 'user', content: message, fallback: false, sources: [] }]
  const assistant: Message = { id: crypto.randomUUID(), role: 'assistant', content: '', fallback: false, sources: [], ai_trace: [] }
  messages.value = [...messages.value, assistant]
  const handlers = {
    onMeta: (data: { conversation_id: string; message_id: string; run_id: string }) => {
      conversationId.value = data.conversation_id; assistant.id = data.message_id; activeRunId = data.run_id
      localStorage.setItem(STORAGE_KEY, data.conversation_id)
    },
    onDelta: (content: string) => {
      assistant.content += content
      if (scrollAnchor.value) scrollAnchor.value.scrollIntoView({ behavior: 'smooth', block: 'end' })
    },
    onTrace: (step: AiTraceStep) => {
      const current = assistant.ai_trace ?? []
      const index = current.findIndex((item) => item.stage === step.stage)
      assistant.ai_trace = index === -1
        ? [...current, step]
        : current.map((item, itemIndex) => itemIndex === index ? step : item)
    },
    onSources: (sources: Source[]) => { assistant.sources = sources },
    onAdvisor: (data: { advisor_session_id: string; plan: AdvisorPlan }) => {
      assistant.advisor_session_id = data.advisor_session_id
      assistant.advisor_plan = data.plan
    },
    onDone: (data: { fallback: boolean; transfer_suggested: boolean }) => {
      assistant.fallback = data.fallback; assistant.transfer_suggested = data.transfer_suggested
    },
    onError: (data: { message: string }) => { error.value = data.message || '回答生成失败' },
  }
  try {
    try {
      await streamChat(
        { knowledge_base_ids: knowledgeBaseIds.value, conversation_id: conversationId.value, message },
        handlers,
        controller.signal,
      )
    } catch (reason) {
      if (!(reason instanceof ChatStreamError && reason.code === 'conversation_knowledge_mismatch')) throw reason
      conversationId.value = undefined
      localStorage.removeItem(STORAGE_KEY)
      await streamChat(
        { knowledge_base_ids: knowledgeBaseIds.value, message },
        handlers,
        controller.signal,
      )
    }
    await loadInsights()
  } catch (reason) {
    if (!(reason instanceof DOMException && reason.name === 'AbortError')) error.value = classifyError(reason)
    if (!assistant.content) messages.value = messages.value.filter((item) => item.id !== assistant.id)
  } finally { busy.value = false; controller = null; activeRunId = undefined }
}

async function changeKnowledgeBase(): Promise<void> {
  conversationId.value = undefined
  messages.value = []
  ticketStatus.value = 'idle'
  localStorage.removeItem(STORAGE_KEY)
  try { await loadInsights() } catch (reason) { error.value = classifyError(reason) }
}

async function feedback(messageId: string, rating: 'up' | 'down'): Promise<void> {
  if (rating === 'down') {
    feedbackMessageId.value = messageId
    feedbackOpen.value = true
    return
  }
  await submitFeedback(messageId, rating)
}

async function submitFeedback(messageId: string, rating: 'up' | 'down', correction?: string): Promise<void> {
  feedbackBusy.value = true
  try {
    await api.post('/chat/feedback', { message_id: messageId, rating, correction })
    feedbackRatings[messageId] = rating
    ElMessage.success(rating === 'up' ? '谢谢认可，已记录为有帮助' : '改进建议已提交')
  } finally { feedbackBusy.value = false }
}

async function submitCorrection(payload: { reason: string; correction?: string }): Promise<void> {
  const correction = payload.correction ? `${payload.reason}：${payload.correction}` : payload.reason
  await submitFeedback(feedbackMessageId.value, 'down', correction)
  feedbackOpen.value = false
}

async function createTicket(): Promise<void> {
  if (!conversationId.value || ticketStatus.value !== 'idle') return
  ticketStatus.value = 'creating'
  error.value = ''
  try {
    await api.post('/tickets', { conversation_id: conversationId.value, priority: 'high' })
    ticketStatus.value = 'created'
    ElMessage.success('人工工单已创建，运营人员可在后台查看')
  } catch (reason) {
    ticketStatus.value = 'idle'
    error.value = classifyError(reason)
  }
}

async function clearConversation(): Promise<void> {
  if (conversationId.value) await api.delete(`/conversations/${conversationId.value}`)
  conversationId.value = undefined; messages.value = []; ticketStatus.value = 'idle'; localStorage.removeItem(STORAGE_KEY)
}

async function stopGeneration(): Promise<void> {
  if (activeRunId) await api.post(`/chat/runs/${activeRunId}/cancel`).catch(() => undefined)
  controller?.abort()
}

async function clearProfile(): Promise<void> {
  await api.delete('/operations/profile/me')
  ElMessage.success('当前用户的演示画像与行为数据已清除')
  await loadInsights()
}
</script>

<template>
  <section class="chat-page">
    <header class="page-heading"><div><span>AI CUSTOMER SERVICE</span><h1>你好，需要什么帮助？</h1><p>产品参数、使用指导、选购对比与售后政策，都可以直接问我。</p></div><div class="chat-controls"><KnowledgeBaseMultiSelect v-model="knowledgeBaseIds" :items="knowledgeBases" @change="changeKnowledgeBase" /><el-button @click="clearConversation">新建对话</el-button></div></header>
    <el-alert v-if="error" :title="error" type="error" show-icon closable @close="error = ''" />
    <aside class="insight-strip">
      <div><b>{{ coldStart ? '大家都在问' : '根据你的偏好' }}</b><button v-for="item in recommendations.slice(0, 4)" :key="item.product_model" type="button" @click="send(`${item.product_model} 有哪些主要特点？`)">{{ item.product_model }}</button></div>
      <button class="profile-entry" type="button" @click="profileOpen = true">查看我的服务画像 →</button>
    </aside>
    <div class="conversation-panel">
      <div v-if="!messages.length" class="chat-empty"><div class="bot-mark">MI</div><strong>小爱客服已准备好</strong><p>回答会严格依据当前知识库，并在答案下方展示原文来源。</p><div class="quick-questions"><button type="button" @click="send('小米手机如何开启无线充电？')"><b>产品使用</b><span>小米手机如何开启无线充电？</span></button><button type="button" @click="send('扫地机器人无法开机怎么排查？')"><b>故障排查</b><span>扫地机器人无法开机怎么办？</span></button><button type="button" @click="send('介绍一下小米的售后服务政策')"><b>售后政策</b><span>退换货与维修政策是什么？</span></button></div></div>
      <div class="message-list"><ChatMessage v-for="(message, index) in messages" :key="message.id" :message="message" :ticket-status="ticketStatus" :feedback-rating="feedbackRatings[message.id]" :is-typing="busy && index === messages.length - 1 && message.role === 'assistant'" @feedback="feedback" @create-ticket="createTicket" /><div ref="scrollAnchor" style="height: 1px;"></div></div>
      <ChatComposer :busy="busy" :disabled="!knowledgeBaseIds.length" @send="send" @stop="stopGeneration" />
      <p class="answer-note">AI 回答仅供参考，重要信息请以小米官方页面与服务政策为准。</p>
    </div>
    <ProfileDrawer :open="profileOpen" :profile="profile" @close="profileOpen = false" @clear="clearProfile" />
    <FeedbackDrawer :open="feedbackOpen" :loading="feedbackBusy" @close="feedbackOpen = false" @submit="submitCorrection" />
  </section>
</template>

<style scoped>
.chat-page{margin:0 auto;max-width:1100px}.page-heading{align-items:flex-end;display:flex;justify-content:space-between;margin-bottom:24px}.page-heading>div:first-child{max-width:680px}.page-heading span{color:var(--mi-orange);font-family:var(--font-mono);font-size:10px;font-weight:700;letter-spacing:.16em}.page-heading h1{font-size:clamp(34px,4vw,52px);letter-spacing:-.05em;line-height:1.05;margin:9px 0 10px}.page-heading p{color:var(--ink-muted);font-size:15px;margin:0}.chat-controls{align-items:center;display:flex;gap:8px}.insight-strip{align-items:center;background:#fff;border:1px solid var(--line);border-radius:15px;display:flex;justify-content:space-between;margin-bottom:14px;padding:10px 12px}.insight-strip>div{align-items:center;display:flex;flex-wrap:wrap;gap:7px}.insight-strip>div>b{font-size:12px;margin:0 4px}.insight-strip>div button{background:#f7f5f2;border:1px solid #ebe7e1;border-radius:9px;color:var(--ink-soft);cursor:pointer;padding:7px 10px}.insight-strip>div button:hover{border-color:#ffc69e;color:var(--mi-orange)}.profile-entry{background:none;border:0;color:var(--ink-muted);cursor:pointer;font-size:11px;white-space:nowrap}.conversation-panel{background:#fff;border:1px solid var(--line);border-radius:20px;box-shadow:var(--shadow-sm);overflow:hidden;padding:0 22px 12px}.chat-empty{color:var(--ink-muted);padding:54px 24px 38px;text-align:center}.bot-mark{background:var(--mi-orange);border-radius:14px;box-shadow:0 10px 25px rgba(255,105,0,.22);color:#fff;display:grid;font-size:13px;font-weight:800;height:44px;margin:0 auto 15px;place-items:center;width:44px}.chat-empty>strong{color:var(--ink);display:block;font-size:20px}.chat-empty>p{font-size:13px;margin:8px auto 28px;max-width:470px}.quick-questions{display:grid;gap:9px;grid-template-columns:repeat(3,1fr);margin:0 auto;max-width:850px}.quick-questions button{background:#faf9f7;border:1px solid var(--line);border-radius:13px;cursor:pointer;padding:14px;text-align:left}.quick-questions button:hover{background:#fff8f2;border-color:#ffc89f}.quick-questions b,.quick-questions span{display:block}.quick-questions b{color:var(--mi-orange);font-size:10px;margin-bottom:6px}.quick-questions span{color:var(--ink-soft);font-size:12px}.message-list{min-height:140px}.answer-note{color:#aaa6a1;font-size:10px;margin:9px 0 0;text-align:center}@media(max-width:760px){.page-heading{align-items:flex-start;flex-direction:column;gap:18px}.chat-controls{align-items:stretch;width:100%}.profile-entry{display:none}.conversation-panel{padding:0 12px 10px}.quick-questions{grid-template-columns:1fr}.chat-empty{padding:38px 4px 24px}.page-heading h1{font-size:36px}}
</style>
