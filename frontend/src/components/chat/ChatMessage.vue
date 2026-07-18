<script setup lang="ts">
import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'
import { computed } from 'vue'
import { CircleCheckFilled, WarningFilled } from '@element-plus/icons-vue'

import type { ChatMessage as Message } from '@/types'

import AiTracePanel from './AiTracePanel.vue'
import SourceRail from './SourceRail.vue'

const props = withDefaults(defineProps<{
  message: Message
  ticketStatus?: 'idle' | 'creating' | 'created'
  feedbackRating?: 'up' | 'down'
  isTyping?: boolean
}>(), { ticketStatus: 'idle', feedbackRating: undefined, isTyping: false })
const emit = defineEmits<{
  feedback: [messageId: string, rating: 'up' | 'down']
  createTicket: [messageId: string]
}>()
const markdown = new MarkdownIt({ html: false, linkify: true, breaks: true })
const rendered = computed(() => DOMPurify.sanitize(markdown.render(props.message.content)))
</script>

<template>
  <article class="message" :class="`message--${message.role}`">
    <div class="message__identity">{{ message.role === 'assistant' ? '小爱客服' : '你' }}</div>
    <div class="message__body">
      <div v-if="message.fallback" class="message__fallback">知识库暂无可靠答案</div>
      <AiTracePanel v-if="message.role === 'assistant' && message.ai_trace?.length" :steps="message.ai_trace" />
      <div class="message__content" :class="{ 'is-typing': isTyping }" v-html="rendered" />
      <SourceRail v-if="message.sources.length" :sources="message.sources" />
      <div v-if="message.role === 'assistant'" class="message__actions">
        <button
          type="button"
          data-testid="feedback-up"
          :class="{ selected: feedbackRating === 'up' }"
          :aria-pressed="feedbackRating === 'up'"
          @click="emit('feedback', message.id, 'up')"
        ><CircleCheckFilled aria-hidden="true" />{{ feedbackRating === 'up' ? '已记录' : '有帮助' }}</button>
        <button
          type="button"
          data-testid="feedback-down"
          :class="{ selected: feedbackRating === 'down' }"
          :aria-pressed="feedbackRating === 'down'"
          @click="emit('feedback', message.id, 'down')"
        ><WarningFilled aria-hidden="true" />{{ feedbackRating === 'down' ? '已提交改进' : '需改进' }}</button>
        <button
          v-if="message.transfer_suggested"
          type="button"
          class="transfer"
          :disabled="ticketStatus !== 'idle'"
          @click="emit('createTicket', message.id)"
        >{{ ticketStatus === 'creating' ? '创建中…' : ticketStatus === 'created' ? '工单已创建' : '创建人工工单' }}</button>
      </div>
    </div>
  </article>
</template>

<style scoped>
.message { display: grid; grid-template-columns: 72px minmax(0, 1fr); gap: 14px; padding: 17px 0; }
.message__identity { color: var(--ink-muted); font-size: 12px; font-weight: 650; padding-top: 14px; }.message__identity::before { background: linear-gradient(135deg,#7050e7,#d85bb4); border-radius: 11px; color: white; content: '✦'; display: grid; height: 30px; margin-bottom: 6px; place-items: center; width: 30px; animation: avatar-glow 3s infinite alternate; }.message--user .message__identity::before { background: linear-gradient(135deg,#3d90e8,#5fc7dc); content: '你'; font-size: 11px; animation: none; }
.message__body { background: rgba(255,255,255,.65); border: 1px solid rgba(255,255,255,.4); border-radius: 5px 20px 20px 20px; box-shadow: 0 4px 12px rgba(112, 79, 232, 0.05), 0 16px 32px rgba(112, 79, 232, 0.08); backdrop-filter: blur(14px); max-width: 800px; padding: 17px 19px; }.message--user .message__body { background: linear-gradient(135deg,rgba(237,244,255,.7),rgba(242,239,255,.7)); border-color: #dbe4f7; border-radius: 20px 5px 20px 20px; margin-left: auto; max-width: 72%; }
.message__content { color: var(--ink); font-size: 15px; line-height: 1.8; }
.message__content.is-typing::after { content: ''; display: inline-block; width: 4px; height: 1em; background: var(--mi-orange); animation: blink 1s step-end infinite; vertical-align: -2px; margin-left: 4px; }
.message__content :deep(strong) { background: linear-gradient(90deg,#6b4be0,#d851a6); background-clip: text; color: transparent; font-weight: 760; }.message__content :deep(code) { background: #f0ebff; border-radius: 6px; color: #6745c6; padding: 2px 5px; }.message--user .message__content { font-size: 16px; font-weight: 580; }
.message__fallback { color: #a94712; background: #fff0e7; border-radius: 8px; display: inline-block; font-size: 12px; margin-bottom: 8px; padding: 5px 9px; }
.message__actions { display: flex; gap: 8px; margin-top: 12px; }
.message__actions button { align-items: center; background: transparent; border: 1px solid var(--line); border-radius: 999px; color: var(--ink-muted); cursor: pointer; display: inline-flex; font-size: 12px; gap: 5px; padding: 6px 11px; transition: background-color .18s ease, border-color .18s ease, color .18s ease, transform .18s ease; }
.message__actions button svg { height: 15px; width: 15px; }
.message__actions button:hover { border-color: var(--mi-orange); color: var(--mi-orange); }
.message__actions button:active { transform: scale(.94); }
.message__actions button.selected { animation: feedback-pop .34s ease-out; background: #eee9ff; border-color: #8168ee; color: #5d43c8; }
.message__actions .transfer { background: var(--mi-orange); border-color: var(--mi-orange); color: white; }
.message__actions .transfer:disabled { cursor: default; opacity: .72; }
@media (max-width: 640px) { .message { grid-template-columns: 1fr; gap: 6px; } }
@media (prefers-reduced-motion: reduce) { .message__actions button.selected { animation: none; } .message__identity::before { animation: none; } }
@keyframes feedback-pop { 50% { transform: scale(1.08); } }
@keyframes avatar-glow { from { box-shadow: 0 0 4px rgba(112,80,231,.2); } to { box-shadow: 0 0 12px rgba(216,91,180,.6); } }
@keyframes blink { 50% { opacity: 0; } }
</style>
