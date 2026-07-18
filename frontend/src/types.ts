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
  stage: 'understanding' | 'retrieval' | 'generation' | 'grounding'
  status: 'running' | 'completed' | 'skipped' | 'degraded' | 'failed'
  engine: string
  model: string
  duration_ms?: number | null
  summary: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  fallback: boolean
  sources: Source[]
  transfer_suggested?: boolean
  ai_trace?: AiTraceStep[]
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
}
