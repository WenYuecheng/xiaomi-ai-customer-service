<script setup lang="ts">
import type { AdvisorSessionSummary } from '@/types'

defineProps<{ sessions: readonly AdvisorSessionSummary[]; activeId?: string }>()
const emit = defineEmits<{ select: [id: string]; delete: [id: string] }>()
</script>

<template>
  <aside class="history-panel">
    <header><span>方案档案</span><b>{{ sessions.length }}</b></header>
    <p v-if="!sessions.length" class="empty">生成的方案会按当前账号安全保存。</p>
    <article v-for="item in sessions" :key="item.id" :class="{ active: item.id === activeId }" @click="emit('select', item.id)">
      <div><strong>{{ item.title }}</strong><small>{{ item.turn_count }} 轮调整</small></div>
      <button type="button" aria-label="删除方案" @click.stop="emit('delete', item.id)">×</button>
    </article>
  </aside>
</template>

<style scoped>
.history-panel { background: rgba(255,255,255,.76); border: 1px solid #e4def1; border-radius: 21px; padding: 15px; }.history-panel header { align-items: center; display: flex; justify-content: space-between; margin-bottom: 10px; }.history-panel header span { color: #635872; font-size: 11px; font-weight: 700; }.history-panel header b { background: #ece6fb; border-radius: 999px; color: #644bb9; font-size: 10px; padding: 3px 7px; }.history-panel article { align-items: center; border: 1px solid transparent; border-radius: 13px; cursor: pointer; display: flex; gap: 8px; justify-content: space-between; margin-top: 7px; padding: 10px; }.history-panel article:hover,.history-panel article.active { background: #f0ecfb; border-color: #ded5f4; }.history-panel article div { display: grid; gap: 3px; min-width: 0; }.history-panel strong { color: #463d57; font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.history-panel small,.empty { color: #91879e; font-size: 9px; }.history-panel button { background: transparent; border: 0; color: #9c91aa; cursor: pointer; font-size: 16px; }
</style>
