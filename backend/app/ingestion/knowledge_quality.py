"""Quality contract for publishable product knowledge documents."""

from pathlib import Path
from urllib.parse import urlparse

CORE_BRANDS = {"小米", "redmi", "米家"}
CORE_LIBRARY = "小米生态核心库"
COMPARISON_LIBRARY = "竞品选购对比库"
REQUIRED_METADATA = (
    "文档编号",
    "标题",
    "类别",
    "品牌",
    "型号",
    "发布或上市",
    "语言",
    "整理日期",
    "审核状态",
    "主要来源",
    "来源类型",
    "来源等级",
    "价格来源",
    "知识库",
)
UNRESOLVED_MARKERS = ("待复核", "待确认", "待人工", "需复核")


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    """Return simple scalar front matter and the answerable Markdown body."""
    normalized = text.lstrip("\ufeff")
    lines = normalized.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, normalized
    try:
        closing = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        return {}, normalized

    metadata: dict[str, str] = {}
    for line in lines[1:closing]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata, "\n".join(lines[closing + 1 :]).strip()


def library_for_brand(brand: str) -> str:
    """Classify a brand into the isolated runtime knowledge library."""
    return CORE_LIBRARY if brand.strip().lower() in CORE_BRANDS else COMPARISON_LIBRARY


def is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_publishable_document(path: Path) -> list[str]:
    """Return deterministic publication-contract violations for one Markdown file."""
    metadata, body = parse_front_matter(path.read_text(encoding="utf-8-sig"))
    errors = [
        f"缺少元数据：{key}" for key in REQUIRED_METADATA if not metadata.get(key, "").strip()
    ]

    for key in ("主要来源", "价格来源"):
        value = metadata.get(key, "")
        if value and not is_http_url(value):
            errors.append(f"{key}不是有效 HTTP URL")

    status = metadata.get("审核状态", "")
    if status and not status.startswith("可入库"):
        errors.append("审核状态不是可入库")

    brand = metadata.get("品牌", "")
    expected_library = library_for_brand(brand) if brand else ""
    if expected_library and metadata.get("知识库") != expected_library:
        errors.append(f"知识库应为：{expected_library}")

    for marker in UNRESOLVED_MARKERS:
        if marker in body:
            errors.append(f"可回答正文包含未核实标记：{marker}")
    return errors
