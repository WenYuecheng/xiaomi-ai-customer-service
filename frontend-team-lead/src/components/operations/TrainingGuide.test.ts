import { mount } from '@vue/test-utils'

import TrainingGuide from './TrainingGuide.vue'

describe('TrainingGuide', () => {
  it('explains the selected goal and emits a concrete training target', async () => {
    const wrapper = mount(TrainingGuide, {
      props: { runs: [], busy: false },
      global: { stubs: { 'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }, 'el-empty': true } },
    })

    await wrapper.get('[data-testid="goal-recall"]').trigger('click')
    expect(wrapper.text()).toContain('尽量找回用户可能喜欢的产品')
    await wrapper.get('[data-testid="start-training"]').trigger('click')

    expect(wrapper.emitted('train')?.[0]).toEqual(['recall'])
  })
})
