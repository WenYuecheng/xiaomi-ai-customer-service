<script setup lang="ts">
import { computed, watch } from 'vue'

import type { KnowledgeBase } from '@/types'
import { defaultKnowledgeBaseIds, KNOWLEDGE_SELECTION_STORAGE_KEY, sanitizeKnowledgeBaseIds } from './knowledgeSelection'

const props = defineProps<{ modelValue: string[]; items: readonly KnowledgeBase[]; storageKey?: string }>()
const emit = defineEmits<{ 'update:modelValue': [ids: string[]]; change: [ids: string[]] }>()
const key = computed(() => props.storageKey || KNOWLEDGE_SELECTION_STORAGE_KEY)
const selected = computed({
  get: () => props.modelValue,
  set: (ids: string[]) => {
    const value = sanitizeKnowledgeBaseIds(ids, props.items)
    emit('update:modelValue', value)
    emit('change', value)
  },
})

watch(() => props.items, (items) => {
  let value = sanitizeKnowledgeBaseIds(props.modelValue, items)
  if (!value.length) {
    try { value = sanitizeKnowledgeBaseIds(JSON.parse(localStorage.getItem(key.value) || '[]'), items) } catch { value = [] }
  }
  if (!value.length) value = defaultKnowledgeBaseIds(items)
  if (value.join('|') !== props.modelValue.join('|')) emit('update:modelValue', value)
  if (value.length) localStorage.setItem(key.value, JSON.stringify(value))
}, { immediate: true, deep: true })

watch(() => props.modelValue, (ids) => {
  const value = sanitizeKnowledgeBaseIds(ids, props.items)
  if (value.length) localStorage.setItem(key.value, JSON.stringify(value))
}, { deep: true })
</script>

<template>
  <div class="kb-multi-select">
    <el-select v-model="selected" multiple collapse-tags collapse-tags-tooltip :max-collapse-tags="2"
      :multiple-limit="5" placeholder="选择 1–5 个知识库" aria-label="当前知识库范围">
      <el-option v-for="item in items" :key="item.id" :label="item.name" :value="item.id" />
    </el-select>
    <span>{{ selected.length }}/5 个库</span>
  </div>
</template>

<style scoped>
.kb-multi-select{align-items:center;display:flex;gap:8px}.kb-multi-select .el-select{min-width:280px}.kb-multi-select>span{background:#fff3e9;border:1px solid #ffd8bc;border-radius:999px;color:#bd5009;font-size:10px;font-weight:700;padding:5px 8px;white-space:nowrap}@media(max-width:760px){.kb-multi-select{align-items:stretch;flex:1;flex-direction:column}.kb-multi-select .el-select{min-width:0;width:100%}.kb-multi-select>span{align-self:flex-start}}
</style>
