<script setup lang="ts">
import { onMounted, reactive, ref, shallowRef } from 'vue'
import { ElMessage } from 'element-plus'

import { api } from '@/api/client'
import { ChatStreamError, streamChat } from '@/api/chat'
import ChatComposer from '@/components/chat/ChatComposer.vue'
import ChatMessage from '@/components/chat/ChatMessage.vue'
import FeedbackDrawer from '@/components/chat/FeedbackDrawer.vue'
import ProfileDrawer from '@/components/chat/ProfileDrawer.vue'
import type { AiTraceStep, ChatMessage as Message, KnowledgeBase, Source } from '@/types'

const STORAGE_KEY = 'xmcs_last_conversation'
const knowledgeBases = shallowRef<KnowledgeBase[]>([])
const knowledgeBaseId = shallowRef('')
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
let controller: AbortController | null = null
let activeRunId: string | undefined

function classifyError(reason: unknown): string {
  if (!navigator.onLine) return '网络已断开，请恢复网络后重试'
  if (reason instanceof Error && /timeout/i.test(reason.message)) return '回答超时，请缩短问题后重试'
  return reason instanceof Error ? reason.message : '回答生成失败，请重试'
}

async function restoreConversation(id: string): Promise<void> {
  try {
    const response = await api.get<{ knowledge_base_id: string; messages: Message[] }>(`/conversations/${id}`)
    if (!knowledgeBases.value.some((item) => item.id === response.data.knowledge_base_id)) return
    conversationId.value = id
    knowledgeBaseId.value = response.data.knowledge_base_id
    messages.value = response.data.messages
  } catch {
    localStorage.removeItem(STORAGE_KEY)
  }
}

async function loadInsights(): Promise<void> {
  if (!knowledgeBaseId.value) return
  const [profileResult, recommendationResult] = await Promise.all([
    api.get('/operations/profile/me'),
    api.get('/recommendations', { params: { knowledge_base_id: knowledgeBaseId.value } }),
  ])
  profile.value = profileResult.data
  recommendations.value = recommendationResult.data.items
  coldStart.value = recommendationResult.data.cold_start
}

onMounted(async () => {
  try {
    const response = await api.get<{ items: KnowledgeBase[] }>('/knowledge-bases')
    knowledgeBases.value = response.data.items.filter((item) => item.status === 'active')
    knowledgeBaseId.value = knowledgeBases.value[0]?.id ?? ''
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) await restoreConversation(saved)
    await loadInsights()
  } catch (reason) { error.value = classifyError(reason) }
})

async function send(message: string): Promise<void> {
  if (!knowledgeBaseId.value || busy.value) return
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
    onDone: (data: { fallback: boolean; transfer_suggested: boolean }) => {
      assistant.fallback = data.fallback; assistant.transfer_suggested = data.transfer_suggested
    },
    onError: (data: { message: string }) => { error.value = data.message || '回答生成失败' },
  }
  try {
    try {
      await streamChat(
        { knowledge_base_id: knowledgeBaseId.value, conversation_id: conversationId.value, message },
        handlers,
        controller.signal,
      )
    } catch (reason) {
      if (!(reason instanceof ChatStreamError && reason.code === 'conversation_knowledge_mismatch')) throw reason
      conversationId.value = undefined
      localStorage.removeItem(STORAGE_KEY)
      await streamChat(
        { knowledge_base_id: knowledgeBaseId.value, message },
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
    <header class="page-heading"><div><span>GROUNDED CONVERSATION ✦</span><h1>你好，今天想了解什么？</h1><p>从具体型号、使用问题或售后需求开始，每个产品事实都有官方依据。</p></div><div class="chat-controls"><el-select v-model="knowledgeBaseId" placeholder="选择知识库" style="width: 220px" @change="changeKnowledgeBase"><el-option v-for="item in knowledgeBases" :key="item.id" :label="item.name" :value="item.id" /></el-select><el-button @click="clearConversation">开启新对话</el-button></div></header>
    <el-alert v-if="error" :title="error" type="error" show-icon closable @close="error = ''" />
    <aside class="insight-strip">
      <div><b>{{ coldStart ? '热门推荐' : '为你推荐' }}</b><button v-for="item in recommendations.slice(0, 4)" :key="item.product_model" type="button" @click="send(`${item.product_model} 有哪些主要特点？`)">{{ item.product_model }} · {{ item.reason }}</button></div>
      <el-button @click="profileOpen = true">我的咨询画像</el-button>
    </aside>
    <div v-if="!messages.length" class="chat-empty"><strong>从一个具体型号开始</strong><p>例如：“小米 14 支持多少瓦快充？”</p></div>
    <div class="message-list">
      <ChatMessage v-for="(message, index) in messages" :key="message.id" :message="message" :ticket-status="ticketStatus" :feedback-rating="feedbackRatings[message.id]" :is-typing="busy && index === messages.length - 1 && message.role === 'assistant'" @feedback="feedback" @create-ticket="createTicket" />
      <div ref="scrollAnchor" style="height: 1px;"></div>
    </div>
    <ChatComposer :busy="busy" :disabled="!knowledgeBaseId" @send="send" @stop="stopGeneration" />
    <ProfileDrawer :open="profileOpen" :profile="profile" @close="profileOpen = false" @clear="clearProfile" />
    <FeedbackDrawer :open="feedbackOpen" :loading="feedbackBusy" @close="feedbackOpen = false" @submit="submitCorrection" />
  </section>
</template>

<style scoped>
.chat-page { margin: 0 auto; max-width: 980px; }.page-heading { align-items: end; display: flex; justify-content: space-between; margin-bottom: 28px; }.page-heading span { background: linear-gradient(90deg,#684bd8,#d45db4); background-clip: text; color: transparent; font-family: var(--font-mono); font-size: 11px; letter-spacing: .16em; }.page-heading h1 { font-size: clamp(32px,4vw,46px); letter-spacing: -.045em; margin: 9px 0; }.page-heading p { color: var(--ink-muted); margin: 0; max-width: 620px; }.chat-controls { display: flex; gap: 8px; }.chat-empty { background: radial-gradient(circle at 50% 0,rgba(176,139,255,.2),transparent 55%),rgba(255,255,255,.68); border: 1px dashed #cfc3ee; border-radius: 22px; color: var(--ink-muted); margin: 44px 0; padding: 54px; text-align: center; }.chat-empty strong { color: var(--ink); display: block; font-size: 20px; }.message-list { min-height: 260px; }
.insight-strip { align-items: center; background: rgba(255,255,255,.72); border: 1px solid #e4def1; border-radius: 18px; box-shadow: 0 16px 36px rgba(67,48,119,.06); display: flex; gap: 14px; justify-content: space-between; margin: 14px 0; padding: 13px 15px; backdrop-filter: blur(14px); }.insight-strip div { align-items: center; display: flex; flex-wrap: wrap; gap: 8px; }.insight-strip b { color: #6048b9; }.insight-strip button { background: linear-gradient(135deg,#eee9ff,#fcecff); border: 1px solid #e0d6fa; border-radius: 999px; color: #654db7; cursor: pointer; padding: 7px 11px; transition: transform .18s ease,box-shadow .18s ease; }.insight-strip button:hover { box-shadow: 0 8px 18px rgba(107,75,195,.14); transform: translateY(-2px); }
@media (max-width: 760px) { .page-heading { align-items: start; flex-direction: column; gap: 18px; } }
@media (prefers-reduced-motion: reduce) { .insight-strip button { transition: none; } }
</style>
