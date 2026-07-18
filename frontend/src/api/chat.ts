import type { AiTraceStep, Source } from '@/types'

import { TOKEN_KEY } from './client'

export interface StreamHandlers {
  onMeta: (data: { conversation_id: string; message_id: string; run_id: string }) => void
  onDelta: (content: string) => void
  onTrace: (step: AiTraceStep) => void
  onSources: (sources: Source[]) => void
  onDone: (data: { fallback: boolean; transfer_suggested: boolean }) => void
  onError?: (data: { code: string; message: string }) => void
}

export class ChatStreamError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message)
    this.name = 'ChatStreamError'
  }
}

export async function streamChat(
  payload: { knowledge_base_id: string; conversation_id?: string; message: string },
  handlers: StreamHandlers,
  signal: AbortSignal,
): Promise<void> {
  const token = localStorage.getItem(TOKEN_KEY)
  const response = await fetch('/api/v1/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token ?? ''}` },
    body: JSON.stringify({ ...payload, stream: true }),
    signal,
  })
  if (!response.ok || !response.body) {
    const body = await response.json().catch(() => null)
    throw new ChatStreamError(
      response.status,
      body?.error?.code ?? 'stream_connection_failed',
      body?.error?.message ?? '流式回答连接失败',
    )
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value, { stream: !done })
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() ?? ''
    for (const block of blocks) {
      const event = block.match(/^event: (.+)$/m)?.[1]
      const raw = block.match(/^data: (.+)$/m)?.[1]
      if (!event || !raw) continue
      const data = JSON.parse(raw)
      if (event === 'meta') handlers.onMeta(data)
      if (event === 'delta') handlers.onDelta(data.content)
      if (event === 'trace') handlers.onTrace(data)
      if (event === 'sources') handlers.onSources(data.sources)
      if (event === 'done') handlers.onDone(data)
      if (event === 'error') {
        handlers.onError?.(data)
        throw new ChatStreamError(500, data.code ?? 'generation_failed', data.message ?? '回答生成失败')
      }
    }
    if (done) break
  }
}
