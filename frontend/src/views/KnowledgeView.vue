<script setup lang="ts">
import { onMounted, shallowRef } from 'vue'

import { api } from '@/api/client'
import DocumentManager from '@/components/knowledge/DocumentManager.vue'
import KnowledgeAnalytics from '@/components/knowledge/KnowledgeAnalytics.vue'
import KnowledgeBaseManager from '@/components/knowledge/KnowledgeBaseManager.vue'
import type { KnowledgeBase } from '@/types'

const items = shallowRef<KnowledgeBase[]>([])
const selectedId = shallowRef('')
const loading = shallowRef(false)

async function load(): Promise<void> {
  loading.value = true
  try {
    const response = await api.get<{ items: KnowledgeBase[] }>('/knowledge-bases')
    items.value = response.data.items
    if (!items.value.some((item) => item.id === selectedId.value)) selectedId.value = items.value[0]?.id ?? ''
  } finally { loading.value = false }
}

onMounted(load)
</script>

<template>
  <section>
    <header class="section-heading"><span>KNOWLEDGE OPERATIONS</span><h1>知识库</h1><p>资料经过安全校验、语义清洗和结构切分后进入可信检索。</p></header>
    <KnowledgeAnalytics :knowledge-base-id="selectedId" />
    <KnowledgeBaseManager :items="items" :loading="loading" @refresh="load" @select="selectedId = $event" />
    <DocumentManager :knowledge-bases="items" :selected-id="selectedId" @select="selectedId = $event" />
  </section>
</template>

<style scoped>
.section-heading { margin-bottom: 28px; }.section-heading span { background: linear-gradient(90deg,#6c4ddd,#d855ac); background-clip: text; color: transparent; font-family: var(--font-mono); font-size: 11px; letter-spacing: .16em; }.section-heading h1 { font-size: 42px; margin: 8px 0; }.section-heading p { color: var(--ink-muted); }
</style>
