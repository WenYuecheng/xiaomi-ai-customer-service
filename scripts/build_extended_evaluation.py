import csv
from pathlib import Path


def main() -> None:
    manifest_path = Path("data/knowledge/manifest.csv")
    official_dir = Path("data/knowledge/official")
    source_questions = Path("data/evaluation/questions.csv")
    output = Path("data/evaluation/questions-expanded.csv")
    with source_questions.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    with manifest_path.open(encoding="utf-8", newline="") as file:
        manifest = list(csv.DictReader(file))
    next_id = len(rows) + 1
    for item in manifest:
        files = sorted(official_dir.glob(f"{item['id']}-*.md"))
        if not files:
            continue
        subject = (
            item["product_models"].split("|")[0]
            if item["product_models"]
            else item["category"]
        )
        for question in (
            f"根据小米官方资料，请介绍{subject}。",
            f"{subject}有哪些核心规格、功能或服务说明？",
        ):
            rows.append(
                {
                    "id": f"Q{next_id:03d}",
                    "question": question,
                    "expected_keywords": subject,
                    "source_file": files[0].name,
                }
            )
            next_id += 1
    with output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file, fieldnames=["id", "question", "expected_keywords", "source_file"]
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"questions={len(rows)} output={output}")


if __name__ == "__main__":
    main()
