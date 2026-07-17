import { mount } from '@vue/test-utils'

import ChatMessage from './ChatMessage.vue'

describe('ChatMessage', () => {
  it('renders a grounded answer and its evidence source', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        message: {
          id: 'm1',
          role: 'assistant',
          content: '小米 14 支持 **90W** 快充。',
          fallback: false,
          sources: [
            {
              document_id: 'd1',
              chunk_id: 'c1',
              filename: 'xiaomi14.md',
              location: '第 1 页',
              snippet: '小米 14 支持 90W 快充。',
              score: 0.91,
            },
          ],
        },
      },
    })

    expect(wrapper.text()).toContain('90W')
    expect(wrapper.text()).toContain('xiaomi14.md')
    expect(wrapper.find('[data-testid="source-rail"]').exists()).toBe(true)
  })

  it('shows the explicit fallback state without an empty source rail', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        message: {
          id: 'm2',
          role: 'assistant',
          content: '未找到可靠依据。',
          fallback: true,
          sources: [],
        },
      },
    })

    expect(wrapper.text()).toContain('知识库暂无可靠答案')
    expect(wrapper.find('[data-testid="source-rail"]').exists()).toBe(false)
  })
})

