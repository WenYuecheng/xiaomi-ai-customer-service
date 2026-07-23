import { createPinia, setActivePinia } from 'pinia'

const mocks = vi.hoisted(() => ({ post: vi.fn(), get: vi.fn() }))
vi.mock('@/api/client', () => ({
  api: { post: mocks.post, get: mocks.get },
  TOKEN_KEY: 'xmcs_access_token',
}))

import { useAuthStore } from './auth'

describe('auth store registration', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    mocks.post.mockReset()
  })

  it('stores the returned session and user without a second request', async () => {
    mocks.post.mockResolvedValue({
      data: {
        access_token: 'registered-token',
        token_type: 'bearer',
        user: {
          id: 'user-1', username: 'new_user', display_name: 'new_user',
          avatar_key: 'aurora', role: 'user', is_active: true, created_at: '2026-07-18T00:00:00Z',
        },
      },
    })
    const auth = useAuthStore()

    await auth.register('new_user', 'Password123', 'Password123')

    expect(mocks.post).toHaveBeenCalledWith('/auth/register', {
      username: 'new_user', password: 'Password123', password_confirm: 'Password123',
    })
    expect(auth.user?.display_name).toBe('new_user')
    expect(localStorage.getItem('xmcs_access_token')).toBe('registered-token')
  })
})
