import { mount } from '@vue/test-utils'

import ChatMessage from './ChatMessage.vue'

describe('ChatMessage', () => {
  it('places the user identity after the message body on the right', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        message: {
          id: 'user-message',
          role: 'user',
          content: '小米 14',
          fallback: false,
          sources: [],
        },
      },
    })

    const body = wrapper.get('.message__body')
    const identity = wrapper.get('.message__identity')

    expect(wrapper.classes()).toContain('message--user')
    expect(identity.text()).toBe('你')
    expect(body.element.nextElementSibling).toBe(identity.element)
  })

  it('keeps the assistant identity before the answer body on the left', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        message: {
          id: 'assistant-message',
          role: 'assistant',
          content: '这是小爱客服的回答。',
          fallback: false,
          sources: [],
        },
      },
    })

    const body = wrapper.get('.message__body')
    const identity = wrapper.get('.message__identity')

    expect(wrapper.classes()).toContain('message--assistant')
    expect(identity.text()).toBe('小爱客服')
    expect(identity.element.nextElementSibling).toBe(body.element)
  })

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

  it('shows an accessible selected state after helpful feedback', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        message: {
          id: 'm3', role: 'assistant', content: '答案', fallback: false, sources: [],
        },
        feedbackRating: 'up',
      },
    })

    const helpful = wrapper.get('[data-testid="feedback-up"]')
    expect(helpful.attributes('aria-pressed')).toBe('true')
    expect(helpful.text()).toContain('已记录')
  })
})

it('renders a safe clickable public source URL', () => {
  const wrapper = mount(ChatMessage, {
    props: {
      message: {
        id: 'm2',
        role: 'assistant',
        content: '答案',
        fallback: false,
        sources: [{
          document_id: 'd1', chunk_id: 'c1', filename: 'guide.md', location: '第 1 节',
          snippet: '证据', score: 0.9, source_url: 'https://www.mi.com/example',
        }],
      },
    },
  })

  expect(wrapper.get('a').attributes('href')).toBe('https://www.mi.com/example')
  expect(wrapper.get('a').attributes('rel')).toContain('noopener')
})
