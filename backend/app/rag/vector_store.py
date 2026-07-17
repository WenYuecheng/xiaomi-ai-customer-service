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
    """Deterministic character n-gram embeddings for offline tests and demos."""

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
    """Lazy local BGE adapter so default installs stay lightweight."""

    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError("BGE embeddings require: uv sync --extra local-embeddings") from exc
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, normalize_embeddings=True).tolist()

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
    return BgeEmbeddings(settings.embedding_model)


class VectorStoreService:
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
