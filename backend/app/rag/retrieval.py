"""
文件职责：
实现混合检索（Hybrid Search）逻辑，结合大模型向量相似度和结巴分词的字面召回评分。

所属功能：
RAG 引擎 -> 上下文召回。
"""

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
    """
    功能归属：
    词法匹配算分。

    主要职责：
    通过 jieba 分词对 Query 和文本块进行 Jaccard 相似度/交集计算，
    补充纯向量召回对实体名词不够敏感的问题。
    """
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
    """
    核心业务流程：
    混合检索与过滤流水线。

    执行链：
    1. 通过 VectorStore 获取粗排结果 (Top-K 放大约 5 倍)。
    2. 使用 `extract_product_models` 提取提问中的型号标签，执行硬性元数据过滤，
       排除不是该型号的切片。
    3. 调用 `lexical_score` 获取字面分数。
    4. 执行 70% 向量分与 30% 字面分的加权融合（Blended Score）。
    5. 返回达标的最终 Top-K 引用列表。
    """
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
