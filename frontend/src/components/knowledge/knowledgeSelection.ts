import type { KnowledgeBase } from '@/types'

export const KNOWLEDGE_SELECTION_STORAGE_KEY = 'xmcs_knowledge_base_ids'

export function sanitizeKnowledgeBaseIds(ids: readonly string[], items: readonly KnowledgeBase[]): string[] {
  const valid = new Set(items.filter((item) => item.status === 'active').map((item) => item.id))
  return [...new Set(ids)].filter((id) => valid.has(id)).slice(0, 5)
}

export function defaultKnowledgeBaseIds(items: readonly KnowledgeBase[]): string[] {
  const active = items.filter((item) => item.status === 'active')
  const defaults = [
    active.find((item) => item.name.includes('小米生态核心库')),
    active.find((item) => item.name.includes('小米中国官方完整知识库')),
  ].filter((item): item is KnowledgeBase => Boolean(item))
  return sanitizeKnowledgeBaseIds(defaults.map((item) => item.id), active).length
    ? sanitizeKnowledgeBaseIds(defaults.map((item) => item.id), active)
    : active.slice(0, 1).map((item) => item.id)
}
