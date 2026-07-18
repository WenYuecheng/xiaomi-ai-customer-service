import { mount } from '@vue/test-utils'

import AiTracePanel from './AiTracePanel.vue'

describe('AiTracePanel', () => {
  it('is expanded by default and explains the two AI calls and retrieval', () => {
    const wrapper = mount(AiTracePanel, {
      props: {
        steps: [
          { stage: 'understanding', status: 'completed', engine: 'DeepSeek', model: 'deepseek-chat', duration_ms: 21, summary: '识别意图：知识咨询' },
          { stage: 'retrieval', status: 'completed', engine: 'BGE', model: 'BAAI/bge-small-zh-v1.5', duration_ms: 8, summary: '召回 3 个可靠知识片段' },
          { stage: 'generation', status: 'completed', engine: 'DeepSeek', model: 'deepseek-chat', duration_ms: 45, summary: '可信回答生成完成' },
          { stage: 'grounding', status: 'completed', engine: '引用校验', model: 'source-grounding-v1', duration_ms: 1, summary: '已确认采用 2 个来源' },
        ],
      },
    })

    expect(wrapper.get('details').attributes()).toHaveProperty('open')
    expect(wrapper.text()).toContain('DeepSeek 调用 1/2')
    expect(wrapper.text()).toContain('BAAI/bge-small-zh-v1.5')
    expect(wrapper.text()).toContain('DeepSeek 调用 2/2')
    expect(wrapper.text()).toContain('引用校验')
  })

  it('makes a skipped second call explicit', () => {
    const wrapper = mount(AiTracePanel, {
      props: {
        steps: [{
          stage: 'generation', status: 'skipped', engine: 'DeepSeek', model: 'deepseek-chat', duration_ms: 0,
          summary: 'DeepSeek #2 已跳过：知识库没有可靠依据',
        }],
      },
    })

    expect(wrapper.text()).toContain('已跳过')
    expect(wrapper.text()).toContain('知识库没有可靠依据')
  })
})
