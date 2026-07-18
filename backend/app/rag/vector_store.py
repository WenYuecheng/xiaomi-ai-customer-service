"""
文件职责：
封装底层向量数据库（ChromaDB）和文本嵌入（Embeddings）模型适配。

所属功能：
RAG 引擎 -> 向量存储与特征提取。
"""

import hashlib
import math
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document as LangChainDocument
from langchain_core.embeddings import Embeddings
from langchain_ollama import OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings

from app.core.config import Settings


class HashEmbeddings(Embeddings):
    """
    内部辅助类：
    基于字符 N-Gram 和 SHA256 哈希的确定性伪向量计算。
    仅用于脱机测试和 Mock 演示，避免在开发阶段依赖真实 GPU 或大模型 API。
    """

    dimensions = 256

    def _embed(self, text: str) -> list[float]:
        normalized = "".join(text.lower().split())
        vector = [0.0] * self.dimensions
        tokens = [normalized[index : index + 3] for index in range(max(1, len(normalized) - 2))]
        if not tokens:
            tokens = [normalized]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:2], "big") % self.dimensions
            vector[index] += 1.0 if digest[2] % 2 == 0 else -1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


class BgeEmbeddings(Embeddings):
    """
    内部辅助类：
    基于 FastEmbed 的轻量级本地 BGE 模型适配器。
    支持在无独立 GPU 环境下，通过 ONNX Runtime 利用 CPU 提供高质量的中文向量嵌入。
    通过懒加载防止启动时卡顿，并在需要时下载模型至指定缓存目录。
    """

    def __init__(self, model_name: str, cache_dir: str | Path | None = None) -> None:
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:
            raise RuntimeError("BGE embeddings require: uv sync --extra local-embeddings") from exc
        self.model = TextEmbedding(
            model_name=model_name,
            cache_dir=str(cache_dir) if cache_dir is not None else None,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self.model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


def create_embeddings(settings: Settings) -> Embeddings:
    if settings.embedding_provider == "mock":
        return HashEmbeddings()
    if settings.embedding_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI embeddings")
        return OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
    if settings.embedding_provider == "ollama":
        return OllamaEmbeddings(
            model=settings.embedding_model,
            base_url=settings.ollama_base_url,
        )
    return BgeEmbeddings(
        settings.embedding_model,
        cache_dir=settings.model_artifact_dir / "fastembed",
    )


class VectorStoreService:
    """
    核心业务服务：
    提供知识库分片的持久化和检索能力。内部使用 ChromaDB，并针对不同知识库创建独立的 Collection。
    """

    def __init__(self, root: Path, embeddings: Embeddings | None = None) -> None:
        self.root = root
        self.embeddings = embeddings or HashEmbeddings()

    def collection(self, knowledge_base_id: str) -> Chroma:
        return Chroma(
            collection_name=f"kb_{knowledge_base_id.replace('-', '_')}",
            persist_directory=str(self.root),
            embedding_function=self.embeddings,
            collection_metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, knowledge_base_id: str, chunks: list) -> None:
        documents = [
            LangChainDocument(
                page_content=chunk.text,
                metadata={
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "location": chunk.location,
                    "product_models": ",".join(chunk.product_models),
                },
            )
            for chunk in chunks
        ]
        if documents:
            self.collection(knowledge_base_id).add_documents(
                documents=documents, ids=[chunk.id for chunk in chunks]
            )

    def delete_chunks(self, knowledge_base_id: str, chunk_ids: list[str]) -> None:
        if chunk_ids:
            self.collection(knowledge_base_id).delete(ids=chunk_ids)
