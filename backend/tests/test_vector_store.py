import sys
from types import SimpleNamespace

from app.rag.vector_store import BgeEmbeddings


class _FakeVector:
    def __init__(self, values: list[float]) -> None:
        self.values = values

    def tolist(self) -> list[float]:
        return self.values


def test_bge_embeddings_use_fastembed_without_pytorch(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class FakeTextEmbedding:
        def __init__(self, *, model_name: str, cache_dir: str | None = None) -> None:
            calls["model_name"] = model_name
            calls["cache_dir"] = cache_dir

        def embed(self, texts: list[str]):
            calls["texts"] = texts
            return iter([_FakeVector([0.1, 0.2]) for _ in texts])

    class ForbiddenSentenceTransformer:
        def __init__(self, *_args, **_kwargs) -> None:
            raise AssertionError("BGE adapter must not load sentence-transformers/PyTorch")

    monkeypatch.setitem(sys.modules, "fastembed", SimpleNamespace(TextEmbedding=FakeTextEmbedding))
    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        SimpleNamespace(SentenceTransformer=ForbiddenSentenceTransformer),
    )

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
