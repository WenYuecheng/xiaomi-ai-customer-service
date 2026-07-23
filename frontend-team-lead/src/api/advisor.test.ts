import { streamAdvisor } from './advisor'

describe('streamAdvisor', () => {
  it('delivers structured advisor plans after trace events', async () => {
    const trace = vi.fn()
    const plan = vi.fn()
    const body = [
      'event: meta\ndata: {"session_id":"s1","turn_id":"t1"}',
      'event: trace\ndata: {"stage":"understanding","status":"completed","engine":"DeepSeek","model":"deepseek-chat","summary":"已理解"}',
      'event: advisor\ndata: {"plan":{"title":"方案","candidates":[]},"turn_id":"t1"}',
      'event: sources\ndata: {"sources":[]}',
      'event: done\ndata: {"status":"completed"}',
      '',
    ].join('\n\n')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, { status: 200 })))

    await streamAdvisor(
      '/api/v1/advisor/sessions',
      { knowledge_base_id: 'kb-1', message: '推荐手机' },
      { onMeta: vi.fn(), onTrace: trace, onAdvisor: plan, onSources: vi.fn(), onDone: vi.fn() },
      new AbortController().signal,
    )

    expect(trace).toHaveBeenCalledTimes(1)
    expect(plan).toHaveBeenCalledWith(expect.objectContaining({ title: '方案' }), 't1')
  })
})
