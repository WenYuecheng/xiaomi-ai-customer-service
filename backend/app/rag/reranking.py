from dataclasses import replace

from app.rag.providers import ChatProvider, RerankCandidate


def rerank_sources(
    provider: ChatProvider,
    question: str,
    candidates,
    top_k: int,
    min_score: float,
) -> tuple[list, str, str, list[str]]:
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
