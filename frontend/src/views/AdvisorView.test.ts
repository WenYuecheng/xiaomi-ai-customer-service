import { flushPromises, mount } from '@vue/test-utils'

const mocks = vi.hoisted(() => ({ get: vi.fn(), delete: vi.fn(), streamAdvisor: vi.fn() }))
vi.mock('@/api/client', () => ({ api: { get: mocks.get, delete: mocks.delete } }))
vi.mock('@/api/advisor', () => ({ streamAdvisor: mocks.streamAdvisor }))

import AdvisorView from './AdvisorView.vue'
import AdvisorBriefForm from '@/components/advisor/AdvisorBriefForm.vue'

describe('AdvisorView', () => {
  beforeEach(() => {
    mocks.get.mockImplementation((url: string) => {
      if (url === '/knowledge-bases') return Promise.resolve({ data: { items: [{ id: 'kb-1', name: '官方资料', status: 'active' }] } })
      if (url === '/advisor/sessions') return Promise.resolve({ data: { items: [] } })
      throw new Error(`unexpected GET ${url}`)
    })
    mocks.streamAdvisor.mockImplementation(async (_url, _payload, handlers) => {
      handlers.onMeta({ session_id: 'session-1', turn_id: 'turn-1' })
      handlers.onTrace({ stage: 'understanding', status: 'completed', engine: 'DeepSeek', model: 'deepseek-chat', summary: '已理解预算和偏好' })
      handlers.onAdvisor({ title: 'AI 手机选购方案', interpreted_need: '重视续航', candidates: [], comparison_rows: [], recommendation: { primary_model: '小米 14', summary: '推荐', reasons: [], caveats: [] }, follow_up_suggestions: [] }, 'turn-1')
      handlers.onSources([])
      handlers.onDone({ status: 'completed' })
    })
  })

  it('shows the visible AI lab and streams a submitted brief', async () => {
    const wrapper = mount(AdvisorView, {
      global: {
        stubs: {
          'el-alert': true, 'el-button': true, 'el-input': true, 'el-input-number': true,
          'el-option': true, 'el-select': true, 'el-slider': true,
          AdvisorPlanCard: { template: '<div class="plan-stub">{{ plan.title }}</div>', props: ['plan', 'sources'] },
          AiTracePanel: true,
        },
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('AI 智能选购实验室')
    wrapper.findComponent(AdvisorBriefForm).vm.$emit('submit', {
      knowledge_base_id: 'kb-1', message: '推荐续航好的手机', category: 'phone',
      mode: 'purchase_advice', priorities: ['battery'], product_models: [],
    })
    await flushPromises()

    expect(mocks.streamAdvisor).toHaveBeenCalledOnce()
    expect(wrapper.text()).toContain('AI 手机选购方案')
  })
})
