import { mount } from '@vue/test-utils'

import AiTracePanel from './AiTracePanel.vue'

describe('AiTracePanel', () => {
  it('is expanded by default and explains three AI calls, retrieval, and rerank decisions', () => {
    const wrapper = mount(AiTracePanel, {
      props: {
        steps: [
          { stage: 'understanding', status: 'completed', engine: 'DeepSeek', model: 'deepseek-chat', duration_ms: 21, summary: '识别意图：知识咨询' },
          { stage: 'retrieval', status: 'completed', engine: 'BGE', model: 'BAAI/bge-small-zh-v1.5', duration_ms: 8, summary: '召回 8 个候选知识片段' },
          { stage: 'reranking', status: 'completed', engine: 'DeepSeek', model: 'deepseek-chat', duration_ms: 30, summary: '从 8 个候选中保留 4 个', details: ['保留 xiaomi-14-01：直接包含电池容量'] },
          { stage: 'generation', status: 'completed', engine: 'DeepSeek', model: 'deepseek-chat', duration_ms: 45, summary: '可信回答生成完成' },
          { stage: 'grounding', status: 'completed', engine: '引用校验', model: 'source-grounding-v1', duration_ms: 1, summary: '已确认采用 2 个来源' },
        ],
      },
    })

    expect(wrapper.get('details').attributes()).toHaveProperty('open')
    expect(wrapper.text()).toContain('DeepSeek 调用 1/3')
    expect(wrapper.text()).toContain('BAAI/bge-small-zh-v1.5')
    expect(wrapper.text()).toContain('DeepSeek 调用 2/3')
    expect(wrapper.text()).toContain('DeepSeek 调用 3/3')
    expect(wrapper.text()).toContain('直接包含电池容量')
    expect(wrapper.text()).toContain('5/5 阶段')
    expect(wrapper.text()).toContain('引用校验')
  })

  it('makes a skipped generation call explicit', () => {
    const wrapper = mount(AiTracePanel, {
      props: {
        steps: [{
          stage: 'generation', status: 'skipped', engine: 'DeepSeek', model: 'deepseek-chat', duration_ms: 0,
          summary: 'DeepSeek #3 已跳过：知识库没有可靠依据',
        }],
      },
    })

    expect(wrapper.text()).toContain('已跳过')
    expect(wrapper.text()).toContain('知识库没有可靠依据')
  })
})
