import argparse
import os
import time
from pathlib import Path

import httpx


def source_url(path: Path) -> str | None:
    for line in path.read_text(encoding="utf-8").splitlines()[:12]:
        if line.startswith("source_url:"):
            return line.partition(":")[2].strip() or None
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload the official public demo samples"
    )
    parser.add_argument("--samples", type=Path, default=Path("data/samples"))
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--username", default=os.getenv("INGEST_USERNAME", "operator"))
    parser.add_argument("--password", default=os.getenv("INGEST_PASSWORD"))
    parser.add_argument("--knowledge-base-id")
    parser.add_argument("--knowledge-base-name")
    parser.add_argument(
        "--description", default="小米官方公开资料；每份文档保留来源和采集日期。"
    )
    args = parser.parse_args()
    if not args.password:
        raise SystemExit(
            "Set INGEST_PASSWORD; credentials are not accepted on the command line"
        )

    with httpx.Client(base_url=args.base_url, timeout=60, trust_env=False) as client:
        login = client.post(
            "/auth/login", data={"username": args.username, "password": args.password}
        )
        login.raise_for_status()
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        knowledge_base_id = args.knowledge_base_id
        if not knowledge_base_id:
            response = client.post(
                "/knowledge-bases",
                headers=headers,
                json={
                    "name": args.knowledge_base_name
                    or f"小米官方公开资料-{int(time.time())}",
                    "description": args.description,
                },
            )
            response.raise_for_status()
            knowledge_base_id = response.json()["id"]

        jobs: list[tuple[str, str]] = []
        for path in sorted(args.samples.glob("*.md")):
            if path.name == "SOURCES.md":
                continue
            with path.open("rb") as file:
                data = {"knowledge_base_id": knowledge_base_id}
                if url := source_url(path):
                    data["source_url"] = url
                response = client.post(
                    "/documents/upload",
                    headers=headers,
                    data=data,
                    files={"file": (path.name, file, "text/markdown")},
                )
            response.raise_for_status()
            jobs.append((path.name, response.json()["job_id"]))

        failures: list[str] = []
        for filename, job_id in jobs:
            for _ in range(120):
                response = client.get(f"/jobs/{job_id}", headers=headers)
                response.raise_for_status()
                job = response.json()
                if job["status"] in {"succeeded", "failed", "cancelled"}:
                    print(f"{filename}: {job['status']}")
                    if job["status"] != "succeeded":
                        failures.append(filename)
                    break
                time.sleep(0.25)
            else:
                failures.append(filename)
        print(f"knowledge_base_id={knowledge_base_id}")
        raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
