from importlib import import_module
from pathlib import Path

from app.ingestion.parsers import extract_product_models

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
