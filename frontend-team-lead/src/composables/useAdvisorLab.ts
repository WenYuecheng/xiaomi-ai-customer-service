import { readonly, ref, shallowRef } from 'vue'

import { streamAdvisor } from '@/api/advisor'
import { api } from '@/api/client'
import type { AdvisorPlan, AdvisorSession, AdvisorSessionSummary, AiTraceStep, KnowledgeBase, Source } from '@/types'

export function useAdvisorLab() {
  const knowledgeBases = ref<KnowledgeBase[]>([])
  const sessions = ref<AdvisorSessionSummary[]>([])
  const activeSession = shallowRef<AdvisorSession>()
  const activeSessionId = shallowRef<string>()
  const plan = shallowRef<AdvisorPlan>()
  const sources = ref<Source[]>([])
  const trace = ref<AiTraceStep[]>([])
  const busy = shallowRef(false)
  const error = shallowRef('')
  let controller: AbortController | undefined

  function upsertTrace(step: AiTraceStep): void {
    const index = trace.value.findIndex((item) => item.stage === step.stage)
    trace.value = index === -1
      ? [...trace.value, step]
      : trace.value.map((item, itemIndex) => itemIndex === index ? step : item)
  }

  async function load(): Promise<void> {
    const [knowledgeResult, sessionResult] = await Promise.all([
      api.get<{ items: KnowledgeBase[] }>('/knowledge-bases'),
      api.get<{ items: AdvisorSessionSummary[] }>('/advisor/sessions'),
    ])
    knowledgeBases.value = knowledgeResult.data.items.filter((item) => item.status === 'active')
    sessions.value = sessionResult.data.items
  }

  async function run(url: string, payload: object): Promise<void> {
    busy.value = true; error.value = ''; trace.value = []; plan.value = undefined; sources.value = []
    controller = new AbortController()
    try {
      await streamAdvisor(url, payload, {
        onMeta: (data) => { activeSessionId.value = data.session_id },
        onTrace: upsertTrace,
        onAdvisor: (value) => { plan.value = value },
        onSources: (value) => { sources.value = value },
        onDone: () => undefined,
        onError: (data) => { error.value = data.message },
      }, controller.signal)
      const result = await api.get<{ items: AdvisorSessionSummary[] }>('/advisor/sessions')
      sessions.value = result.data.items
    } catch (reason) {
      if (!(reason instanceof DOMException && reason.name === 'AbortError')) {
        error.value = reason instanceof Error ? reason.message : 'AI 选购方案生成失败'
      }
    } finally { busy.value = false; controller = undefined }
  }

  async function submit(payload: object): Promise<void> {
    await run('/api/v1/advisor/sessions', payload)
  }

  async function followUp(question: string): Promise<void> {
    if (!activeSessionId.value) return
    await run(`/api/v1/advisor/sessions/${activeSessionId.value}/turns`, { message: question })
  }

  async function selectSession(id: string): Promise<void> {
    const result = await api.get<AdvisorSession>(`/advisor/sessions/${id}`)
    activeSession.value = result.data
    activeSessionId.value = id
    const latest = result.data.turns.at(-1)
    plan.value = latest?.plan ?? undefined
    sources.value = latest?.sources ?? []
    trace.value = latest?.ai_trace ?? []
  }

  async function deleteSession(id: string): Promise<void> {
    await api.delete(`/advisor/sessions/${id}`)
    sessions.value = sessions.value.filter((item) => item.id !== id)
    if (activeSessionId.value === id) {
      activeSessionId.value = undefined; activeSession.value = undefined
      plan.value = undefined; sources.value = []; trace.value = []
    }
  }

  function stop(): void { controller?.abort() }

  return {
    knowledgeBases: readonly(knowledgeBases), sessions: readonly(sessions), activeSessionId,
    plan, sources: readonly(sources), trace: readonly(trace), busy, error,
    load, submit, followUp, selectSession, deleteSession, stop,
  }
}
