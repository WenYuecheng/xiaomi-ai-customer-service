<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, shallowRef, useTemplateRef, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'

import { api } from '@/api/client'
import type { DocumentChunk, DocumentRecord, KnowledgeBase, ProcessingJob } from '@/types'

const props = defineProps<{ knowledgeBases: KnowledgeBase[]; selectedId: string }>()
const emit = defineEmits<{ select: [id: string] }>()
const documents = shallowRef<DocumentRecord[]>([])
const jobs = shallowRef<ProcessingJob[]>([])
const chunks = shallowRef<DocumentChunk[]>([])
const previewName = shallowRef('')
const previewOpen = shallowRef(false)
const busy = shallowRef(false)
const uploadProgress = reactive<Record<string, number>>({})
const config = reactive({ chunk_size: 800, chunk_overlap: 120, source_url: '' })
const isDragover = shallowRef(false)
const fileInput = useTemplateRef<HTMLInputElement>('fileInput')
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
  busy.value = true
  try {
    for (const file of files) {
      const body = new FormData()
      body.append('knowledge_base_id', selected.value)
      body.append('file', file)
      body.append('chunk_size', String(config.chunk_size))
      body.append('chunk_overlap', String(config.chunk_overlap))
      if (config.source_url.trim()) body.append('source_url', config.source_url.trim())
      uploadProgress[file.name] = 0
      await api.post('/documents/upload', body, {
        onUploadProgress: (progress) => { uploadProgress[file.name] = progress.total ? Math.round(progress.loaded / progress.total * 100) : 0 },
      })
      uploadProgress[file.name] = 100
    }
    ElMessage.success(`${files.length} 个文件已进入处理队列`)
    await load()
  } finally { busy.value = false }
}

async function uploadFiles(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const files = [...(input.files ?? [])]
  await processFiles(files)
  input.value = ''
}

async function handleDrop(event: DragEvent): Promise<void> {
  isDragover.value = false
  if (busy.value || !selected.value) return
  const files = [...(event.dataTransfer?.files ?? [])]
  await processFiles(files)
}

function triggerFileSelect(): void {
  if (busy.value || !selected.value) return
  fileInput.value?.click()
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
    <div class="upload-dropzone" :class="{ 'is-dragover': isDragover, 'is-disabled': busy || !selected }" @dragover.prevent="isDragover = true" @dragleave.prevent="isDragover = false" @drop.prevent="handleDrop" @click="triggerFileSelect">
      <el-icon class="upload-icon"><UploadFilled /></el-icon>
      <div class="upload-text">将文件拖到此处，或 <em>点击上传</em></div>
      <div class="upload-hint">支持 PDF、DOCX、TXT、Markdown · 单文件最大 10 MB · 可多选</div>
      <input ref="fileInput" class="hidden-input" type="file" multiple accept=".pdf,.docx,.txt,.md" :disabled="busy || !selected" @change="uploadFiles" />
    </div>
    <div v-for="(progress, name) in uploadProgress" :key="name" class="progress-row"><span>{{ name }}</span><el-progress :percentage="progress" /></div>
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
.document-card{border-radius:20px!important}.card-header{align-items:center;display:flex;justify-content:space-between}.card-header>div>span,.card-header strong,.card-header small{display:block}.card-header>div>span{color:var(--mi-orange);font-family:var(--font-mono);font-size:9px;font-weight:700;letter-spacing:.14em}.card-header strong{font-size:18px;margin:4px 0}.card-header small{color:var(--ink-muted);font-size:10px}.upload-grid{display:grid;gap:10px;grid-template-columns:1fr 150px 150px 1.2fr}.upload-grid label{display:grid;gap:5px}.upload-grid label>span{color:var(--ink-muted);font-size:10px;font-weight:650}.upload-grid :deep(.el-input-number){width:100%}.upload-dropzone{background:#faf9f7;border:2px dashed #d8d3cc;border-radius:16px;cursor:pointer;margin:16px 0;padding:34px;text-align:center;transition:all .2s ease}.upload-dropzone:hover{background:#fff8f2;border-color:var(--mi-orange)}
.upload-dropzone.is-dragover { border-color: var(--mi-orange); background: #fff8f3; }
.upload-dropzone.is-disabled { cursor: not-allowed; opacity: .6; pointer-events: none; }
.upload-icon{color:#aaa59e;font-size:38px;margin-bottom:8px;transition:color .2s}.upload-dropzone:hover .upload-icon{color:var(--mi-orange)}
.upload-text { color: var(--ink); font-size: 15px; margin-bottom: 4px; }
.upload-text em{color:var(--mi-orange);font-style:normal;font-weight:700}
.upload-hint { color: var(--ink-muted); font-size: 12px; }
.hidden-input { display: none; }
.progress-row { display: grid; gap: 12px; grid-template-columns: 180px 1fr; margin: 8px 0; }
.chunk-card { border: 1px solid var(--line); border-radius: 10px; margin-bottom: 12px; padding: 14px; }
.chunk-card div { align-items: center; display: flex; gap: 8px; }.chunk-card span { color: var(--ink-muted); }.chunk-card p { line-height: 1.7; white-space: pre-wrap; }
@media (max-width: 800px) { .upload-grid { grid-template-columns: 1fr 1fr; } }
</style>
