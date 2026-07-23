<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, shallowRef, watch } from 'vue'
import { Delete, WarningFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

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
const deleteOpen = shallowRef(false)
const deleting = shallowRef(false)
const deleteTarget = shallowRef<DocumentRecord>()
type UploadState = {
  progress: number
  status: '校验中' | '上传中' | '处理中' | '成功' | '失败'
  message: string
  jobId?: string
  documentId?: string
}
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
  syncUploadStates()
}

function syncUploadStates(): void {
  for (const [filename, state] of Object.entries(uploadStates)) {
    const document = documents.value.find((item) =>
      item.id === state.documentId || item.original_filename === filename,
    )
    const job = jobs.value.find((item) =>
      item.id === state.jobId || (document && item.document_id === document.id),
    )
    if (!job && document?.status === 'ready') {
      state.progress = 100
      state.status = '成功'
      state.message = '解析、切分和向量生成已完成'
      continue
    }
    if (!job && document?.status === 'failed') {
      state.status = '失败'
      state.message = document.error_message || '后台处理失败'
      continue
    }
    if (!job) continue
    if (job.status === 'succeeded') {
      state.progress = 100
      state.status = '成功'
      state.message = '解析、切分和向量生成已完成'
    } else if (job.status === 'failed' || job.status === 'cancelled') {
      state.status = '失败'
      state.message = job.error_message || (job.status === 'cancelled' ? '处理任务已取消' : '后台处理失败')
    } else {
      state.status = '处理中'
      state.message = job.status === 'running' ? '正在解析、切分和生成向量' : '已进入处理队列'
    }
  }
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
        const response = await api.post<{ job_id: string; document_id: string }>('/documents/upload', body, {
          onUploadProgress: (progress) => { uploadStates[file.name].progress = progress.total ? Math.round(progress.loaded / progress.total * 100) : 0 },
        })
        uploadStates[file.name] = {
          progress: 100,
          status: '处理中',
          message: '已进入处理队列',
          jobId: response.data.job_id,
          documentId: response.data.document_id,
        }
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

function requestRemove(document: DocumentRecord): void {
  deleteTarget.value = document
  deleteOpen.value = true
}

async function confirmRemove(): Promise<void> {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    const filename = deleteTarget.value.original_filename
    await api.delete(`/documents/${deleteTarget.value.id}`)
    delete uploadStates[filename]
    deleteOpen.value = false
    deleteTarget.value = undefined
    ElMessage.success('文档、原文件和检索向量已删除')
    await load()
  } catch (error) {
    ElMessage.error((error as Error).message || '删除失败，请稍后重试')
  } finally {
    deleting.value = false
  }
}

function latestJob(documentId: string): ProcessingJob | undefined {
  return jobs.value.find((item) => item.document_id === documentId)
}

