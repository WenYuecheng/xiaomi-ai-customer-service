from dataclasses import dataclass

import jieba
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk
from app.ingestion.parsers import extract_product_models
from app.rag.vector_store import VectorStoreService

ATTRIBUTE_TERMS = (
    "型号",
    "额定功率",
    "净重",
    "吸力",
    "导航",
    "清扫",
    "屏幕",
    "亮度",
    "续航",
    "容量",
    "防水",
    "运动模式",
    "屏占比",
)


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
    token_score = len(meaningful & text_tokens) / len(meaningful)
    requested_attributes = {term for term in ATTRIBUTE_TERMS if term in query}
    attribute_score = (
        len({term for term in requested_attributes if term in text}) / len(requested_attributes)
        if requested_attributes
        else 0.0
    )
    return max(token_score, attribute_score)


def retrieve_sources(
    session: Session,
    vector_store: VectorStoreService,
    knowledge_base_id: str,
    query: str,
    top_k: int,
    threshold: float,
    require_lexical_overlap: bool,
) -> list[RetrievedSource]:
    results = vector_store.collection(knowledge_base_id).similarity_search_with_score(
        query, k=max(top_k * 5, 20)
    )
    requested_models = set(extract_product_models(query))
    sources: list[RetrievedSource] = []
    for langchain_document, distance in results:
        chunk_id = langchain_document.metadata.get("chunk_id")
        chunk = session.get(DocumentChunk, chunk_id)
        if not chunk:
            continue
        exact_model_match = bool(requested_models.intersection(chunk.product_models))
        if requested_models and not exact_model_match:
            continue
        lexical = lexical_score(query, chunk.text)
        vector_score = 1 - float(distance)
        blended = vector_score * 0.7 + lexical * 0.3
        # A precise lexical match must not be buried by a weak offline hash vector.
        score = max(0.0, min(1.0, max(blended, lexical)))
        if exact_model_match and lexical > 0:
            score = max(score, threshold)
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
    return sorted(sources, key=lambda item: item.score, reverse=True)[:top_k]
