<script setup lang="ts">
import { computed, shallowRef } from 'vue'

const props = defineProps<{ busy: boolean; disabled?: boolean }>()
const emit = defineEmits<{ send: [message: string]; stop: [] }>()
const text = shallowRef('')
const canSend = computed(() => Boolean(text.value.trim()) && !props.busy && !props.disabled)

function submit(): void {
  if (!canSend.value) return
  emit('send', text.value.trim())
  text.value = ''
}
</script>

<template>
  <form class="composer" @submit.prevent="submit">
    <el-input
      v-model="text"
      type="textarea"
      :autosize="{ minRows: 1, maxRows: 6 }"
      resize="none"
      maxlength="4000"
      show-word-limit
      placeholder="输入产品型号和你的问题，例如：小米 14 支持多少瓦快充？"
      @keydown.ctrl.enter.prevent="submit"
    />
    <div class="composer__footer">
      <span><i /> 已启用知识库约束与引用追踪 · Ctrl + Enter 发送</span>
      <el-button v-if="busy" type="danger" plain @click="emit('stop')">停止生成</el-button>
      <el-button v-else type="primary" native-type="submit" :disabled="!canSend">发送问题</el-button>
    </div>
  </form>
</template>

<style scoped>
.composer{background:#fff;border:1px solid #d8d4ce;border-radius:16px;box-shadow:0 12px 32px rgba(30,27,24,.08);padding:11px}
.composer__footer { align-items: center; display: flex; justify-content: space-between; padding: 10px 2px 0; }
.composer__footer span { color: var(--ink-muted); font-size: 12px; }
.composer__footer span i{background:#25a66f;border-radius:50%;display:inline-block;height:6px;margin-right:6px;width:6px}
@media(max-width:560px){.composer__footer span{font-size:9px}}
</style>
