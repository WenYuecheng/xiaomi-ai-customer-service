import { mount } from '@vue/test-utils'

import ChangePasswordDialog from './ChangePasswordDialog.vue'

describe('ChangePasswordDialog', () => {
  it('blocks mismatched passwords and emits a valid password change', async () => {
    const wrapper = mount(ChangePasswordDialog, { props: { open: true } })
    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('Current123')
    await inputs[1].setValue('NewSecure123')
    await inputs[2].setValue('Different123')
    await wrapper.get('form').trigger('submit')
    expect(wrapper.text()).toContain('两次输入的新密码不一致')
    expect(wrapper.emitted('changePassword')).toBeUndefined()

    await inputs[2].setValue('NewSecure123')
    await wrapper.get('form').trigger('submit')
    expect(wrapper.emitted('changePassword')?.[0]).toEqual([{
      current_password: 'Current123',
      new_password: 'NewSecure123',
      new_password_confirm: 'NewSecure123',
    }])
  })
})
