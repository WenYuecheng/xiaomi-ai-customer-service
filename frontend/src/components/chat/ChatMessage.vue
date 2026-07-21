<script setup lang="ts">
import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'
import { computed } from 'vue'
import { CircleCheckFilled, WarningFilled } from '@element-plus/icons-vue'

import type { ChatMessage as Message } from '@/types'
import AdvisorPlanCard from '@/components/advisor/AdvisorPlanCard.vue'

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
    <div class="message__identity"><span>{{ message.role === 'assistant' ? 'AI' : 'YOU' }}</span>{{ message.role === 'assistant' ? '小爱客服' : '你' }}</div>
    <div class="message__body">
      <div v-if="message.fallback" class="message__fallback">知识库暂无可靠答案</div>
      <AiTracePanel v-if="message.role === 'assistant' && message.ai_trace?.length" :steps="message.ai_trace" />
      <div class="message__content" :class="{ 'is-typing': isTyping }" v-html="rendered" />
      <AdvisorPlanCard v-if="message.advisor_plan" :plan="message.advisor_plan" :sources="message.sources" />
      <SourceRail v-if="message.sources.length && !message.advisor_plan" :sources="message.sources" />
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
.message{display:grid;gap:14px;grid-template-columns:68px minmax(0,1fr);padding:18px 0}.message+.message{border-top:1px solid #f0eeea}.message__identity{color:var(--ink-muted);font-size:11px;font-weight:650;padding-top:4px}.message__identity span{background:#f0ede9;border:1px solid #ded9d2;border-radius:9px;color:var(--ink-soft);display:grid;font-size:9px;height:31px;margin-bottom:7px;place-items:center;width:31px}.message--assistant .message__identity span{background:#fff1e6;border-color:#ffd0ad;color:var(--mi-orange)}.message__body{max-width:850px;padding:3px 0}.message--user .message__body{background:#f7f6f3;border-radius:16px;margin-left:auto;max-width:72%;padding:14px 17px}
.message__content { color: var(--ink); font-size: 15px; line-height: 1.8; }
.message__content.is-typing::after { content: ''; display: inline-block; width: 4px; height: 1em; background: var(--mi-orange); animation: blink 1s step-end infinite; vertical-align: -2px; margin-left: 4px; }
.message__content :deep(strong){color:var(--ink);font-weight:780}.message__content :deep(code){background:#f2efeb;border-radius:6px;color:#b64e08;padding:2px 5px}.message__content :deep(a){color:var(--mi-orange)}.message--user .message__content{font-size:15px;font-weight:580}
.message__fallback { color: #a94712; background: #fff0e7; border-radius: 8px; display: inline-block; font-size: 12px; margin-bottom: 8px; padding: 5px 9px; }
.message__actions { display: flex; gap: 8px; margin-top: 12px; }
.message__actions button { align-items: center; background: transparent; border: 1px solid var(--line); border-radius: 999px; color: var(--ink-muted); cursor: pointer; display: inline-flex; font-size: 12px; gap: 5px; padding: 6px 11px; transition: background-color .18s ease, border-color .18s ease, color .18s ease, transform .18s ease; }
.message__actions button svg { height: 15px; width: 15px; }
.message__actions button:hover { border-color: var(--mi-orange); color: var(--mi-orange); }
.message__actions button:active { transform: scale(.94); }
.message__actions button.selected{animation:feedback-pop .34s ease-out;background:#fff1e6;border-color:#ffb681;color:#c95508}
.message__actions .transfer { background: var(--mi-orange); border-color: var(--mi-orange); color: white; }
.message__actions .transfer:disabled { cursor: default; opacity: .72; }
@media (max-width: 640px) { .message { grid-template-columns: 1fr; gap: 6px; } }
@media (prefers-reduced-motion: reduce) { .message__actions button.selected { animation: none; } }
@keyframes feedback-pop { 50% { transform: scale(1.08); } }
@keyframes blink { 50% { opacity: 0; } }
</style>
