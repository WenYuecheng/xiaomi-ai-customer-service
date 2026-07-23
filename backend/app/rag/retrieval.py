"""
文件职责：
该文件负责实现混合检索（Hybrid Search）逻辑，结合大模型向量相似度和结巴分词的字面召回评分。

所属功能：
RAG 引擎（Retrieval-Augmented Generation） -> 上下文召回。

主要流程：
定义了基于词法匹配和向量模型结合的查询管道。
"""

import re
from dataclasses import dataclass

import jieba
from sqlalchemy import select
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
    """
    用于封装从检索库返回的溯源匹配段数据结构。

    生命周期：
    作为底层 `retrieve_sources` 函数与上层 LLM 生成管道之间的数据传递对象，通常被转化为 API JSON。
    """

    document_id: str
    chunk_id: str
    filename: str
    location: str
    snippet: str
    score: float


def requested_product_models(session: Session, knowledge_base_id: str, query: str) -> set[str]:
    """Resolve an explicit query model against generic entities stored in the library."""
    if extracted := set(extract_product_models(query)):
        return extracted

    compact_query = re.sub(r"\s+", "", query).lower()
    stored_models = {
        model
        for models in session.scalars(
            select(DocumentChunk.product_models).where(
                DocumentChunk.knowledge_base_id == knowledge_base_id
            )
        )
        for model in models
        if model
    }
    matched = {
        model for model in stored_models if re.sub(r"\s+", "", model).lower() in compact_query
    }
    return {
        model
        for model in matched
        if not any(
            model != other
            and re.sub(r"\s+", "", model).lower() in re.sub(r"\s+", "", other).lower()
            for other in matched
        )
    }


def lexical_score(query: str, text: str) -> float:
    """
    词法匹配算分。

    功能归属：
    词汇召回算法。

    主要职责：
    通过 jieba 分词对 Query 和文本块进行 Jaccard 相似度/交集计算，
    补充纯向量召回对特定实体名词或硬件参数不够敏感的问题。

    Args:
        query: 用户发起的原始查询文本。
        text: 知识库中文档切片的文本内容。

    Returns:
        基于分词重合度与属性词命中的最高分 (0.0 到 1.0)。
    """
    # 获取有效的分词集合，忽略首尾空格和大小写差异
    query_tokens = {token.strip().lower() for token in jieba.cut(query) if token.strip()}
    text_tokens = {token.strip().lower() for token in jieba.cut(text) if token.strip()}

    # 过滤过短或非纯文本的标记词
    meaningful = {token for token in query_tokens if len(token) > 1 or token.isalnum()}
    if not meaningful:
        return 0.0

    # 计算基础的 Jaccard 类型重合分
    token_score = len(meaningful & text_tokens) / len(meaningful)

    # 获取查询命中的业务特定属性词
    requested_attributes = {term for term in ATTRIBUTE_TERMS if term in query}
    attribute_score = (
        len({term for term in requested_attributes if term in text}) / len(requested_attributes)
        if requested_attributes
        else 0.0
    )

    # 取两者较高分作为最终的词汇召回分数
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
    执行基于给定查询语句的文档分块混合检索。

    核心业务流程：
    混合检索与过滤流水线。

    执行链：
    1. 通过 VectorStore 获取粗排结果 (Top-K 放大约 5 倍，扩大召回池)。
    2. 使用 `extract_product_models` 提取提问中的型号标签，执行硬性元数据过滤，
       排除不是该型号的切片（防止张冠李戴）。
    3. 调用 `lexical_score` 获取字面分数。
    4. 执行 70% 向量分与 30% 字面分的加权融合（Blended Score）。
    5. 返回达标的最终 Top-K 引用列表。

    Args:
        session: 用于查询片段来源元信息的数据库会话。
        vector_store: 存放文档向量嵌入的实例对象。
        knowledge_base_id: 知识库 UUID 标识。
        query: 用户的自然语言查询。
        top_k: 返回给最终上下文的数量。
        threshold: 最终综合评分的阈值下限。
        require_lexical_overlap: 是否硬性要求具有词汇交集。

    Returns:
        包含片段详情的 `RetrievedSource` 对象列表，按融合得分降序排列。
    """
    # 1. 向下层向量库发起粗排检索请求，扩大 K 值以保留足够样本供后置清洗。
    results = vector_store.collection(knowledge_base_id).similarity_search_with_score(
        query, k=max(top_k * 5, 20)
    )

    requested_models = requested_product_models(session, knowledge_base_id, query)
    sources: list[RetrievedSource] = []

    for langchain_document, distance in results:
        chunk_id = langchain_document.metadata.get("chunk_id")
        chunk = session.get(DocumentChunk, chunk_id)
        if not chunk:
            continue

        # 2. 型号硬过滤：如果用户提到特定型号，且该块不包含此型号，跳过。
        exact_model_match = bool(requested_models.intersection(chunk.product_models))
        if requested_models and not exact_model_match:
            continue

        # 3. 计算文本重合度
        lexical = lexical_score(query, chunk.text)
        vector_score = 1 - float(distance)

        # 4. 加权合成最终分数
        blended = vector_score * 0.7 + lexical * 0.3

        # 防止强词汇匹配在向量模型下由于离线哈希被埋没
        score = max(0.0, min(1.0, max(blended, lexical)))

        if exact_model_match and lexical > 0:
            score = max(score, threshold)

        if score < threshold or (require_lexical_overlap and lexical == 0):
            continue

        # 填充来源文档信息以供呈现
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

    # 5. 再次对处理后的结果重排并截断最终期望的 top_k。
    return sorted(sources, key=lambda item: item.score, reverse=True)[:top_k]
