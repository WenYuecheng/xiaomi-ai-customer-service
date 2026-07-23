import { streamChat } from './chat'

describe('streamChat', () => {
  it('preserves the backend error code for recoverable conversation conflicts', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
      error: {
        code: 'conversation_knowledge_mismatch',
        message: '会话与知识库不匹配',
      },
    }), {
      status: 409,
      headers: { 'Content-Type': 'application/json' },
    })))

    await expect(streamChat(
      { knowledge_base_id: 'kb-new', conversation_id: 'conversation-old', message: '小米 14' },
      { onMeta: vi.fn(), onTrace: vi.fn(), onDelta: vi.fn(), onSources: vi.fn(), onDone: vi.fn() },
      new AbortController().signal,
    )).rejects.toMatchObject({
      status: 409,
      code: 'conversation_knowledge_mismatch',
      message: '会话与知识库不匹配',
    })
  })

  it('delivers trace events to the caller in stream order', async () => {
    const trace = vi.fn()
    const body = [
      'event: meta\ndata: {"conversation_id":"c1","message_id":"m1","run_id":"r1"}',
      'event: trace\ndata: {"stage":"understanding","status":"completed","engine":"DeepSeek","model":"deepseek-chat","duration_ms":12,"summary":"已理解"}',
      'event: done\ndata: {"fallback":false,"transfer_suggested":false}',
      '',
    ].join('\n\n')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, { status: 200 })))

    await streamChat(
      { knowledge_base_id: 'kb-1', message: '问题' },
      { onMeta: vi.fn(), onTrace: trace, onDelta: vi.fn(), onSources: vi.fn(), onDone: vi.fn() },
      new AbortController().signal,
    )

    expect(trace).toHaveBeenCalledWith(expect.objectContaining({ stage: 'understanding' }))
  })
})
