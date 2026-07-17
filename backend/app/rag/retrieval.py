from dataclasses import dataclass

import jieba
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk
from app.ingestion.parsers import extract_product_models
from app.rag.vector_store import VectorStoreService


@dataclass(frozen=True)
class RetrievedSource:
    document_id: str
    chunk_id: str
    filename: str
    location: str
    snippet: str
    score: float


def lexical_score(query: str, text: str) -> float:
    query_tokens = {token.strip().lower() for token in jieba.cut(query) if token.strip()}
    text_tokens = {token.strip().lower() for token in jieba.cut(text) if token.strip()}
    meaningful = {token for token in query_tokens if len(token) > 1 or token.isalnum()}
    if not meaningful:
        return 0.0
    return len(meaningful & text_tokens) / len(meaningful)


def retrieve_sources(
    session: Session,
    vector_store: VectorStoreService,
    knowledge_base_id: str,
    query: str,
    top_k: int,
    threshold: float,
    require_lexical_overlap: bool,
) -> list[RetrievedSource]:
    results = vector_store.collection(knowledge_base_id).similarity_search_with_relevance_scores(
        query, k=top_k
    )
    requested_models = set(extract_product_models(query))
    sources: list[RetrievedSource] = []
    for langchain_document, vector_score in results:
        chunk_id = langchain_document.metadata.get("chunk_id")
        chunk = session.get(DocumentChunk, chunk_id)
        if not chunk:
            continue
        if requested_models and not requested_models.intersection(chunk.product_models):
            continue
        lexical = lexical_score(query, chunk.text)
        score = max(0.0, min(1.0, float(vector_score) * 0.7 + lexical * 0.3))
        if score < threshold or (require_lexical_overlap and lexical == 0):
            continue
        document = session.get(Document, chunk.document_id)
        if not document:
            continue
        sources.append(
            RetrievedSource(
                document_id=document.id,
                chunk_id=chunk.id,
                filename=document.original_filename,
                location=chunk.location,
                snippet=chunk.text,
                score=round(score, 4),
            )
        )
    return sorted(sources, key=lambda item: item.score, reverse=True)

