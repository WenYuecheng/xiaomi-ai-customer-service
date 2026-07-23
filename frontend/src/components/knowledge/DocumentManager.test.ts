import { flushPromises, mount } from '@vue/test-utils'

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  success: vi.fn(),
}))

vi.mock('@/api/client', () => ({ api: { get: mocks.get, post: mocks.post, delete: vi.fn() } }))
vi.mock('element-plus', () => ({
  ElMessage: { success: mocks.success },
  ElMessageBox: { confirm: vi.fn() },
}))

import DocumentManager from './DocumentManager.vue'

const knowledgeBases = [{
  id: 'kb-1',
  name: '文件上传验收库',
  status: 'active',
  embedding_model: 'mock',
  owner_id: 'operator',
  created_at: '2026-07-23T00:00:00Z',
}]

function mountManager() {
  return mount(DocumentManager, {
    props: { knowledgeBases, selectedId: 'kb-1' },
    global: {
      stubs: {
        'el-button': true,
        'el-card': { template: '<section><slot name="header"/><slot/></section>' },
        'el-dialog': true,
        'el-icon': true,
        'el-input': true,
        'el-input-number': true,
        'el-option': true,
        'el-progress': true,
        'el-select': true,
        'el-table': true,
        'el-table-column': true,
        'el-tag': true,
      },
    },
  })
}

describe('DocumentManager uploads', () => {
  beforeEach(() => {
    mocks.get.mockImplementation((url: string) => {
      if (url === '/documents') return Promise.resolve({ data: { items: [] } })
      if (url === '/jobs') return Promise.resolve({ data: { items: [] } })
      throw new Error(`unexpected GET ${url}`)
    })
    mocks.post.mockReset()
  })

  it('does not recursively reopen the chooser when the hidden input click bubbles', async () => {
    const wrapper = mountManager()
    await flushPromises()
    const input = wrapper.get<HTMLInputElement>('input[type="file"]')
    const clickSpy = vi.spyOn(input.element, 'click')

    await input.trigger('click')

    expect(clickSpy).not.toHaveBeenCalled()
  })

  it('continues a batch after one file fails and shows per-file results', async () => {
    mocks.post
      .mockRejectedValueOnce(new Error('文件内容与声明格式不匹配'))
      .mockResolvedValueOnce({ data: { job_id: 'job-2' } })
    const wrapper = mountManager()
    await flushPromises()
    const input = wrapper.get<HTMLInputElement>('input[type="file"]')
    Object.defineProperty(input.element, 'files', {
      configurable: true,
      value: [
        new File(['not pdf'], 'bad.pdf', { type: 'application/pdf' }),
        new File(['UPLOAD-TXT-20260723'], 'good.txt', { type: 'text/plain' }),
      ],
    })

    await input.trigger('change')
    await flushPromises()

    expect(mocks.post).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('bad.pdf')
    expect(wrapper.text()).toContain('文件内容与声明格式不匹配')
    expect(wrapper.text()).toContain('good.txt')
    expect(wrapper.text()).toContain('已进入处理队列')
  })

  it('updates a queued upload to success when the worker job completes', async () => {
    mocks.post.mockResolvedValueOnce({ data: { job_id: 'job-pdf' } })
    mocks.get.mockImplementation((url: string) => {
      if (url === '/documents') {
        return Promise.resolve({
          data: {
            items: [{
              id: 'doc-pdf',
              knowledge_base_id: 'kb-1',
              original_filename: 'upload-verification.pdf',
              status: 'ready',
            }],
          },
        })
      }
      if (url === '/jobs') {
        return Promise.resolve({
          data: {
            items: [{
              id: 'job-pdf',
              document_id: 'doc-pdf',
              operation: 'ingest',
              status: 'succeeded',
              stage: 'completed',
            }],
          },
        })
      }
      throw new Error(`unexpected GET ${url}`)
    })
    const wrapper = mountManager()
    await flushPromises()
    const input = wrapper.get<HTMLInputElement>('input[type="file"]')
    Object.defineProperty(input.element, 'files', {
      configurable: true,
      value: [new File(['%PDF-1.3'], 'upload-verification.pdf', { type: 'application/pdf' })],
    })

    await input.trigger('change')
    await flushPromises()

    expect(wrapper.text()).toContain('成功')
    expect(wrapper.text()).toContain('解析、切分和向量生成已完成')
  })
})
