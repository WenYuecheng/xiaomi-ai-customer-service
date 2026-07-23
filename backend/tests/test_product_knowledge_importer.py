import sys
from collections import Counter
from importlib import import_module
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def importer_module():
    return import_module("scripts.ingest_product_knowledge")


def test_repository_documents_are_routed_into_two_libraries() -> None:
    documents = importer_module().discover_documents(PROJECT_ROOT / "data/knowledge")

    assert len(documents) == 50
    assert Counter(document.library for document in documents) == {
        "小米生态核心库": 30,
        "竞品选购对比库": 20,
    }


def test_upload_data_forwards_source_url() -> None:
    module = importer_module()
    document = module.discover_documents(PROJECT_ROOT / "data/knowledge")[0]

    assert module.build_upload_data(document, "kb-123") == {
        "knowledge_base_id": "kb-123",
        "source_url": document.source_url,
        "chunk_size": "800",
        "chunk_overlap": "120",
    }


def test_existing_filename_is_skipped() -> None:
    module = importer_module()
    documents = module.discover_documents(PROJECT_ROOT / "data/knowledge")[:2]

    assert module.pending_documents(documents, {documents[0].path.name}) == [documents[1]]


def test_non_publishable_document_is_rejected(tmp_path: Path) -> None:
    core = tmp_path / "product-core"
    core.mkdir()
    (core / "PROD-001_invalid.md").write_text("# missing metadata", encoding="utf-8")

    with pytest.raises(ValueError, match="PROD-001_invalid.md"):
        importer_module().discover_documents(tmp_path)
