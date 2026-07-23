import { mount } from '@vue/test-utils'

import AdvisorPlanCard from './AdvisorPlanCard.vue'

describe('AdvisorPlanCard', () => {
  it('renders evidence-backed candidates, comparison and price status', () => {
    const wrapper = mount(AdvisorPlanCard, {
      props: {
        plan: {
          title: '手机 AI 选购方案',
          interpreted_need: '重视续航和屏幕',
          candidates: [{
            model: '小米 14',
            fit_score: 91,
            highlights: ['4610mAh 电池'],
            tradeoffs: ['价格以官网为准'],
            dimension_scores: { battery: 90, screen: 84 },
            source_chunk_ids: ['chunk-1'],
            price: { status: 'unavailable', display: '价格待官网确认' },
          }],
          comparison_rows: [{ dimension: '电池', values: { '小米 14': '4610mAh' } }],
          recommendation: {
            primary_model: '小米 14',
            summary: '更符合均衡需求',
            reasons: ['续航资料完整'],
            caveats: ['购买前核对官网'],
          },
          follow_up_suggestions: ['如果更重视便携性呢？'],
        },
        sources: [],
      },
      global: { stubs: { AdvisorRadar: true, SourceRail: true } },
    })

    expect(wrapper.text()).toContain('91%')
    expect(wrapper.text()).toContain('4610mAh')
    expect(wrapper.text()).toContain('价格待官网确认')
    expect(wrapper.text()).toContain('AI 需求匹配评分')
  })

  it('emits a follow-up question from a suggestion chip', async () => {
    const wrapper = mount(AdvisorPlanCard, {
      props: {
        plan: {
          title: '选购方案', interpreted_need: '需求',
          candidates: [{ model: '小米 14', fit_score: 90, highlights: [], tradeoffs: [], dimension_scores: {}, source_chunk_ids: ['c1'], price: { status: 'unavailable', display: '价格待官网确认' } }],
          comparison_rows: [],
          recommendation: { primary_model: '小米 14', summary: '推荐', reasons: [], caveats: [] },
          follow_up_suggestions: ['更重视续航呢？'],
        },
        sources: [],
      },
      global: { stubs: { AdvisorRadar: true, SourceRail: true } },
    })

    await wrapper.get('[data-testid="advisor-follow-up"]').trigger('click')
    expect(wrapper.emitted('followUp')?.[0]).toEqual(['更重视续航呢？'])
  })
})
