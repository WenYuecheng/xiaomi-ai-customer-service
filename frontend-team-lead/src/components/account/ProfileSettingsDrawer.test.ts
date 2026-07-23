import { mount } from '@vue/test-utils'

import ProfileSettingsDrawer from './ProfileSettingsDrawer.vue'

const user = {
  id: 'u1', username: 'customer', display_name: '探索者', avatar_key: 'aurora' as const,
  role: 'user' as const, is_active: true, created_at: '2026-07-01T00:00:00Z',
}

describe('ProfileSettingsDrawer', () => {
  it('emits a trimmed display name and selected preset avatar', async () => {
    const wrapper = mount(ProfileSettingsDrawer, { props: { open: true, user } })
    await wrapper.get('input[name="display-name"]').setValue('  星河用户  ')
    await wrapper.get('[data-avatar="cosmos"]').trigger('click')
    await wrapper.get('form').trigger('submit')

    expect(wrapper.findAll('.avatar-options [data-avatar]')).toHaveLength(8)
    expect(wrapper.emitted('save')?.[0]).toEqual([{ display_name: '星河用户', avatar_key: 'cosmos' }])
  })
})
