<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, shallowRef, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { api } from '@/api/client'
import type { DocumentChunk, DocumentRecord, KnowledgeBase, ProcessingJob } from '@/types'
import DocumentUploadPanel from './DocumentUploadPanel.vue'

const props = defineProps<{ knowledgeBases: KnowledgeBase[]; selectedId: string }>()
const emit = defineEmits<{ select: [id: string] }>()
const documents = shallowRef<DocumentRecord[]>([])
const jobs = shallowRef<ProcessingJob[]>([])
const chunks = shallowRef<DocumentChunk[]>([])
const previewName = shallowRef('')
const previewOpen = shallowRef(false)
const busy = shallowRef(false)
type UploadState = { progress: number; status: '校验中' | '上传中' | '处理中' | '成功' | '失败'; message: string }
const uploadStates = reactive<Record<string, UploadState>>({})
const config = reactive({ chunk_size: 800, chunk_overlap: 120, source_url: '' })
let poller: number | undefined
const selected = computed({ get: () => props.selectedId, set: (value) => emit('select', value) })
const documentRow = (value: unknown): DocumentRecord => value as DocumentRecord

async function load(): Promise<void> {
  if (!selected.value) { documents.value = []; jobs.value = []; return }
  const [documentResponse, jobResponse] = await Promise.all([
    api.get<{ items: DocumentRecord[] }>('/documents', { params: { knowledge_base_id: selected.value } }),
    api.get<{ items: ProcessingJob[] }>('/jobs'),
  ])
  documents.value = documentResponse.data.items
  const ids = new Set(documents.value.map((item) => item.id))
  jobs.value = jobResponse.data.items.filter((job) => ids.has(job.document_id))
}

async function processFiles(files: File[]): Promise<void> {
  if (!files.length || !selected.value) return
  if (config.chunk_overlap >= config.chunk_size) {
    ElMessage.error('重叠字符必须小于切片长度')
    return
  }
  busy.value = true
  let succeeded = 0
  try {
    for (const file of files) {
      uploadStates[file.name] = { progress: 0, status: '校验中', message: '正在检查格式和大小' }
      const suffix = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
      if (!['.pdf', '.docx', '.txt', '.md'].includes(suffix)) {
        uploadStates[file.name] = { progress: 0, status: '失败', message: '仅支持 PDF、DOCX、TXT 和 MD' }
        continue
      }
      if (file.size > 10 * 1024 * 1024) {
        uploadStates[file.name] = { progress: 0, status: '失败', message: '文件超过 10 MB' }
        continue
      }
      const body = new FormData()
      body.append('knowledge_base_id', selected.value)
      body.append('file', file)
      body.append('chunk_size', String(config.chunk_size))
      body.append('chunk_overlap', String(config.chunk_overlap))
      if (config.source_url.trim()) body.append('source_url', config.source_url.trim())
      uploadStates[file.name] = { progress: 0, status: '上传中', message: '正在安全上传' }
      try {
        await api.post('/documents/upload', body, {
          onUploadProgress: (progress) => { uploadStates[file.name].progress = progress.total ? Math.round(progress.loaded / progress.total * 100) : 0 },
        })
        uploadStates[file.name] = { progress: 100, status: '处理中', message: '已进入处理队列' }
        succeeded += 1
      } catch (error) {
        const responseMessage = (error as { response?: { data?: { error?: { message?: string } } } }).response?.data?.error?.message
        uploadStates[file.name] = { progress: 0, status: '失败', message: responseMessage || (error as Error).message || '上传失败' }
      }
    }
    if (succeeded) ElMessage.success(`${succeeded} 个文件已进入处理队列`)
    await load()
  } finally { busy.value = false }
}

async function preview(document: DocumentRecord): Promise<void> {
  const response = await api.get<{ items: DocumentChunk[] }>(`/documents/${document.id}/chunks`)
  chunks.value = response.data.items
  previewName.value = document.original_filename
  previewOpen.value = true
}

async function reindex(document: DocumentRecord): Promise<void> {
  await api.post(`/documents/${document.id}/reindex`)
  ElMessage.success('已创建重建任务')
  await load()
}

async function retry(document: DocumentRecord): Promise<void> {
  const job = jobs.value.find((item) => item.document_id === document.id && item.status === 'failed')
  if (!job) return
  await api.post(`/jobs/${job.id}/retry`)
  ElMessage.success('失败任务已重新入队')
  await load()
}

async function remove(document: DocumentRecord): Promise<void> {
  await ElMessageBox.confirm(`删除“${document.original_filename}”及全部向量？`, '删除文档', { type: 'warning' })
  await api.delete(`/documents/${document.id}`)
  ElMessage.success('文档、原文和向量已删除')
  await load()
}

function latestJob(documentId: string): ProcessingJob | undefined {
  return jobs.value.find((item) => item.document_id === documentId)
}

