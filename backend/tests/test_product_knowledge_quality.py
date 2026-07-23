from importlib import import_module
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient

from app.ingestion.parsers import extract_product_models
from tests.conftest import auth_headers
from tests.test_documents import wait_for_job

PROJECT_ROOT = Path(__file__).resolve().parents[2]

VALID_DOCUMENT = """---
文档编号: "PROD-999"
标题: "OPPO Pad 4 Pro 参数资料"
类别: "平板"
品牌: "OPPO"
型号: "OPPO Pad 4 Pro"
发布或上市: "2026-04"
语言: "zh-CN"
整理日期: "2026-07-23"
审核状态: "可入库（来源关联，待人工终审）"
主要来源: "https://example.com/products/oppo-pad-4-pro"
来源类型: "专业评测媒体"
来源等级: "B（专业媒体）"
价格来源: "https://example.com/prices/oppo-pad-4-pro"
知识库: "竞品选购对比库"
---

# OPPO Pad 4 Pro 参数资料

- 屏幕尺寸：13.2 英寸。
"""


def quality_module():
    return import_module("app.ingestion.knowledge_quality")


def test_front_matter_model_is_extracted_for_any_brand() -> None:
    assert "oppo pad 4 pro" in extract_product_models(VALID_DOCUMENT)


def test_valid_publishable_document_passes(tmp_path: Path) -> None:
    path = tmp_path / "PROD-999_oppo-pad-4-pro.md"
    path.write_text(VALID_DOCUMENT, encoding="utf-8")

    assert quality_module().validate_publishable_document(path) == []


def test_missing_source_url_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "PROD-999_oppo-pad-4-pro.md"
    path.write_text(VALID_DOCUMENT.replace("https://example.com/products/oppo-pad-4-pro", ""))

    errors = quality_module().validate_publishable_document(path)

    assert any("主要来源" in error for error in errors)


def test_unresolved_marker_in_answerable_body_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "PROD-999_oppo-pad-4-pro.md"
    path.write_text(VALID_DOCUMENT + "\n- 电池容量：待人工复核。\n", encoding="utf-8")

    errors = quality_module().validate_publishable_document(path)

    assert any("未核实标记" in error for error in errors)


def test_library_is_derived_from_brand() -> None:
    module = quality_module()

    assert module.library_for_brand("小米") == "小米生态核心库"
    assert module.library_for_brand("REDMI") == "小米生态核心库"
    assert module.library_for_brand("米家") == "小米生态核心库"
    assert module.library_for_brand("OPPO") == "竞品选购对比库"


def test_repository_product_libraries_are_publishable_and_complete() -> None:
    module = quality_module()
    core_files = sorted((PROJECT_ROOT / "data/knowledge/product-core").glob("PROD-*.md"))
    comparison_files = sorted(
        (PROJECT_ROOT / "data/knowledge/product-comparison").glob("PROD-*.md")
    )

    assert len(core_files) == 30
    assert len(comparison_files) == 20

    identifiers: set[str] = set()
    models: set[str] = set()
    for path in [*core_files, *comparison_files]:
        metadata, _body = module.parse_front_matter(path.read_text(encoding="utf-8-sig"))
        assert module.validate_publishable_document(path) == [], path.name
        assert metadata["文档编号"] not in identifiers
        assert metadata["型号"].lower() not in models
        identifiers.add(metadata["文档编号"])
        models.add(metadata["型号"].lower())

    assert len(identifiers) == 50
    assert len(models) == 50


def test_curated_libraries_ingest_with_sources_and_remain_isolated(
    client: TestClient, users: dict[str, str]
) -> None:
    operator_headers = auth_headers(client, "operator", users["operator"])
    user_headers = auth_headers(client, "customer", users["customer"])
    libraries = {
        "product-core": ("集成测试-小米生态核心库", 30),
        "product-comparison": ("集成测试-竞品选购对比库", 20),
    }
    knowledge_base_ids: dict[str, str] = {}

    for folder, (name, expected_count) in libraries.items():
        created = client.post(
            "/api/v1/knowledge-bases",
            headers=operator_headers,
            json={"name": name},
        )
        assert created.status_code == 201, created.text
        knowledge_base_id = created.json()["id"]
        knowledge_base_ids[folder] = knowledge_base_id
        paths = sorted((PROJECT_ROOT / "data/knowledge" / folder).glob("PROD-*.md"))
        assert len(paths) == expected_count

        for path in paths:
            metadata, _body = quality_module().parse_front_matter(
                path.read_text(encoding="utf-8-sig")
            )
            upload = client.post(
                "/api/v1/documents/upload",
                headers=operator_headers,
                data={
                    "knowledge_base_id": knowledge_base_id,
                    "source_url": metadata["主要来源"],
                    "chunk_size": "800",
                    "chunk_overlap": "120",
                },
                files={"file": (path.name, BytesIO(path.read_bytes()), "text/markdown")},
            )
            assert upload.status_code == 202, upload.text
            job = wait_for_job(client, operator_headers, upload.json()["job_id"])
            assert job["status"] == "succeeded", job

        analytics = client.get(
            f"/api/v1/knowledge-bases/{knowledge_base_id}/analytics",
            headers=operator_headers,
        )
        assert analytics.status_code == 200
        assert analytics.json()["ready_count"] == expected_count
        assert analytics.json()["failed_count"] == 0
        assert analytics.json()["product_count"] == expected_count
        assert analytics.json()["source_coverage"] == 1.0

    core_answer = client.post(
        "/api/v1/chat/completions",
        headers=user_headers,
        json={
            "knowledge_base_id": knowledge_base_ids["product-core"],
            "message": "小米 17 Ultra 的电池和充电参数是什么？",
        },
    )
    assert core_answer.status_code == 200
    assert core_answer.json()["fallback"] is False
    assert all(
        source["filename"].startswith("PROD-010_") for source in core_answer.json()["sources"]
    )
    assert all(source["source_url"] for source in core_answer.json()["sources"])

    comparison_answer = client.post(
        "/api/v1/chat/completions",
        headers=user_headers,
        json={
            "knowledge_base_id": knowledge_base_ids["product-comparison"],
            "message": "OPPO Pad 4 Pro 的屏幕和性能参数是什么？",
        },
    )
    assert comparison_answer.status_code == 200
    assert comparison_answer.json()["fallback"] is False
    assert all(
        source["filename"].startswith("PROD-030_") for source in comparison_answer.json()["sources"]
    )
    assert all(source["source_url"] for source in comparison_answer.json()["sources"])