watch(() => props.selectedId, () => void load(), { immediate: true })
poller = window.setInterval(() => {
  const hasPendingJob = jobs.value.some((job) => ['queued', 'running'].includes(job.status))
  const hasPendingUpload = Object.values(uploadStates).some((state) => state.status === '处理中')
  if (hasPendingJob || hasPendingUpload) void load()
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
        <el-button link @click="preview(documentRow(scope.row))">切分预览</el-button><el-button link @click="reindex(documentRow(scope.row))">重建</el-button><el-button v-if="scope.row.status === 'failed'" link type="warning" @click="retry(documentRow(scope.row))">重试</el-button><el-button link type="danger" @click="requestRemove(documentRow(scope.row))">删除</el-button>
      </template></el-table-column>
    </el-table>
    <el-dialog v-model="previewOpen" :title="`${previewName} · 切分预览`" width="min(860px, 92vw)">
      <el-empty v-if="!chunks.length" description="暂无切分内容" />
      <article v-for="chunk in chunks" :key="chunk.id" class="chunk-card"><div><b>#{{ chunk.ordinal + 1 }}</b><span>{{ chunk.location }}</span><el-tag v-for="model in chunk.product_models" :key="model" size="small">{{ model }}</el-tag></div><p>{{ chunk.text }}</p></article>
    </el-dialog>
    <el-dialog v-model="deleteOpen" class="delete-document-dialog" width="min(480px, 92vw)"
      :show-close="false" align-center destroy-on-close>
      <div class="delete-dialog__mark"><el-icon><WarningFilled /></el-icon><span>DESTRUCTIVE ACTION</span></div>
      <h2>确认删除这份文档？</h2>
      <p class="delete-dialog__lead">删除后，客服将无法再从这份资料中检索答案。</p>
      <div class="delete-dialog__file">
        <el-icon><Delete /></el-icon>
        <div><small>即将删除</small><strong>{{ deleteTarget?.original_filename }}</strong></div>
      </div>
      <ul class="delete-dialog__impact">
        <li>移除原始上传文件</li>
        <li>清理全部切分片段</li>
        <li>同步删除关联检索向量</li>
      </ul>
      <p class="delete-dialog__warning">此操作不可撤销，已有历史回答不会被改写。</p>
      <template #footer>
        <div class="delete-dialog__actions">
          <el-button size="large" :disabled="deleting" @click="deleteOpen = false">保留文档</el-button>
          <el-button size="large" type="danger" :loading="deleting" @click="confirmRemove">确认删除</el-button>
        </div>
      </template>
    </el-dialog>
  </el-card>
</template>

<style scoped>
.document-card{border-radius:20px!important}.card-header{align-items:center;display:flex;justify-content:space-between}.card-header>div>span,.card-header strong,.card-header small{display:block}.card-header>div>span{color:var(--mi-orange);font-family:var(--font-mono);font-size:9px;font-weight:700;letter-spacing:.14em}.card-header strong{font-size:18px;margin:4px 0}.card-header small{color:var(--ink-muted);font-size:10px}.upload-grid{display:grid;gap:10px;grid-template-columns:1fr 150px 150px 1.2fr}.upload-grid label{display:grid;gap:5px}.upload-grid label>span{color:var(--ink-muted);font-size:10px;font-weight:650}.upload-grid :deep(.el-input-number){width:100%}
.progress-row{align-items:center;background:#faf9f7;border-radius:12px;display:grid;gap:10px;grid-template-columns:180px 1fr 64px 180px;margin:8px 0;padding:10px 14px}.progress-row b{font-size:12px}.progress-row small{color:var(--ink-muted)}.progress-row .is-失败{color:#d94b4b}.progress-row .is-处理中,.progress-row .is-成功{color:#2c9a68}
.chunk-card { border: 1px solid var(--line); border-radius: 10px; margin-bottom: 12px; padding: 14px; }
.chunk-card div { align-items: center; display: flex; gap: 8px; }.chunk-card span { color: var(--ink-muted); }.chunk-card p { line-height: 1.7; white-space: pre-wrap; }
:global(.delete-document-dialog){border:1px solid #f2ddd7;border-radius:24px!important;box-shadow:0 28px 80px rgba(72,31,17,.22);overflow:hidden;padding:0!important}
:global(.delete-document-dialog .el-dialog__header){display:none}
:global(.delete-document-dialog .el-dialog__body){padding:30px 30px 18px}
:global(.delete-document-dialog .el-dialog__footer){background:#fff9f6;border-top:1px solid #f5e7e1;padding:18px 30px}
.delete-dialog__mark{align-items:center;color:#d94b32;display:flex;font-family:var(--font-mono);font-size:10px;font-weight:750;gap:8px;letter-spacing:.13em}.delete-dialog__mark .el-icon{background:#fff0ea;border-radius:10px;font-size:20px;padding:8px}.delete-document-dialog h2{color:var(--ink);font-size:25px;letter-spacing:-.04em;margin:18px 0 7px}.delete-dialog__lead{color:var(--ink-muted);font-size:13px;line-height:1.6;margin:0}.delete-dialog__file{align-items:center;background:#faf7f4;border:1px solid #ebe4de;border-radius:15px;display:flex;gap:13px;margin:22px 0 16px;padding:15px}.delete-dialog__file>.el-icon{background:#fff;color:#d94b32;font-size:20px;padding:9px}.delete-dialog__file small,.delete-dialog__file strong{display:block}.delete-dialog__file small{color:var(--ink-muted);font-size:10px;margin-bottom:4px}.delete-dialog__file strong{font-size:13px;overflow-wrap:anywhere}.delete-dialog__impact{color:var(--ink-soft);display:grid;font-size:12px;gap:8px;grid-template-columns:repeat(3,1fr);list-style:none;margin:0;padding:0}.delete-dialog__impact li{background:#fff;border:1px solid var(--line);border-radius:10px;line-height:1.45;padding:10px}.delete-dialog__warning{color:#b94733;font-size:11px;font-weight:650;margin:16px 0 0}.delete-dialog__actions{display:flex;gap:10px;justify-content:flex-end}.delete-dialog__actions .el-button{border-radius:12px;min-width:112px}.delete-dialog__actions .el-button--danger{background:#d94b32;border-color:#d94b32}
@media (max-width: 800px) { .upload-grid { grid-template-columns: 1fr 1fr; } }
@media (max-width:520px){.delete-dialog__impact{grid-template-columns:1fr}.delete-dialog__actions{display:grid;grid-template-columns:1fr 1fr}.delete-dialog__actions .el-button{margin:0;min-width:0}}
</style>
