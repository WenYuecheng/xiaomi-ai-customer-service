import argparse
import csv
import html
import json
import re
import shutil
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import httpx


BLOCK_TAGS = {
    "article",
    "br",
    "div",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "header",
    "li",
    "main",
    "p",
    "section",
    "table",
    "td",
    "th",
    "tr",
    "ul",
}


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skipped = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        del attrs
        if tag in {"script", "style", "noscript", "svg"}:
            self.skipped += 1
        elif tag in BLOCK_TAGS and not self.skipped:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self.skipped = max(0, self.skipped - 1)
        elif tag in BLOCK_TAGS and not self.skipped:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skipped and data.strip():
            self.parts.append(data.strip())


def official_url(value: str) -> bool:
    hostname = (urlparse(value).hostname or "").lower()
    return hostname == "mi.com" or hostname.endswith(".mi.com")


def extract_json_strings(raw: str) -> list[str]:
    values = []
    pattern = r'"(?:title|description|text|content)"\s*:\s*("(?:\\.|[^"\\])*")'
    for match in re.finditer(pattern, raw):
        try:
            value = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(value, str) and len(value.strip()) >= 12:
            values.append(re.sub(r"<[^>]+>", " ", value))
    return values


def extract_seo_summary(raw: str) -> list[str]:
    values: list[str] = []
    for key, heading in (
        ("seo_title", "产品名称"),
        ("seo_description", "产品概述"),
        ("seo_keywords", "核心规格与功能"),
    ):
        match = re.search(rf'"{key}"\s*:\s*("(?:\\.|[^"\\])*")', raw)
        if not match:
            continue
        try:
            value = json.loads(match.group(1)).strip()
        except (json.JSONDecodeError, AttributeError):
            continue
        if value:
            values.append(f"## {heading}\n{value}")
    return values


def clean_lines(raw: str) -> list[str]:
    if "$GLOBAL_PAGE_INFO" in raw:
        summary = extract_seo_summary(raw)
        if sum(map(len, summary)) >= 80:
            return summary
    parser = VisibleTextParser()
    parser.feed(raw)
    combined = "\n".join([*parser.parts, *extract_json_strings(raw)])
    lines: list[str] = []
    seen: set[str] = set()
    for value in combined.splitlines():
        line = re.sub(r"\s+", " ", html.unescape(value)).strip(" -|\t")
        if len(line) < 2 or line in seen:
            continue
        if line in {"立即购买", "咨询客服", "F码通道", "概述页", "参数页"}:
            continue
        seen.add(line)
        lines.append(line)
    return lines


def sections(lines: list[str], target_size: int = 2600) -> list[str]:
    result: list[str] = []
    current: list[str] = []
    size = 0
    for line in lines:
        current.append(line)
        size += len(line)
        if size >= target_size:
            result.append("\n\n".join(current))
            current, size = [], 0
    if current:
        if result and size < 500:
            result[-1] += "\n\n" + "\n\n".join(current)
        else:
            result.append("\n\n".join(current))
    return [item for item in result if len(item) >= 120]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect traceable Xiaomi official knowledge"
    )
    parser.add_argument(
        "--manifest", type=Path, default=Path("data/knowledge/manifest.csv")
    )
    parser.add_argument("--output", type=Path, default=Path("data/knowledge/official"))
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if args.output.exists():
        shutil.rmtree(args.output)
    args.output.mkdir(parents=True)
    rows = list(csv.DictReader(args.manifest.open(encoding="utf-8")))
    if args.limit:
        rows = rows[: args.limit]
    failures: list[str] = []
    document_count = 0
    with httpx.Client(
        follow_redirects=True,
        timeout=30,
        trust_env=False,
        headers={"User-Agent": "Mozilla/5.0 XiaomiKnowledgeBot/1.0"},
    ) as client:
        for row in rows:
            url = row["url"]
            if not official_url(url):
                failures.append(f"{row['id']}: non-official URL")
                continue
            try:
                response = client.get(url)
                response.raise_for_status()
                raw = response.text
                chunks = sections(clean_lines(raw))
                if not chunks:
                    raise ValueError("no substantial visible content")
                for index, content in enumerate(chunks, start=1):
                    filename = f"{row['id']}-{index:02d}.md"
                    title = f"{row['product_models'] or row['category']} · 官方资料第 {index} 部分"
                    metadata = (
                        f"title: {title}\nsource_url: {url}\ncaptured_at: {date.today().isoformat()}\n"
                        f"market: CN\ncategory: {row['category']}\nproduct_models: {row['product_models']}\n"
                        "content_type: xiaomi-official-page\n\n"
                    )
                    (args.output / filename).write_text(
                        metadata + f"# {title}\n\n" + content + "\n", encoding="utf-8"
                    )
                    document_count += 1
                print(f"{row['id']}: {len(chunks)} documents")
            except (
                Exception
            ) as exc:  # network and third-party HTML failures are reported per source
                failures.append(f"{row['id']}: {exc}")
    print(f"sources={len(rows)} documents={document_count} failures={len(failures)}")
    for failure in failures:
        print(f"FAILED {failure}")
    if document_count < 45:
        raise SystemExit("Collected fewer than 45 substantial official documents")


if __name__ == "__main__":
    main()
