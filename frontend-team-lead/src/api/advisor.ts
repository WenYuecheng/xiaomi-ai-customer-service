import type { AdvisorPlan, AiTraceStep, Source } from '@/types'

import { TOKEN_KEY } from './client'

export interface AdvisorStreamHandlers {
  onMeta: (data: { session_id: string; turn_id: string }) => void
  onTrace: (step: AiTraceStep) => void
  onAdvisor: (plan: AdvisorPlan, turnId: string) => void
  onSources: (sources: Source[]) => void
  onDone: (data: { status: string }) => void
  onError?: (data: { code?: string; message: string }) => void
}

export async function streamAdvisor(
  url: string,
  payload: object,
  handlers: AdvisorStreamHandlers,
  signal: AbortSignal,
): Promise<void> {
  const token = localStorage.getItem(TOKEN_KEY)
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token ?? ''}` },
    body: JSON.stringify({ ...payload, stream: true }),
    signal,
  })
  if (!response.ok || !response.body) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.error?.message ?? 'AI 选购服务连接失败')
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
      if (event === 'trace') handlers.onTrace(data)
      if (event === 'advisor' && data.plan) handlers.onAdvisor(data.plan, data.turn_id)
      if (event === 'sources') handlers.onSources(data.sources)
      if (event === 'done') handlers.onDone(data)
      if (event === 'error') {
        handlers.onError?.(data)
        throw new Error(data.message ?? 'AI 选购方案生成失败')
      }
    }
    if (done) break
  }
}
