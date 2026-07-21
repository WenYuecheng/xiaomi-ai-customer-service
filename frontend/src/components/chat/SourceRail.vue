<script setup lang="ts">
import type { Source } from '@/types'

defineProps<{ sources: readonly Source[] }>()

function safeSourceUrl(value?: string | null): string | undefined {
  if (!value) return undefined
  try {
    const parsed = new URL(value)
    return ['http:', 'https:'].includes(parsed.protocol) ? parsed.toString() : undefined
  } catch {
    return undefined
  }
}
</script>

<template>
  <aside class="source-rail" data-testid="source-rail" aria-label="回答依据">
    <div class="source-rail__label"><span>✓</span> 已核验的回答依据 <small>{{ sources.length }} 条来源</small></div>
    <article v-for="(source, index) in sources" :key="source.chunk_id" class="source-card">
      <span class="source-card__index">{{ String(index + 1).padStart(2, '0') }}</span>
      <div>
        <a
          v-if="safeSourceUrl(source.source_url)"
          class="source-card__link"
          :href="safeSourceUrl(source.source_url)"
          target="_blank"
          rel="noopener noreferrer"
        >{{ source.filename }}</a>
        <strong v-else>{{ source.filename }}</strong>
        <span>{{ source.location }} · 相关度 {{ Math.round(source.score * 100) }}%</span>
        <p>{{ source.snippet }}</p>
      </div>
    </article>
  </aside>
</template>

<style scoped>
.source-rail{background:#f7f6f3;border:1px solid var(--line);border-left:3px solid var(--success);border-radius:0 13px 13px 0;margin-top:16px;padding:13px 15px}.source-rail__label{color:var(--ink-soft);font-size:11px;font-weight:700;letter-spacing:.08em;margin-bottom:10px;text-transform:uppercase}.source-rail__label>span{color:var(--success);margin-right:5px}.source-rail__label small{color:var(--ink-muted);float:right;font-weight:500;letter-spacing:0;text-transform:none}
.source-card { display: grid; grid-template-columns: 34px 1fr; gap: 8px; padding: 10px 0; }
.source-card__index{color:var(--mi-orange);font-family:var(--font-mono);font-size:12px}
.source-card strong { display: block; font-size: 13px; }
.source-card__link { color: var(--ink); display: block; font-size: 13px; font-weight: 700; }
.source-card span { color: var(--ink-muted); display: block; font-size: 12px; margin-top: 2px; }
.source-card p { color: var(--ink-soft); font-size: 13px; line-height: 1.65; margin: 6px 0 0; }
</style>
