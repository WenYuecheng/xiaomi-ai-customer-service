<script setup lang="ts">
import type { Source } from '@/types'

defineProps<{ sources: Source[] }>()
</script>

<template>
  <aside class="source-rail" data-testid="source-rail" aria-label="回答依据">
    <div class="source-rail__label">回答依据</div>
    <article v-for="(source, index) in sources" :key="source.chunk_id" class="source-card">
      <span class="source-card__index">{{ String(index + 1).padStart(2, '0') }}</span>
      <div>
        <strong>{{ source.filename }}</strong>
        <span>{{ source.location }} · 相关度 {{ Math.round(source.score * 100) }}%</span>
        <p>{{ source.snippet }}</p>
      </div>
    </article>
  </aside>
</template>

<style scoped>
.source-rail { border-left: 2px solid var(--mi-orange); margin-top: 16px; padding-left: 16px; }
.source-rail__label { color: var(--ink-muted); font-size: 12px; letter-spacing: .14em; margin-bottom: 10px; text-transform: uppercase; }
.source-card { display: grid; grid-template-columns: 34px 1fr; gap: 8px; padding: 10px 0; }
.source-card__index { color: var(--mi-orange); font-family: var(--font-mono); font-size: 12px; }
.source-card strong { display: block; font-size: 13px; }
.source-card span { color: var(--ink-muted); display: block; font-size: 12px; margin-top: 2px; }
.source-card p { color: var(--ink-soft); font-size: 13px; line-height: 1.65; margin: 6px 0 0; }
</style>

