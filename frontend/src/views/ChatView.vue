<script setup lang="ts">
import { onMounted, ref, shallowRef } from 'vue'

import { api } from '@/api/client'
import { streamChat } from '@/api/chat'
import ChatComposer from '@/components/chat/ChatComposer.vue'
import ChatMessage from '@/components/chat/ChatMessage.vue'
import type { ChatMessage as Message, KnowledgeBase, Source } from '@/types'

const knowledgeBases = ref<KnowledgeBase[]>([])
const knowledgeBaseId = shallowRef('')
const conversationId = shallowRef<string>()
const messages = ref<Message[]>([])
const busy = shallowRef(false)
const error = shallowRef('')
let controller: AbortController | null = null

onMounted(async () => {
  try {
    const response = await api.get<{ items: KnowledgeBase[] }>('/knowledge-bases')
    knowledgeBases.value = response.data.items
    knowledgeBaseId.value = knowledgeBases.value[0]?.id ?? ''
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '知识库加载失败'
  }
})

async function send(message: string): Promise<void> {
  if (!knowledgeBaseId.value) return
  error.value = ''
  busy.value = true
  controller = new AbortController()
  messages.value.push({ id: crypto.randomUUID(), role: 'user', content: message, fallback: false, sources: [] })
  const assistant: Message = { id: crypto.randomUUID(), role: 'assistant', content: '', fallback: false, sources: [] }
  messages.value.push(assistant)
  try {
    await streamChat(
      { knowledge_base_id: knowledgeBaseId.value, conversation_id: conversationId.value, message },
      {
        onMeta: (data) => { conversationId.value = data.conversation_id; assistant.id = data.message_id },
        onDelta: (content) => { assistant.content += content },
        onSources: (sources: Source[]) => { assistant.sources = sources },
        onDone: (data) => { assistant.fallback = data.fallback },
      },
      controller.signal,
    )
  } catch (reason) {
    if (!(reason instanceof DOMException && reason.name === 'AbortError')) {
      error.value = reason instanceof Error ? reason.message : '回答生成失败'
    }
  } finally {
    busy.value = false
    controller = null
  }
}

async function feedback(messageId: string, rating: 'up' | 'down'): Promise<void> {
  await api.post('/chat/feedback', { message_id: messageId, rating })
}

function clearConversation(): void {
  if (conversationId.value) void api.delete(`/conversations/${conversationId.value}`)
  conversationId.value = undefined
  messages.value = []
}

function stopGeneration(): void {
  controller?.abort()
}
</script>

<template>
  <section class="chat-page">
    <header class="page-heading">
      <div><span>GROUNDED CONVERSATION</span><h1>可信问答</h1><p>答案只来自已入库资料，橙色证据轨展示实际检索片段。</p></div>
      <div class="chat-controls">
        <el-select v-model="knowledgeBaseId" placeholder="选择知识库" style="width: 220px">
          <el-option v-for="item in knowledgeBases" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <el-button @click="clearConversation">清空会话</el-button>
      </div>
    </header>
    <el-alert v-if="error" :title="error" type="error" show-icon />
    <div v-if="!messages.length" class="chat-empty">
      <strong>从一个具体型号开始</strong>
      <p>例如：“小米 14 支持多少瓦快充？”</p>
    </div>
    <div class="message-list">
      <ChatMessage v-for="message in messages" :key="message.id" :message="message" @feedback="feedback" />
    </div>
    <ChatComposer :busy="busy" :disabled="!knowledgeBaseId" @send="send" @stop="stopGeneration" />
  </section>
</template>

<style scoped>
.chat-page { margin: 0 auto; max-width: 920px; }
.page-heading { align-items: end; display: flex; justify-content: space-between; margin-bottom: 34px; }
.page-heading span { color: var(--mi-orange); font-family: var(--font-mono); font-size: 11px; letter-spacing: .16em; }
.page-heading h1 { font-size: 38px; letter-spacing: -.04em; margin: 8px 0; }
.page-heading p { color: var(--ink-muted); margin: 0; }
.chat-controls { display: flex; gap: 8px; }
.chat-empty { border: 1px dashed #cfd3da; border-radius: 14px; color: var(--ink-muted); margin: 60px 0; padding: 50px; text-align: center; }
.chat-empty strong { color: var(--ink); display: block; font-size: 19px; }
.message-list { min-height: 260px; }
@media (max-width: 760px) { .page-heading { align-items: start; flex-direction: column; gap: 18px; } }
</style>
