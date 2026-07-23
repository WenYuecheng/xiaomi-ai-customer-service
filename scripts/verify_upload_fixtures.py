"""通过真实 HTTP API 验收 PDF、DOCX、TXT、MD 四种上传格式。"""

import argparse
import os
import time
from pathlib import Path

import httpx

MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument("--fixtures", type=Path, default=Path("data/upload-fixtures"))
    parser.add_argument("--username", default="operator")
    parser.add_argument("--knowledge-base-name", default="文件上传验收库")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    password = os.getenv("INGEST_PASSWORD") or os.getenv("INITIAL_OPERATOR_PASSWORD")
    token = os.getenv("INGEST_TOKEN")
    if not password and not token:
        raise SystemExit(
            "请设置 INGEST_TOKEN、INGEST_PASSWORD 或 INITIAL_OPERATOR_PASSWORD"
        )
    with httpx.Client(base_url=args.base_url, timeout=30) as client:
        if not token:
            login = client.post(
                "/auth/login", data={"username": args.username, "password": password}
            )
            login.raise_for_status()
            token = login.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
        libraries = client.get("/knowledge-bases").json()["items"]
        library = next(
            (item for item in libraries if item["name"] == args.knowledge_base_name),
            None,
        )
        if not library:
            response = client.post(
                "/knowledge-bases",
                json={
                    "name": args.knowledge_base_name,
                    "description": "四格式上传功能验收专用",
                },
            )
            response.raise_for_status()
            library = response.json()
        for path in sorted(args.fixtures.glob("upload-verification.*")):
            if path.suffix not in MEDIA_TYPES:
                continue
            with path.open("rb") as stream:
                response = client.post(
                    "/documents/upload",
                    data={"knowledge_base_id": library["id"]},
                    files={"file": (path.name, stream, MEDIA_TYPES[path.suffix])},
                )
            if response.status_code == 409:
                print(f"{path.name}: already_exists")
                continue
            response.raise_for_status()
            job_id = response.json()["job_id"]
            for _ in range(60):
                job = client.get(f"/jobs/{job_id}").json()
                if job["status"] in {"succeeded", "failed", "cancelled"}:
                    print(f"{path.name}: {job['status']}")
                    if job["status"] != "succeeded":
                        raise SystemExit(1)
                    break
                time.sleep(0.2)
            else:
                raise SystemExit(f"{path.name}: timeout")
        print(f"knowledge_base_id={library['id']}")


if __name__ == "__main__":
    main()
