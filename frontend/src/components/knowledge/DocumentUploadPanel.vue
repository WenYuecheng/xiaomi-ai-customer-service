<script setup lang="ts">
import { shallowRef, useTemplateRef } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'

const props = defineProps<{ disabled?: boolean }>()
const emit = defineEmits<{ select: [files: File[]] }>()
const fileInput = useTemplateRef<HTMLInputElement>('fileInput')
const isDragover = shallowRef(false)

function openChooser(): void {
  if (!props.disabled) fileInput.value?.click()
}

function selectFiles(event: Event): void {
  const input = event.target as HTMLInputElement
  emit('select', [...(input.files ?? [])])
  input.value = ''
}

function dropFiles(event: DragEvent): void {
  isDragover.value = false
  if (!props.disabled) emit('select', [...(event.dataTransfer?.files ?? [])])
}
</script>

<template>
  <div class="upload-dropzone" :class="{ 'is-dragover': isDragover, 'is-disabled': disabled }"
    @dragover.prevent="isDragover = true" @dragleave.prevent="isDragover = false"
    @drop.prevent="dropFiles" @click="openChooser">
    <el-icon class="upload-icon"><UploadFilled /></el-icon>
    <div class="upload-text">将文件拖到此处，或 <em>点击上传</em></div>
    <div class="upload-hint">支持 PDF、DOCX、TXT、Markdown · 单文件最大 10 MB · 可多选</div>
    <input ref="fileInput" class="hidden-input" type="file" multiple accept=".pdf,.docx,.txt,.md"
      :disabled="disabled" @click.stop @change="selectFiles">
  </div>
</template>

<style scoped>
.upload-dropzone{background:#faf9f7;border:2px dashed #d8d3cc;border-radius:16px;cursor:pointer;margin:16px 0;padding:34px;text-align:center;transition:all .2s ease}.upload-dropzone:hover{background:#fff8f2;border-color:var(--mi-orange)}.upload-dropzone.is-dragover{background:#fff8f3;border-color:var(--mi-orange)}.upload-dropzone.is-disabled{cursor:not-allowed;opacity:.6;pointer-events:none}.upload-icon{color:#aaa59e;font-size:38px;margin-bottom:8px;transition:color .2s}.upload-dropzone:hover .upload-icon{color:var(--mi-orange)}.upload-text{color:var(--ink);font-size:15px;margin-bottom:4px}.upload-text em{color:var(--mi-orange);font-style:normal;font-weight:700}.upload-hint{color:var(--ink-muted);font-size:12px}.hidden-input{display:none}
</style>
