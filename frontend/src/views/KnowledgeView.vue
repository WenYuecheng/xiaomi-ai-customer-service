<script setup lang="ts">
import { onMounted, reactive, ref, shallowRef } from 'vue'
import { ElMessage } from 'element-plus'

import { api } from '@/api/client'
import type { KnowledgeBase } from '@/types'

const items = ref<KnowledgeBase[]>([])
const form = reactive({ name: '', description: '' })
const selectedId = shallowRef('')
const upload = shallowRef<File>()
const busy = shallowRef(false)

async function load(): Promise<void> {
  const response = await api.get<{ items: KnowledgeBase[] }>('/knowledge-bases')
  items.value = response.data.items
  selectedId.value ||= items.value[0]?.id ?? ''
}

async function createKnowledgeBase(): Promise<void> {
  await api.post('/knowledge-bases', form)
  form.name = ''; form.description = ''
  ElMessage.success('知识库已创建')
  await load()
}

async function uploadDocument(): Promise<void> {
  if (!upload.value || !selectedId.value) return
  busy.value = true
  const body = new FormData()
  body.append('knowledge_base_id', selectedId.value)
  body.append('file', upload.value)
  try {
    await api.post('/documents/upload', body)
    ElMessage.success('文件已进入后台处理队列')
    upload.value = undefined
  } finally { busy.value = false }
}

onMounted(load)
</script>

<template>
  <section>
    <header class="section-heading"><span>KNOWLEDGE OPERATIONS</span><h1>知识库</h1><p>资料先经过安全校验、语义清洗和结构切分，再进入检索。</p></header>
    <div class="knowledge-grid">
      <el-card shadow="never">
        <template #header><strong>创建知识库</strong></template>
        <el-form :model="form" label-position="top" @submit.prevent="createKnowledgeBase">
          <el-form-item label="名称"><el-input v-model="form.name" maxlength="100" /></el-form-item>
          <el-form-item label="描述"><el-input v-model="form.description" type="textarea" /></el-form-item>
          <el-button type="primary" native-type="submit" :disabled="!form.name.trim()">创建</el-button>
        </el-form>
      </el-card>
      <el-card shadow="never">
        <template #header><strong>上传资料</strong></template>
        <el-select v-model="selectedId" placeholder="选择知识库" style="width: 100%">
          <el-option v-for="item in items" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <input class="file-input" type="file" accept=".pdf,.docx,.txt,.md" @change="upload = ($event.target as HTMLInputElement).files?.[0]" />
        <el-button type="primary" :loading="busy" :disabled="!upload" @click="uploadDocument">上传并处理</el-button>
      </el-card>
    </div>
    <el-table :data="items" class="knowledge-table">
      <el-table-column prop="name" label="知识库" />
      <el-table-column prop="description" label="描述" />
      <el-table-column prop="status" label="状态" width="120" />
    </el-table>
  </section>
</template>

<style scoped>
.section-heading span { color: var(--mi-orange); font-family: var(--font-mono); font-size: 11px; letter-spacing: .16em; }
.section-heading h1 { font-size: 38px; margin: 8px 0; }.section-heading p { color: var(--ink-muted); }
.knowledge-grid { display: grid; gap: 18px; grid-template-columns: 1fr 1fr; margin: 32px 0; }
.file-input { border: 1px dashed var(--line); border-radius: 8px; display: block; margin: 18px 0; padding: 20px; width: calc(100% - 42px); }
.knowledge-table { border-radius: 12px; }
@media (max-width: 720px) { .knowledge-grid { grid-template-columns: 1fr; } }
</style>

