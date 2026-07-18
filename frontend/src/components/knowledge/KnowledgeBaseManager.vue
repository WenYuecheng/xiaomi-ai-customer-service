<script setup lang="ts">
import { computed, reactive, shallowRef } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { api } from '@/api/client'
import type { KnowledgeBase } from '@/types'

const props = defineProps<{ items: KnowledgeBase[]; loading: boolean }>()
const emit = defineEmits<{ refresh: []; select: [id: string] }>()
const query = shallowRef('')
const statusFilter = shallowRef('')
const form = reactive({ name: '', description: '' })
const filtered = computed(() => props.items.filter((item) =>
  (!query.value || item.name.toLowerCase().includes(query.value.toLowerCase()))
  && (!statusFilter.value || item.status === statusFilter.value),
))
const knowledgeBaseRow = (value: unknown): KnowledgeBase => value as KnowledgeBase

async function createItem(): Promise<void> {
  await api.post('/knowledge-bases', form)
  form.name = ''; form.description = ''
  ElMessage.success('知识库已创建')
  emit('refresh')
}

async function editItem(item: KnowledgeBase): Promise<void> {
  const { value } = await ElMessageBox.prompt('请输入新的知识库名称', '编辑知识库', {
    inputValue: item.name,
    inputValidator: (text) => Boolean(text.trim()) || '名称不能为空',
  })
  await api.patch(`/knowledge-bases/${item.id}`, { name: value.trim() })
  ElMessage.success('知识库已更新')
  emit('refresh')
}

async function toggleArchive(item: KnowledgeBase): Promise<void> {
  const status = item.status === 'active' ? 'archived' : 'active'
  await api.patch(`/knowledge-bases/${item.id}`, { status })
  ElMessage.success(status === 'active' ? '知识库已启用' : '知识库已归档')
  emit('refresh')
}

async function removeItem(item: KnowledgeBase): Promise<void> {
  await ElMessageBox.confirm(`确认删除“${item.name}”？知识库必须为空。`, '删除确认', { type: 'warning' })
  await api.delete(`/knowledge-bases/${item.id}`)
  ElMessage.success('知识库已删除')
  emit('refresh')
}
</script>

<template>
  <el-card shadow="never" class="manager-card">
    <template #header><strong>知识库管理</strong></template>
    <el-form :model="form" inline @submit.prevent="createItem">
      <el-form-item><el-input v-model="form.name" maxlength="100" placeholder="知识库名称" /></el-form-item>
      <el-form-item><el-input v-model="form.description" maxlength="2000" placeholder="描述（可选）" /></el-form-item>
      <el-form-item><el-button type="primary" native-type="submit" :disabled="!form.name.trim()">创建</el-button></el-form-item>
    </el-form>
    <div class="filters">
      <el-input v-model="query" clearable placeholder="按名称筛选" />
      <el-select v-model="statusFilter" clearable placeholder="全部状态"><el-option label="启用" value="active" /><el-option label="已归档" value="archived" /></el-select>
    </div>
    <el-table v-loading="loading" :data="filtered" @row-click="(row: KnowledgeBase) => emit('select', row.id)">
      <el-table-column prop="name" label="名称" min-width="180" />
      <el-table-column prop="description" label="描述" min-width="220" show-overflow-tooltip />
      <el-table-column prop="embedding_model" label="Embedding" min-width="170" />
      <el-table-column prop="status" label="状态" width="90" />
      <el-table-column label="操作" width="230">
        <template #default="scope">
          <el-button link @click.stop="editItem(knowledgeBaseRow(scope.row))">编辑</el-button>
          <el-button link @click.stop="toggleArchive(knowledgeBaseRow(scope.row))">{{ scope.row.status === 'active' ? '归档' : '启用' }}</el-button>
          <el-button link type="danger" @click.stop="removeItem(knowledgeBaseRow(scope.row))">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<style scoped>
.manager-card { margin-bottom: 18px; }
.filters { display: grid; gap: 10px; grid-template-columns: minmax(220px, 1fr) 180px; margin-bottom: 16px; }
@media (max-width: 680px) { .filters { grid-template-columns: 1fr; } }
</style>
