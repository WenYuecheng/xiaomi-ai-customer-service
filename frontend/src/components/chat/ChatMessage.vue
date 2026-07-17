<script setup lang="ts">
import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'
import { computed } from 'vue'

import type { ChatMessage as Message } from '@/types'

import SourceRail from './SourceRail.vue'

const props = defineProps<{ message: Message }>()
const emit = defineEmits<{ feedback: [messageId: string, rating: 'up' | 'down'] }>()
const markdown = new MarkdownIt({ html: false, linkify: true, breaks: true })
const rendered = computed(() => DOMPurify.sanitize(markdown.render(props.message.content)))
</script>

<template>
  <article class="message" :class="`message--${message.role}`">
    <div class="message__identity">{{ message.role === 'assistant' ? '小爱客服' : '你' }}</div>
    <div class="message__body">
      <div v-if="message.fallback" class="message__fallback">知识库暂无可靠答案</div>
      <div class="message__content" v-html="rendered" />
      <SourceRail v-if="message.sources.length" :sources="message.sources" />
      <div v-if="message.role === 'assistant'" class="message__actions">
        <button type="button" @click="emit('feedback', message.id, 'up')">有帮助</button>
        <button type="button" @click="emit('feedback', message.id, 'down')">需改进</button>
      </div>
    </div>
  </article>
</template>

<style scoped>
.message { display: grid; grid-template-columns: 72px minmax(0, 1fr); gap: 18px; padding: 24px 0; }
.message + .message { border-top: 1px solid var(--line); }
.message__identity { color: var(--ink-muted); font-size: 12px; font-weight: 650; padding-top: 3px; }
.message__body { max-width: 780px; }
.message__content { color: var(--ink); font-size: 15px; line-height: 1.8; }
.message--user .message__content { font-size: 17px; font-weight: 580; }
.message__fallback { color: #a94712; background: #fff0e7; border-radius: 8px; display: inline-block; font-size: 12px; margin-bottom: 8px; padding: 5px 9px; }
.message__actions { display: flex; gap: 8px; margin-top: 12px; }
.message__actions button { background: transparent; border: 1px solid var(--line); border-radius: 999px; color: var(--ink-muted); cursor: pointer; font-size: 12px; padding: 5px 10px; }
.message__actions button:hover { border-color: var(--mi-orange); color: var(--mi-orange); }
@media (max-width: 640px) { .message { grid-template-columns: 1fr; gap: 6px; } }
</style>

