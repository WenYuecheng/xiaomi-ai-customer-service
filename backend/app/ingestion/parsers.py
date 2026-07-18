"""
文件职责：
负责不同文件格式（pdf, docx, txt, md）的内容抽取和智能分块。

所属功能：
文档接入与处理 -> 解析与分块 (Chunking)。
"""

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from docx import Document as WordDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader


@dataclass(frozen=True)
class ParsedSection:
    """代表从原始文档中粗略抽取的片段及其物理位置描述（如页码）"""

    text: str
    location: str


def clean_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).replace("\x00", "")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in value.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def load_sections(path: Path) -> list[ParsedSection]:
    """
    功能归属：文档解析。
    根据文件后缀调度对应库（pypdf, python-docx）抽取出全文并附带简单位置。
    """
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return [ParsedSection(clean_text(path.read_text(encoding="utf-8-sig")), "全文")]
    if suffix == ".pdf":
        reader = PdfReader(path)
        return [
            ParsedSection(clean_text(page.extract_text() or ""), f"第 {index} 页")
            for index, page in enumerate(reader.pages, start=1)
            if clean_text(page.extract_text() or "")
        ]
    if suffix == ".docx":
        document = WordDocument(path)
        blocks = [paragraph.text for paragraph in document.paragraphs]
        for table in document.tables:
            blocks.extend(" | ".join(cell.text for cell in row.cells) for row in table.rows)
        return [ParsedSection(clean_text("\n".join(blocks)), "全文")]
    raise ValueError(f"unsupported document suffix: {suffix}")


PRODUCT_MODEL_PATTERNS = (
    re.compile(r"(?:小米|Xiaomi)\s*(\d+(?:\s*(?:Pro|Ultra|Max))?)", re.IGNORECASE),
    re.compile(r"(?:红米|Redmi)\s*([A-Za-z]*\s*\d+(?:\s*(?:Pro|Ultra|Max))?)", re.IGNORECASE),
    re.compile(r"Smart\s+Band\s*(\d+(?:\s*Pro)?)", re.IGNORECASE),
    re.compile(r"Robot\s+Vacuum\s*(\d+(?:\s*Pro)?)", re.IGNORECASE),
    re.compile(r"(?:米家|Mijia)\s*([A-Za-z]*\s*\d+(?:\s*(?:Pro|Ultra|Max))?)", re.IGNORECASE),
    re.compile(r"\b([TX]\d+(?:\s*Pro)?)\b", re.IGNORECASE),
)


def extract_product_models(text: str) -> list[str]:
    """
    内部辅助函数：
    使用正则表达式，从切分后的文本块中提取产品型号名称。
    用于知识图谱的建立及后期查询过滤。
    """
    models: set[str] = set()
    labels = ("小米", "红米", "Smart Band", "Robot Vacuum", "米家", "")
    for pattern, label in zip(PRODUCT_MODEL_PATTERNS, labels, strict=True):
        for match in pattern.findall(text):
            suffix = re.sub(r"\s+", " ", match).strip()
            models.add(f"{label} {suffix}".strip().lower())
    return sorted(models)


def split_sections(
    sections: list[ParsedSection], chunk_size: int, chunk_overlap: int
) -> list[tuple[str, str, list[str]]]:
    """
    功能归属：文档分块。
    使用 Langchain 的 `RecursiveCharacterTextSplitter` 对粗略提取的章节
    按字数和重叠长度进行平滑切分。
    在此环节中调用 `extract_product_models` 获取每个切块对应的产品实体。
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=[
            "\n# ",
            "\n## ",
            "\n\n",
            "\n",
            "。",
            "；",
            "，",
            "",
        ],
    )
    chunks: list[tuple[str, str, list[str]]] = []
    for section in sections:
        for text in splitter.split_text(section.text):
            cleaned = clean_text(text)
            if cleaned:
                chunks.append((cleaned, section.location, extract_product_models(cleaned)))
    return chunks
