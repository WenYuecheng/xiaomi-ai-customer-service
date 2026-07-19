"""
文件职责：
封装基于 LLM 的文档片段二次重排（Rerank）逻辑。

所属功能：
RAG 引擎 -> 检索后处理（Post-Retrieval）。

主要流程：
1. 接收粗略召回的候选片段。
2. 构造 RerankCandidate 结构传递给大模型提供方。
3. 捕获重排结果，根据最小阈值剔除不相关片段。
4. 提供优雅降级机制：如果 LLM 重排异常，退化使用原始向量检索的相似度排序。
"""

from dataclasses import replace

from app.rag.providers import ChatProvider, RerankCandidate


def rerank_sources(
    provider: ChatProvider,
    question: str,
    candidates,
    top_k: int,
    min_score: float,
) -> tuple[list, str, str, list[str]]:
    """
    对粗排阶段生成的候选片段进行基于大模型的二次细排（Rerank）。

    主要职责：
    借助 LLM 强大的语境理解能力，剔除字面相似但语义不符合用户提问意图的“假阳性”片段。
    支持容错降级，避免因为单次 LLM 超时或解析失败导致整个检索链路断裂。

    Args:
        provider: 执行重排请求的大模型提供者。
        question: 用户原始或重写后的提问。
        candidates: 第一阶段（粗排）召回的候选数据列表（元素需要包含 chunk_id、snippet 等）。
        top_k: 期望保留的最大片段数量。
        min_score: 允许被采纳的最小相关性分数阈值（0.0 ~ 1.0）。

    Returns:
        返回一个包含 4 个元素的元组：
        - selected (list): 经过筛选与重新排序，并限制数量的候选列表。
        - status (str): 当前重排状态，"completed" 或 "degraded"。
        - message (str): 可读的状态描述信息。
        - details (list[str]): 对每个候选片段筛选决定的详细记录（如保留理由）。
    """
    try:
        result = provider.rerank(
            question,
            [
                RerankCandidate(
                    chunk_id=item.chunk_id,
                    filename=item.filename,
                    location=item.location,
                    snippet=item.snippet,
                    retrieval_score=item.score,
                )
                for item in candidates
            ],
            top_k,
        )
    except Exception:
        selected = candidates[:top_k]
        return (
            selected,
            "degraded",
            f"AI 重排不可用，已降级使用原始排序并保留 {len(selected)} 个片段",
            ["重排结果解析失败或包含非法候选 ID"],
        )
    candidate_by_id = {item.chunk_id: item for item in candidates}
    selected = [
        replace(candidate_by_id[decision.chunk_id], score=round(decision.relevance_score, 4))
        for decision in result.decisions
        if decision.relevance_score >= min_score
    ][:top_k]
    details = [
        (
            f"保留 {candidate_by_id[item.chunk_id].filename}：{item.reason}"
            if item.relevance_score >= min_score
            else f"排除 {candidate_by_id[item.chunk_id].filename}：{item.reason}"
        )
        for item in result.decisions[:3]
    ]
    return (
        selected,
        "completed",
        f"从 {len(candidates)} 个候选中保留 {len(selected)} 个可靠片段"
        if selected
        else f"检查 {len(candidates)} 个候选后未保留可靠片段",
        details,
    )
