export type Role = 'admin' | 'operator' | 'user'

export interface User {
  id: string
  username: string
  role: Role
  is_active: boolean
}

export interface KnowledgeBase {
  id: string
  name: string
  description?: string
  status: string
  embedding_model: string
  owner_id: string
  created_at: string
}

export interface DocumentRecord {
  id: string
  knowledge_base_id: string
  original_filename: string
  media_type: string
  size_bytes: number
  status: 'queued' | 'processing' | 'ready' | 'failed'
  error_message?: string | null
  chunk_size: number
  chunk_overlap: number
  source_url?: string | null
  created_at: string
}

export interface ProcessingJob {
  id: string
  document_id: string
  operation: string
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled'
  stage: string
  error_message?: string | null
  attempts: number
  created_at: string
}

export interface DocumentChunk {
  id: string
  ordinal: number
  text: string
  location: string
  product_models: string[]
}

export interface Source {
  document_id: string
  chunk_id: string
  filename: string
  location: string
  snippet: string
  score: number
  source_url?: string | null
}

export interface AiTraceStep {
  stage: 'understanding' | 'retrieval' | 'reranking' | 'generation' | 'grounding'
  status: 'running' | 'completed' | 'skipped' | 'degraded' | 'failed'
  engine: string
  model: string
  duration_ms?: number | null
  summary: string
  details?: readonly string[]
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  fallback: boolean
  sources: Source[]
  transfer_suggested?: boolean
  ai_trace?: AiTraceStep[]
  advisor_session_id?: string | null
  advisor_plan?: AdvisorPlan | null
}

export interface ChatCompletion {
  conversation_id: string
  message_id: string
  run_id: string
  answer: string
  sources: Source[]
  fallback: boolean
  transfer_suggested: boolean
  ai_trace: AiTraceStep[]
  advisor_session_id?: string | null
  advisor_plan?: AdvisorPlan | null
}

export interface AdvisorPrice {
  status: 'evidence' | 'unavailable'
  display: string
  source_chunk_id?: string | null
  captured_at?: string | null
}

export interface AdvisorCandidate {
  model: string
  fit_score: number
  highlights: string[]
  tradeoffs: string[]
  dimension_scores: Record<string, number>
  source_chunk_ids: string[]
  price: AdvisorPrice
}

export interface AdvisorPlan {
  title: string
  interpreted_need: string
  candidates: AdvisorCandidate[]
  comparison_rows: Array<{ dimension: string; values: Record<string, string> }>
  recommendation: {
    primary_model: string
    summary: string
    reasons: string[]
    caveats: string[]
  }
  follow_up_suggestions: string[]
}

export interface AdvisorTurn {
  id: string
  sequence_no: number
  question: string
  requirements: Record<string, unknown>
  plan?: AdvisorPlan | null
  sources: Source[]
  ai_trace: AiTraceStep[]
  status: string
  created_at: string
}

export interface AdvisorSessionSummary {
  id: string
  knowledge_base_id: string
  title: string
  category?: string | null
  turn_count: number
  created_at: string
  updated_at: string
}

export interface AdvisorSession extends AdvisorSessionSummary {
  turns: AdvisorTurn[]
}
