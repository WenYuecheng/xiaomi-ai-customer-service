<script setup lang="ts">
import { computed, reactive, watch } from 'vue'

import type { KnowledgeBase } from '@/types'

type Category = 'phone' | 'tablet' | 'wearable' | 'robot_vacuum'
interface BriefPayload {
  knowledge_base_id: string
  message: string
  mode: 'comparison' | 'purchase_advice'
  category: Category
  product_models: string[]
  budget_min?: number
  budget_max?: number
  priorities: string[]
}

const props = defineProps<{ knowledgeBases: readonly KnowledgeBase[]; busy: boolean }>()
const emit = defineEmits<{ submit: [payload: BriefPayload] }>()

const categories: Array<{ value: Category; icon: string; label: string; copy: string }> = [
  { value: 'phone', icon: '▯', label: '手机', copy: '影像、性能与续航' },
  { value: 'tablet', icon: '▭', label: '平板', copy: '生产力、屏幕与便携' },
  { value: 'wearable', icon: '◉', label: '智能穿戴', copy: '健康、运动与续航' },
  { value: 'robot_vacuum', icon: '◎', label: '扫地机器人', copy: '清洁力、导航与避障' },
]
const priorityOptions: Record<Category, Array<{ value: string; label: string }>> = {
  phone: [{ value: 'camera', label: '影像' }, { value: 'performance', label: '性能' }, { value: 'battery', label: '续航' }, { value: 'screen', label: '屏幕' }, { value: 'portability', label: '便携' }],
  tablet: [{ value: 'productivity', label: '生产力' }, { value: 'screen', label: '屏幕' }, { value: 'performance', label: '性能' }, { value: 'battery', label: '续航' }, { value: 'portability', label: '便携' }],
  wearable: [{ value: 'health', label: '健康' }, { value: 'sports', label: '运动' }, { value: 'battery', label: '续航' }, { value: 'comfort', label: '舒适' }, { value: 'connectivity', label: '连接' }],
  robot_vacuum: [{ value: 'cleaning_power', label: '清洁力' }, { value: 'navigation', label: '导航' }, { value: 'obstacle_avoidance', label: '避障' }, { value: 'self_cleaning', label: '自清洁' }, { value: 'battery', label: '续航' }],
}

const form = reactive({
  knowledge_base_id: '', category: 'phone' as Category, mode: 'purchase_advice' as const,
  models: '', budget_min: undefined as number | undefined, budget_max: undefined as number | undefined,
  priorities: ['battery'], message: '请根据我的预算和关注重点，推荐最合适的产品并说明取舍。',
})
const priorities = computed(() => priorityOptions[form.category])

watch(() => props.knowledgeBases, (items) => {
  if (!items.some((item) => item.id === form.knowledge_base_id)) form.knowledge_base_id = items[0]?.id ?? ''
}, { immediate: true })
watch(() => form.category, () => { form.priorities = [priorityOptions[form.category][0].value] })

function togglePriority(value: string): void {
  form.priorities = form.priorities.includes(value)
    ? form.priorities.filter((item) => item !== value)
    : [...form.priorities, value].slice(0, 5)
}

function submit(): void {
  if (!form.knowledge_base_id || !form.message.trim()) return
  emit('submit', {
    knowledge_base_id: form.knowledge_base_id,
    message: form.message.trim(),
    mode: form.mode,
    category: form.category,
    product_models: form.models.split(/[,，|]/).map((item) => item.trim()).filter(Boolean).slice(0, 4),
    budget_min: form.budget_min,
    budget_max: form.budget_max,
    priorities: form.priorities,
  })
}
</script>

