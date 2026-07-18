import { flushPromises, mount } from '@vue/test-utils'

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  delete: vi.fn(),
  success: vi.fn(),
  streamChat: vi.fn(),
}))

vi.mock('@/api/client', () => ({
  api: { get: mocks.get, post: mocks.post, delete: mocks.delete },
}))

vi.mock('element-plus', () => ({
  ElMessage: { success: mocks.success },
  ElMessageBox: { prompt: vi.fn() },
}))

vi.mock('@/api/chat', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/api/chat')>()
  return { ...original, streamChat: mocks.streamChat }
})

import ChatView from './ChatView.vue'
import ChatComposer from '@/components/chat/ChatComposer.vue'
import { ChatStreamError } from '@/api/chat'

describe('ChatView ticket creation', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('xmcs_last_conversation', 'conversation-1')
    mocks.get.mockImplementation((url: string) => {
      if (url === '/knowledge-bases') {
        return Promise.resolve({ data: { items: [{ id: 'kb-1', name: '验收库', status: 'active' }] } })
      }
      if (url === '/conversations/conversation-1') {
        return Promise.resolve({
          data: {
            knowledge_base_id: 'kb-1',
            messages: [{
              id: 'message-1',
              role: 'assistant',
              content: '已为你准备转人工入口。',
              fallback: false,
              sources: [],
              transfer_suggested: true,
            }],
          },
        })
      }
      if (url === '/operations/profile/me') {
        return Promise.resolve({ data: { product_preferences: [], intent_distribution: {}, feedback_summary: {}, event_count: 0 } })
      }
      if (url === '/recommendations') {
        return Promise.resolve({ data: { items: [], cold_start: true } })
      }
      throw new Error(`unexpected GET ${url}`)
    })
    mocks.post.mockResolvedValue({ data: { id: 'ticket-1' } })
    mocks.streamChat.mockReset()
  })

  it('shows a persistent created state after the user creates a ticket', async () => {
    const wrapper = mount(ChatView, {
      global: {
        stubs: {
          'el-alert': true,
          'el-button': true,
          'el-descriptions': true,
          'el-descriptions-item': true,
          'el-drawer': true,
          'el-option': true,
          'el-select': true,
        },
      },
    })
    await flushPromises()

    await wrapper.get('.transfer').trigger('click')
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledWith('/tickets', {
      conversation_id: 'conversation-1',
      priority: 'high',
    })
    expect(wrapper.get('.transfer').text()).toBe('工单已创建')
    expect(wrapper.get<HTMLButtonElement>('.transfer').element.disabled).toBe(true)
  })

  it('opens an in-app feedback panel instead of a browser-style prompt', async () => {
    const wrapper = mount(ChatView, {
      global: {
        stubs: {
          'el-alert': true,
          'el-button': true,
          'el-descriptions': true,
          'el-descriptions-item': true,
          'el-drawer': { template: '<aside><slot /><slot name="footer" /></aside>' },
          'el-option': true,
          'el-select': true,
        },
      },
    })
    await flushPromises()

    await wrapper.get('[data-testid="feedback-down"]').trigger('click')

    expect(wrapper.find('.feedback-drawer').exists()).toBe(true)
  })

  it('starts a new conversation and retries when the selected knowledge base changed', async () => {
    mocks.streamChat
      .mockRejectedValueOnce(new ChatStreamError(409, 'conversation_knowledge_mismatch', '会话与知识库不匹配'))
      .mockImplementationOnce(async (_payload, handlers) => {
        handlers.onMeta({ conversation_id: 'conversation-2', message_id: 'message-2', run_id: 'run-2' })
        handlers.onDelta('小米手机目前覆盖多个系列。')
        handlers.onSources([])
        handlers.onDone({ fallback: false, transfer_suggested: false })
      })

    const wrapper = mount(ChatView, {
      global: {
        stubs: {
          'el-alert': true,
          'el-button': true,
          'el-descriptions': true,
          'el-descriptions-item': true,
          'el-drawer': true,
          'el-option': true,
          'el-select': true,
        },
      },
    })
    await flushPromises()

    wrapper.findComponent(ChatComposer).vm.$emit('send', '小米有哪些手机？')
    await flushPromises()

    expect(mocks.streamChat).toHaveBeenCalledTimes(2)
    expect(mocks.streamChat.mock.calls[1][0].conversation_id).toBeUndefined()
    expect(wrapper.text()).toContain('小米手机目前覆盖多个系列。')
    expect(localStorage.getItem('xmcs_last_conversation')).toBe('conversation-2')
  })

  it('updates repeated streaming trace stages instead of duplicating them', async () => {
    mocks.streamChat.mockImplementationOnce(async (_payload, handlers) => {
      handlers.onMeta({ conversation_id: 'conversation-2', message_id: 'message-2', run_id: 'run-2' })
      handlers.onTrace({ stage: 'generation', status: 'running', engine: 'DeepSeek', model: 'deepseek-chat', summary: '正在生成' })
      handlers.onTrace({ stage: 'generation', status: 'completed', engine: 'DeepSeek', model: 'deepseek-chat', duration_ms: 42, summary: '生成完成' })
      handlers.onDelta('回答')
      handlers.onSources([])
      handlers.onDone({ fallback: false, transfer_suggested: false })
    })
    const wrapper = mount(ChatView, {
      global: {
        stubs: {
          'el-alert': true,
          'el-button': true,
          'el-descriptions': true,
          'el-descriptions-item': true,
          'el-drawer': true,
          'el-option': true,
          'el-select': true,
        },
      },
    })
    await flushPromises()

    wrapper.findComponent(ChatComposer).vm.$emit('send', '小米 14 的电池容量？')
    await flushPromises()

    expect(wrapper.findAll('.ai-trace__steps .is-generation')).toHaveLength(1)
    expect(wrapper.text()).toContain('生成完成')
    expect(wrapper.text()).toContain('42 ms')
  })
})
