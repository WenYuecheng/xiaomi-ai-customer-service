import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

const mocks = vi.hoisted(() => ({ get: vi.fn(), patch: vi.fn(), post: vi.fn(), push: vi.fn() }))
vi.mock('@/api/client', () => ({
  api: { get: mocks.get, patch: mocks.patch, post: mocks.post },
  TOKEN_KEY: 'xmcs_access_token',
}))
vi.mock('vue-router', () => ({ useRouter: () => ({ push: mocks.push }) }))

import ProfileView from './ProfileView.vue'
import { useAuthStore } from '@/stores/auth'

describe('ProfileView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    useAuthStore().replaceUser({
      id: 'user-1', username: 'customer', display_name: '探索者', avatar_key: 'cosmos',
      role: 'user', is_active: true, created_at: '2026-07-01T00:00:00Z',
    })
    mocks.push.mockReset()
    mocks.get.mockImplementation((url: string) => {
      if (url === '/account/dashboard') return Promise.resolve({ data: {
        stats: { consultation_count: 12, advisor_plan_count: 3, feedback_count: 4, helpful_rate: 75 },
        joined_days: 26, growth_level: 2,
        interests: { product_preferences: ['小米 14', 'REDMI K80'], intent_distribution: { knowledge_query: 7 } },
        trend: Array.from({ length: 14 }, (_, index) => ({ date: `2026-07-${String(index + 1).padStart(2, '0')}`, count: index % 3 })),
        recent_activities: [
          { id: 'chat:m1', type: 'chat', title: '可信问答', summary: '小米 14 的续航怎么样？', occurred_at: '2026-07-18T08:00:00Z', resource_id: 'conversation-1' },
        ],
      } })
      if (url === '/account/activities') return Promise.resolve({ data: { items: [], next_cursor: null } })
      throw new Error(`unexpected GET ${url}`)
    })
  })

  it('renders the AI personal space from real dashboard data', async () => {
    const wrapper = mount(ProfileView, {
      global: { stubs: { AppShell: { template: '<main><slot /></main>' }, ActivityTrend: true } },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('个人中心')
    expect(wrapper.text()).toContain('12')
    expect(wrapper.text()).toContain('小米 14')
    expect(wrapper.text()).toContain('小米 14 的续航怎么样？')
  })

  it('routes a chat activity back to its owned conversation', async () => {
    const wrapper = mount(ProfileView, {
      global: { stubs: { AppShell: { template: '<main><slot /></main>' }, ActivityTrend: true } },
    })
    await flushPromises()
    await wrapper.get('[data-activity-id="chat:m1"]').trigger('click')

    expect(mocks.push).toHaveBeenCalledWith({ name: 'chat', query: { conversation_id: 'conversation-1' } })
  })
})
