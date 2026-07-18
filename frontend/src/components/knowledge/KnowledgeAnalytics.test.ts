import { flushPromises, mount } from '@vue/test-utils'
import { nextTick } from 'vue'

const mocks = vi.hoisted(() => ({ get: vi.fn(), init: vi.fn(), setOption: vi.fn() }))

vi.mock('@/api/client', () => ({ api: { get: mocks.get } }))
vi.mock('echarts/core', () => ({
  init: (element: HTMLElement) => {
    mocks.init(element)
    return { setOption: mocks.setOption, resize: vi.fn(), dispose: vi.fn() }
  },
  use: vi.fn(),
}))
vi.mock('echarts/charts', () => ({ GraphChart: {} }))
vi.mock('echarts/components', () => ({ LegendComponent: {}, TooltipComponent: {} }))
vi.mock('echarts/renderers', () => ({ CanvasRenderer: {} }))

import KnowledgeAnalytics from './KnowledgeAnalytics.vue'
import knowledgeAnalyticsSource from './KnowledgeAnalytics.vue?raw'

describe('KnowledgeAnalytics', () => {
  it('does not shadow the chart template ref in production compilation', () => {
    expect(knowledgeAnalyticsSource).not.toMatch(/\blet chart\b/)
  })

  it('renders coverage metrics and the derived knowledge graph', async () => {
    const animationFrame = vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback) => {
      callback(performance.now() + 2000)
      return 1
    })
    mocks.get.mockImplementation((url: string) => {
      if (url.endsWith('/analytics')) return Promise.resolve({ data: {
        document_count: 64, chunk_count: 186, product_count: 28, ready_count: 63,
        failed_count: 1, source_coverage: 0.9844, categories: [{ name: '手机', count: 12 }],
      } })
      return Promise.resolve({ data: {
        nodes: [{ id: 'kb:1', label: '正式库', kind: 'knowledge_base', value: 64 }],
        edges: [],
      } })
    })

    const wrapper = mount(KnowledgeAnalytics, {
      props: { knowledgeBaseId: 'kb-1' },
      global: {
        stubs: { 'el-empty': true },
        directives: { loading: {} },
      },
    })
    await flushPromises()
    await nextTick()

    expect((wrapper.vm as unknown as { analytics: { document_count: number } }).analytics.document_count).toBe(64)
    expect(wrapper.text()).toContain('64')
    expect(wrapper.text()).toContain('186')
    expect(wrapper.text()).toContain('98%')
    expect(wrapper.find('[data-testid="knowledge-graph"]').exists()).toBe(true)
    expect(mocks.init).toHaveBeenCalledWith(wrapper.get('[data-testid="knowledge-graph"]').element)
    expect(mocks.setOption).toHaveBeenCalled()
    animationFrame.mockRestore()
  })
})