watch(() => props.selectedId, () => void load(), { immediate: true })
poller = window.setInterval(() => {
  if (jobs.value.some((job) => ['queued', 'running'].includes(job.status))) void load()
}, 1500)
onBeforeUnmount(() => window.clearInterval(poller))
</script>

<template>
  <el-card shadow="never" class="document-card">
    <template #header><div class="card-header"><div><span>INGESTION PIPELINE</span><strong>文档入库与处理任务</strong><small>上传后自动完成安全校验、文本清洗、语义切分和向量生成</small></div><el-button @click="load">刷新状态</el-button></div></template>
    <div class="upload-grid">
      <label><span>目标知识库</span><el-select v-model="selected" placeholder="选择知识库"><el-option v-for="item in knowledgeBases" :key="item.id" :label="item.name" :value="item.id" /></el-select></label>
      <label><span>切片长度</span><el-input-number v-model="config.chunk_size" :min="200" :max="4000" :step="100" controls-position="right" /></label>
      <label><span>重叠字符</span><el-input-number v-model="config.chunk_overlap" :min="0" :max="800" :step="20" controls-position="right" /></label>
      <label><span>公开来源</span><el-input v-model="config.source_url" placeholder="https://www.mi.com/…" /></label>
    </div>
    <DocumentUploadPanel :disabled="busy || !selected" @select="processFiles" />
    <div v-for="(state, name) in uploadStates" :key="name" class="progress-row">
      <span>{{ name }}</span><el-progress :percentage="state.progress" />
      <b :class="`is-${state.status}`">{{ state.status }}</b><small>{{ state.message }}</small>
    </div>
    <el-table :data="documents" empty-text="当前知识库还没有文档">
      <el-table-column prop="original_filename" label="文档" min-width="190" />
      <el-table-column prop="status" label="文档状态" width="110" />
      <el-table-column label="任务" min-width="150"><template #default="scope"><span>{{ latestJob(scope.row.id)?.operation ?? '-' }} / {{ latestJob(scope.row.id)?.status ?? '-' }}</span></template></el-table-column>
      <el-table-column label="切分" width="120"><template #default="scope">{{ scope.row.chunk_size }}/{{ scope.row.chunk_overlap }}</template></el-table-column>
      <el-table-column prop="error_message" label="错误" min-width="150" show-overflow-tooltip />
      <el-table-column label="操作" width="270"><template #default="scope">
        <el-button link @click="preview(documentRow(scope.row))">切分预览</el-button><el-button link @click="reindex(documentRow(scope.row))">重建</el-button><el-button v-if="scope.row.status === 'failed'" link type="warning" @click="retry(documentRow(scope.row))">重试</el-button><el-button link type="danger" @click="remove(documentRow(scope.row))">删除</el-button>
      </template></el-table-column>
    </el-table>
    <el-dialog v-model="previewOpen" :title="`${previewName} · 切分预览`" width="min(860px, 92vw)">
      <el-empty v-if="!chunks.length" description="暂无切分内容" />
      <article v-for="chunk in chunks" :key="chunk.id" class="chunk-card"><div><b>#{{ chunk.ordinal + 1 }}</b><span>{{ chunk.location }}</span><el-tag v-for="model in chunk.product_models" :key="model" size="small">{{ model }}</el-tag></div><p>{{ chunk.text }}</p></article>
    </el-dialog>
  </el-card>
</template>

<style scoped>
.document-card{border-radius:20px!important}.card-header{align-items:center;display:flex;justify-content:space-between}.card-header>div>span,.card-header strong,.card-header small{display:block}.card-header>div>span{color:var(--mi-orange);font-family:var(--font-mono);font-size:9px;font-weight:700;letter-spacing:.14em}.card-header strong{font-size:18px;margin:4px 0}.card-header small{color:var(--ink-muted);font-size:10px}.upload-grid{display:grid;gap:10px;grid-template-columns:1fr 150px 150px 1.2fr}.upload-grid label{display:grid;gap:5px}.upload-grid label>span{color:var(--ink-muted);font-size:10px;font-weight:650}.upload-grid :deep(.el-input-number){width:100%}
.progress-row{align-items:center;background:#faf9f7;border-radius:12px;display:grid;gap:10px;grid-template-columns:180px 1fr 64px 180px;margin:8px 0;padding:10px 14px}.progress-row b{font-size:12px}.progress-row small{color:var(--ink-muted)}.progress-row .is-失败{color:#d94b4b}.progress-row .is-处理中,.progress-row .is-成功{color:#2c9a68}
.chunk-card { border: 1px solid var(--line); border-radius: 10px; margin-bottom: 12px; padding: 14px; }
.chunk-card div { align-items: center; display: flex; gap: 8px; }.chunk-card span { color: var(--ink-muted); }.chunk-card p { line-height: 1.7; white-space: pre-wrap; }
@media (max-width: 800px) { .upload-grid { grid-template-columns: 1fr 1fr; } }
</style>
