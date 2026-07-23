"""Validate and import the curated product libraries through the public API."""

import argparse
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.ingestion.knowledge_quality import (  # noqa: E402
    COMPARISON_LIBRARY,
    CORE_LIBRARY,
    parse_front_matter,
    validate_publishable_document,
)


@dataclass(frozen=True)
class ProductDocument:
    path: Path
    library: str
    source_url: str


def discover_documents(root: Path) -> list[ProductDocument]:
    """Load only documents that satisfy the publication contract."""
    documents: list[ProductDocument] = []
    for folder in (root / "product-core", root / "product-comparison"):
        for path in sorted(folder.glob("PROD-*.md")):
            errors = validate_publishable_document(path)
            if errors:
                raise ValueError(f"{path.name}: {'; '.join(errors)}")
            metadata, _body = parse_front_matter(path.read_text(encoding="utf-8-sig"))
            documents.append(
                ProductDocument(
                    path=path,
                    library=metadata["知识库"],
                    source_url=metadata["主要来源"],
                )
            )
    return documents


def build_upload_data(document: ProductDocument, knowledge_base_id: str) -> dict[str, str]:
    return {
        "knowledge_base_id": knowledge_base_id,
        "source_url": document.source_url,
        "chunk_size": "800",
        "chunk_overlap": "120",
    }


def pending_documents(
    documents: list[ProductDocument], existing_filenames: set[str]
) -> list[ProductDocument]:
    return [document for document in documents if document.path.name not in existing_filenames]


def get_or_create_knowledge_base(
    client: httpx.Client,
    headers: dict[str, str],
    name: str,
    description: str,
) -> str:
    response = client.get("/knowledge-bases", headers=headers, params={"q": name})
    response.raise_for_status()
    existing = next((item for item in response.json()["items"] if item["name"] == name), None)
    if existing:
        return existing["id"]
    response = client.post(
        "/knowledge-bases",
        headers=headers,
        json={"name": name, "description": description},
    )
    response.raise_for_status()
    return response.json()["id"]


def import_library(
    client: httpx.Client,
    headers: dict[str, str],
    knowledge_base_id: str,
    documents: list[ProductDocument],
) -> dict[str, object]:
    response = client.get(
        "/documents", headers=headers, params={"knowledge_base_id": knowledge_base_id}
    )
    response.raise_for_status()
    existing = {item["original_filename"] for item in response.json()["items"]}
    jobs: list[tuple[str, str]] = []
    for document in pending_documents(documents, existing):
        with document.path.open("rb") as file:
            response = client.post(
                "/documents/upload",
                headers=headers,
                data=build_upload_data(document, knowledge_base_id),
                files={"file": (document.path.name, file, "text/markdown")},
            )
        response.raise_for_status()
        jobs.append((document.path.name, response.json()["job_id"]))

    failures: list[dict[str, str]] = []
    for filename, job_id in jobs:
        for _attempt in range(720):
            response = client.get(f"/jobs/{job_id}", headers=headers)
            response.raise_for_status()
            job = response.json()
            if job["status"] in {"succeeded", "failed", "cancelled"}:
                if job["status"] != "succeeded":
                    failures.append(
                        {"filename": filename, "status": job["status"], "error": job["error_message"]}
                    )
                break
            time.sleep(0.25)
        else:
            failures.append({"filename": filename, "status": "timeout", "error": "等待超时"})

    analytics = client.get(
        f"/knowledge-bases/{knowledge_base_id}/analytics", headers=headers
    )
    analytics.raise_for_status()
    return {
        "knowledge_base_id": knowledge_base_id,
        "uploaded": len(jobs),
        "skipped": len(documents) - len(jobs),
        "failures": failures,
        "analytics": analytics.json(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="导入经过质量校验的双产品知识库")
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--username", default=os.getenv("INGEST_USERNAME", "operator"))
    parser.add_argument("--password-env", default="INGEST_PASSWORD")
    parser.add_argument("--documents-root", type=Path, default=Path("data/knowledge"))
    parser.add_argument("--core-name", default=CORE_LIBRARY)
    parser.add_argument("--comparison-name", default=COMPARISON_LIBRARY)
    args = parser.parse_args()
    password = os.getenv(args.password_env)
    if not password:
        raise SystemExit(f"请通过环境变量 {args.password_env} 提供密码")

    documents = discover_documents(args.documents_root)
    grouped = {
        CORE_LIBRARY: [item for item in documents if item.library == CORE_LIBRARY],
        COMPARISON_LIBRARY: [item for item in documents if item.library == COMPARISON_LIBRARY],
    }
    names = {CORE_LIBRARY: args.core_name, COMPARISON_LIBRARY: args.comparison_name}
    descriptions = {
        CORE_LIBRARY: "30 份小米、REDMI、米家产品资料；来源已关联，仍保留人工终审边界。",
        COMPARISON_LIBRARY: "20 份竞品参数资料；仅用于选购和对比，不参与小米客服核心问答。",
    }

    results = {}
    with httpx.Client(base_url=args.base_url, timeout=60, trust_env=False) as client:
        login = client.post(
            "/auth/login", data={"username": args.username, "password": password}
        )
        login.raise_for_status()
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        for library in (CORE_LIBRARY, COMPARISON_LIBRARY):
            knowledge_base_id = get_or_create_knowledge_base(
                client, headers, names[library], descriptions[library]
            )
            results[library] = import_library(
                client, headers, knowledge_base_id, grouped[library]
            )

    failed = False
    for library, result in results.items():
        analytics = result["analytics"]
        print(
            f"{library}: knowledge_base_id={result['knowledge_base_id']} "
            f"uploaded={result['uploaded']} skipped={result['skipped']} "
            f"ready={analytics['ready_count']} chunks={analytics['chunk_count']} "
            f"sources={analytics['source_coverage']:.0%}"
        )
        failed = failed or bool(result["failures"])
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
