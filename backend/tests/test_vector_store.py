"""
文件职责：
该文件负责测试向量存储模块中对嵌入 (Embeddings) 的处理，特别是 BGE 模型适配器的行为和依赖管控。

所属功能：
向量数据库与文本嵌入 (Vector Store & Embeddings)

主要流程：
1. 使用 monkeypatch 隔离环境依赖。
2. 拦截 PyTorch 相关的包加载，防止启动慢或依赖过重。
3. 注入虚拟的 TextEmbedding 测试 BGE 模型嵌入计算流程。
"""

import sys
from types import SimpleNamespace

from app.rag.vector_store import BgeEmbeddings


class _FakeVector:
    """
    伪造的向量对象，用于模拟 FastEmbed 返回的向量格式。

    Responsibilities:
        提供与真实向量相似的接口调用（如 tolist），供测试用例模拟向量降维或取值。

    Attributes:
        values: 包含浮点数的模拟向量列表。
    """

    def __init__(self, values: list[float]) -> None:
        self.values = values

    def tolist(self) -> list[float]:
        return self.values


def test_bge_embeddings_use_fastembed_without_pytorch(monkeypatch) -> None:
    """
    测试 BgeEmbeddings 模型在不依赖 PyTorch (sentence-transformers) 的情况下，
    能够通过 fastembed 正常生成文本和查询的向量。

    Args:
        monkeypatch: pytest fixture，用于在测试期间动态修改类和模块行为。

    Returns:
        None

    Raises:
        AssertionError: 出现非法调用 sentence-transformers，或者最终生成的向量结构不符预期。
    """
    # 收集测试执行过程中的调用信息以供断言
    calls: dict[str, object] = {}

    class FakeTextEmbedding:
        def __init__(self, *, model_name: str, cache_dir: str | None = None) -> None:
            calls["model_name"] = model_name
            calls["cache_dir"] = cache_dir

        def embed(self, texts: list[str]):
            calls["texts"] = texts
            return iter([_FakeVector([0.1, 0.2]) for _ in texts])

    class ForbiddenSentenceTransformer:
        """一旦被实例化就会立刻抛错，用于拦截对 PyTorch 后端的意外加载"""

        def __init__(self, *_args, **_kwargs) -> None:
            raise AssertionError("BGE adapter must not load sentence-transformers/PyTorch")

    # 在 sys.modules 中注入造假的 fastembed，并将 sentence_transformers 设为黑洞
    monkeypatch.setitem(sys.modules, "fastembed", SimpleNamespace(TextEmbedding=FakeTextEmbedding))
    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        SimpleNamespace(SentenceTransformer=ForbiddenSentenceTransformer),
    )

    # 实例化 BgeEmbeddings 时将自动采用上面注入的假底层
    embeddings = BgeEmbeddings(
        "BAAI/bge-small-zh-v1.5",
        cache_dir="/data/models/fastembed",
    )

    assert embeddings.embed_documents(["小米 14", "智能手环 9"]) == [
        [0.1, 0.2],
        [0.1, 0.2],
    ]
    assert embeddings.embed_query("X20 Pro") == [0.1, 0.2]
    assert calls == {
        "model_name": "BAAI/bge-small-zh-v1.5",
        "cache_dir": "/data/models/fastembed",
        "texts": ["X20 Pro"],
    }
