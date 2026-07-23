import { defaultKnowledgeBaseIds, sanitizeKnowledgeBaseIds } from './knowledgeSelection'

const items = [
  { id: 'core', name: '小米生态核心库', status: 'active' },
  { id: 'official', name: '小米中国官方完整知识库', status: 'active' },
  { id: 'competitor', name: '竞品选购对比库', status: 'active' },
  { id: 'archived', name: '旧库', status: 'archived' },
].map((item) => ({ ...item, embedding_model: 'mock', owner_id: 'u', created_at: '' }))

describe('knowledge base multi selection', () => {
  it('defaults to core and official libraries', () => {
    expect(defaultKnowledgeBaseIds(items)).toEqual(['core', 'official'])
  })

  it('deduplicates, removes invalid libraries and limits selection to five', () => {
    expect(sanitizeKnowledgeBaseIds(['core', 'core', 'archived', 'missing', 'official'], items))
      .toEqual(['core', 'official'])
  })
})
