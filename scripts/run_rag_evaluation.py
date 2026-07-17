import argparse
import csv
import os
from pathlib import Path

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the 30-question RAG regression set"
    )
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--knowledge-base-id", required=True)
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--username", default=os.getenv("EVAL_USERNAME", "customer"))
    parser.add_argument("--password", default=os.getenv("EVAL_PASSWORD"))
    args = parser.parse_args()
    if not args.password:
        raise SystemExit(
            "Set EVAL_PASSWORD instead of passing a password on the command line"
        )
    with httpx.Client(base_url=args.base_url, timeout=60, trust_env=False) as client:
        login = client.post(
            "/auth/login", data={"username": args.username, "password": args.password}
        )
        login.raise_for_status()
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        with args.questions.open(encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))
        passed = 0
        failures = []
        for row in rows:
            response = client.post(
                "/chat/completions",
                headers=headers,
                json={
                    "knowledge_base_id": args.knowledge_base_id,
                    "message": row["question"],
                },
            )
            response.raise_for_status()
            result = response.json()
            keywords = [
                item.strip().lower() for item in row["expected_keywords"].split("|")
            ]
            answer = result["answer"].lower()
            success = all(keyword in answer for keyword in keywords) and (
                bool(result["sources"]) or result["fallback"]
            )
            passed += int(success)
            if not success:
                failures.append({"id": row["id"], "answer": result["answer"]})
        accuracy = passed / len(rows) if rows else 0
        print(f"passed={passed}/{len(rows)} accuracy={accuracy:.2%}")
        for failure in failures:
            print(f"FAIL {failure['id']}: {failure['answer']}")
        raise SystemExit(0 if accuracy >= 0.8 else 1)


if __name__ == "__main__":
    main()
