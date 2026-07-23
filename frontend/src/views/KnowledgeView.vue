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
  <section class="knowledge-page">
    <header class="section-heading"><div><span>KNOWLEDGE OPERATIONS</span><h1>知识中心</h1><p>维护机器人唯一可信的事实来源，完整追踪上传、解析、切分、向量化与引用关系。</p></div><div class="flow"><span>01 上传</span><i /> <span>02 解析切分</span><i /> <span>03 向量检索</span><i /> <span>04 可信回答</span></div></header>
    <KnowledgeBaseManager :items="items" :loading="loading" @refresh="load" @select="selectedId = $event" />
    <template v-if="selectedId">
      <KnowledgeAnalytics :knowledge-base-id="selectedId" />
      <DocumentManager :knowledge-bases="items" :selected-id="selectedId" @select="selectedId = $event" />
    </template>
    <section v-else class="knowledge-onboarding"><span>01</span><div><h2>从创建第一个知识库开始</h2><p>知识库用于隔离不同业务资料。创建后上传官方 PDF、DOCX、TXT 或 Markdown，系统会自动生成切片、向量与知识图谱。</p></div><ol><li><b>创建知识库</b><small>填写名称与用途说明</small></li><li><b>上传官方资料</b><small>建议保留原始来源链接</small></li><li><b>等待处理完成</b><small>确认文档状态变为 Ready</small></li></ol></section>
  </section>
</template>

<style scoped>
.knowledge-page{display:grid;gap:18px}.section-heading{align-items:flex-end;display:flex;justify-content:space-between;margin-bottom:10px}.section-heading>div:first-child{max-width:720px}.section-heading>div>span{color:var(--mi-orange);font-family:var(--font-mono);font-size:10px;font-weight:700;letter-spacing:.16em}.section-heading h1{font-size:clamp(36px,5vw,54px);letter-spacing:-.05em;margin:8px 0}.section-heading p{color:var(--ink-muted);line-height:1.7;margin:0}.flow{align-items:center;background:white;border:1px solid var(--line);border-radius:12px;display:flex;gap:7px;padding:10px 12px}.flow span{color:var(--ink-soft);font-size:10px;white-space:nowrap}.flow i{background:#d8d4ce;height:1px;width:14px}.knowledge-onboarding{align-items:center;background:#1d1c1a;border-radius:20px;color:white;display:grid;gap:24px;grid-template-columns:auto minmax(220px,1fr) minmax(400px,1.3fr);padding:28px}.knowledge-onboarding>span{color:var(--mi-orange);font-family:var(--font-mono);font-size:30px}.knowledge-onboarding h2{font-size:22px;margin:0 0 8px}.knowledge-onboarding p{color:#aaa7a2;font-size:12px;line-height:1.7;margin:0}.knowledge-onboarding ol{display:grid;gap:8px;grid-template-columns:repeat(3,1fr);list-style:none;margin:0;padding:0}.knowledge-onboarding li{background:#292825;border:1px solid #383633;border-radius:12px;padding:13px}.knowledge-onboarding b,.knowledge-onboarding small{display:block}.knowledge-onboarding b{font-size:12px}.knowledge-onboarding small{color:#8d8a85;font-size:10px;margin-top:5px}@media(max-width:900px){.section-heading{align-items:flex-start;flex-direction:column;gap:16px}.flow{max-width:100%;overflow:auto}.knowledge-onboarding{grid-template-columns:auto 1fr}.knowledge-onboarding ol{grid-column:1/-1}}@media(max-width:620px){.flow{display:none}.knowledge-onboarding{grid-template-columns:1fr}.knowledge-onboarding>span{display:none}.knowledge-onboarding ol{grid-template-columns:1fr}}
</style>
<style scoped>
.knowledge-onboarding{background:#fff;border:1px solid var(--line);box-shadow:var(--shadow-sm);color:var(--ink)}.knowledge-onboarding p{color:var(--ink-muted)}.knowledge-onboarding li{background:#faf9f7;border-color:var(--line)}.knowledge-onboarding small{color:var(--ink-muted)}
</style>
