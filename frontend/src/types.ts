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
}

export interface Source {
  document_id: string
  chunk_id: string
  filename: string
  location: string
  snippet: string
  score: number
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  fallback: boolean
  sources: Source[]
}

export interface ChatCompletion {
  conversation_id: string
  message_id: string
  run_id: string
  answer: string
  sources: Source[]
  fallback: boolean
  transfer_suggested: boolean
}