<template>
  <form class="brief-console" @submit.prevent="submit">
    <div class="console-top"><span>01 / SELECT DOMAIN</span><b>告诉 AI 你在选什么</b></div>
    <div class="category-grid">
      <button v-for="item in categories" :key="item.value" type="button" :class="{ selected: form.category === item.value }" @click="form.category = item.value">
        <i>{{ item.icon }}</i><strong>{{ item.label }}</strong><small>{{ item.copy }}</small>
      </button>
    </div>
    <div class="field-grid">
      <label><span>知识库</span><el-select v-model="form.knowledge_base_id"><el-option v-for="item in knowledgeBases" :key="item.id" :label="item.name" :value="item.id" /></el-select></label>
      <label><span>方案类型</span><el-select v-model="form.mode"><el-option label="智能推荐" value="purchase_advice" /><el-option label="指定型号对比" value="comparison" /></el-select></label>
      <label class="model-field"><span>候选型号（可选，用逗号分隔）</span><el-input v-model="form.models" placeholder="例如：小米 14，REDMI K80" /></label>
      <label><span>预算下限</span><el-input-number v-model="form.budget_min" :min="0" :max="100000" :step="500" controls-position="right" /></label>
      <label><span>预算上限</span><el-input-number v-model="form.budget_max" :min="0" :max="100000" :step="500" controls-position="right" /></label>
    </div>
    <div class="priority-section"><span>最关注什么</span><div><button v-for="item in priorities" :key="item.value" type="button" :class="{ selected: form.priorities.includes(item.value) }" @click="togglePriority(item.value)">{{ item.label }}</button></div></div>
    <label class="question-field"><span>补充你的使用场景</span><el-input v-model="form.message" type="textarea" :rows="3" maxlength="4000" show-word-limit /></label>
    <button class="launch-button" type="submit" :disabled="busy || !form.knowledge_base_id"><span>{{ busy ? 'AI 正在执行三段分析…' : '启动 3 次 DeepSeek 智能选购' }}</span><i>→</i></button>
  </form>
</template>

<style scoped>
.brief-console { background: #1b1628; border: 1px solid #3b3153; border-radius: 26px; box-shadow: 0 30px 70px rgba(30,20,52,.22); color: white; padding: 22px; }.console-top { align-items: center; display: flex; justify-content: space-between; margin-bottom: 16px; }.console-top span { color: #a990ff; font-family: var(--font-mono); font-size: 9px; letter-spacing: .15em; }.console-top b { color: #ddd5ed; font-size: 12px; }
.category-grid { display: grid; gap: 9px; grid-template-columns: repeat(4,1fr); }.category-grid button { background: #241d35; border: 1px solid #423655; border-radius: 16px; color: #cfc5de; cursor: pointer; display: grid; gap: 4px; min-height: 102px; padding: 13px; text-align: left; }.category-grid button.selected { background: linear-gradient(145deg,#6243cb,#9d4dcc); border-color: #b79cf7; box-shadow: 0 10px 28px rgba(117,72,215,.3); }.category-grid i { color: #d5c5ff; font-size: 24px; font-style: normal; }.category-grid strong { font-size: 13px; }.category-grid small { font-size: 9px; opacity: .66; }
.field-grid { display: grid; gap: 11px; grid-template-columns: 1fr 1fr; margin-top: 16px; }.field-grid label,.question-field { display: grid; gap: 6px; }.field-grid label>span,.question-field>span,.priority-section>span { color: #a99db9; font-size: 10px; }.model-field { grid-column: 1/-1; }.brief-console :deep(.el-input__wrapper),.brief-console :deep(.el-select__wrapper),.brief-console :deep(.el-textarea__inner) { background: #282039; box-shadow: 0 0 0 1px #463a5d inset; color: white; }.brief-console :deep(input),.brief-console :deep(textarea) { color: #f5f1fb; }.brief-console :deep(.el-input-number) { width: 100%; }
.priority-section { margin: 16px 0; }.priority-section>div { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 7px; }.priority-section button { background: #29213b; border: 1px solid #44375a; border-radius: 999px; color: #bfb3cf; cursor: pointer; padding: 7px 12px; }.priority-section button.selected { background: #eee8ff; border-color: #eee8ff; color: #5638b5; }.launch-button { align-items: center; background: linear-gradient(90deg,#ff6900,#f24f9c,#7958ed); border: 0; border-radius: 15px; color: white; cursor: pointer; display: flex; font-weight: 720; justify-content: space-between; margin-top: 15px; padding: 14px 17px; width: 100%; }.launch-button i { font-size: 20px; font-style: normal; }.launch-button:disabled { cursor: wait; filter: grayscale(.45); opacity: .7; }
@media (max-width: 700px) { .category-grid { grid-template-columns: 1fr 1fr; }.field-grid { grid-template-columns: 1fr; }.model-field { grid-column: auto; } }
</style>
