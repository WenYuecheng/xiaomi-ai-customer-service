import { mount } from '@vue/test-utils'

import RegisterForm from './RegisterForm.vue'

describe('RegisterForm', () => {
  it('shows password strength and emits a valid registration', async () => {
    const wrapper = mount(RegisterForm, {
      global: { stubs: { 'el-button': { template: '<button type="submit"><slot /></button>' } } },
    })
    const inputs = wrapper.findAll('input')

    await inputs[0].setValue('new_user')
    await inputs[1].setValue('Password123')
    await inputs[2].setValue('Password123')
    await wrapper.get('form').trigger('submit')

    expect(wrapper.text()).toContain('密码强度：较强')
    expect(wrapper.emitted('register')?.[0]).toEqual([{
      username: 'new_user', password: 'Password123', passwordConfirm: 'Password123',
    }])
  })

  it('shows field-level mismatch feedback instead of submitting', async () => {
    const wrapper = mount(RegisterForm, {
      global: { stubs: { 'el-button': { template: '<button type="submit"><slot /></button>' } } },
    })
    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('new_user')
    await inputs[1].setValue('Password123')
    await inputs[2].setValue('Different123')
    await wrapper.get('form').trigger('submit')

    expect(wrapper.text()).toContain('两次输入的密码不一致')
    expect(wrapper.emitted('register')).toBeUndefined()
  })
})
