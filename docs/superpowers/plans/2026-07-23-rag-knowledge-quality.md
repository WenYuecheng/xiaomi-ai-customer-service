# RAG Knowledge Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the 50 PR 1 product documents into two traceable RAG libraries, validate all runtime metadata, and deploy them with the teammate frontend without contaminating the current Docker data before verification.

**Architecture:** A small quality module parses document front matter and enforces the publication contract. The ingestion parser consumes the same metadata for generic model extraction, while a cross-platform Python importer creates separate Xiaomi-core and competitor-comparison knowledge bases and forwards each source URL to the existing API.

**Tech Stack:** Python 3.11, FastAPI, Pydantic 2, LangChain text splitters, Chroma, openpyxl, pytest, Docker Compose.

## Global Constraints

- Core knowledge contains only Xiaomi, REDMI, and Mijia documents; comparison knowledge contains all other brands.
- A publishable document has a valid source URL and contains no unresolved-review markers in its answerable body.
- Automated processing never claims to be human review.
- No DeepSeek call may be used to invent or complete product facts.
- Existing Docker data must be backed up before import and retained in its named volume.

---

### Task 1: Quality contract and failing data tests

**Files:**
- Create: `backend/app/ingestion/knowledge_quality.py`
- Create: `backend/tests/test_product_knowledge_quality.py`
- Modify: `backend/app/ingestion/parsers.py`

**Interfaces:**
- Produces: `parse_front_matter(text: str) -> tuple[dict[str, str], str]`
- Produces: `validate_publishable_document(path: Path) -> list[str]`
- Produces: `extract_product_models(text: str) -> list[str]` with front-matter model support.

- [ ] Write tests asserting a metadata model such as `型号: "OPPO Pad 4 Pro"` is extracted as `oppo pad 4 pro`, missing/invalid source URLs fail validation, and unresolved markers in the answerable body fail validation.
- [ ] Run `pytest backend/tests/test_product_knowledge_quality.py -v` and confirm failures are caused by the missing quality module and generic entity behavior.
- [ ] Implement strict front-matter parsing, URL validation, unresolved-marker detection, library classification, and front-matter-first model extraction.
- [ ] Run the focused tests and the existing parser/document tests.
- [ ] Commit with `feat: enforce product knowledge quality contract`.

### Task 2: Curate and split the 50 documents

**Files:**
- Create: `data/knowledge/product-core/*.md`
- Create: `data/knowledge/product-comparison/*.md`
- Move: `近两年产品参数知识库_待审核/产品来源与人工审核表.xlsx` to `data/knowledge/audits/product-source-review.xlsx`
- Remove after migration: `近两年产品参数知识库_待审核/`

**Interfaces:**
- Consumes the source table columns `品牌`, `产品名称`, `主要来源`, `来源类型`, `来源等级`, `价格来源`.
- Produces exactly 30 core and 20 comparison Markdown documents satisfying Task 1.

- [ ] Add a failing repository test asserting counts 30/20, unique document IDs/models, complete source metadata, and zero unresolved markers in publishable bodies.
- [ ] Run the test and confirm the current staging directory fails source coverage and status requirements.
- [ ] Transform each Markdown front matter with `主要来源`, `来源类型`, `来源等级`, `价格来源`, `知识库`, and `审核状态: "可入库（来源关联，待人工终审）"`; remove unresolved factual lines from the answerable body and preserve them under a non-indexed audit-note metadata field.
- [ ] Update the workbook with `最终分库` and `自动质量检查` columns while preserving its style and formulas.
- [ ] Run the repository quality test and workbook formula/error scan.
- [ ] Commit with `data: curate product knowledge into isolated libraries`.

### Task 3: Cross-platform dual-library importer

**Files:**
- Create: `scripts/ingest_product_knowledge.py`
- Create: `backend/tests/test_product_knowledge_importer.py`
- Keep: `scripts/ingest_product_knowledge.ps1` as a documented Windows wrapper or compatibility tool.

**Interfaces:**
- Produces CLI options `--base-url`, `--username`, `--password-env`, `--core-name`, `--comparison-name`, and `--documents-root`.
- Uploads `source_url` from front matter and routes documents by `知识库`.

- [ ] Write failing tests for deterministic split routing, source URL forwarding, duplicate skipping, and rejection of non-publishable documents.
- [ ] Run focused tests and verify expected failures.
- [ ] Implement the Python importer using the existing login, knowledge-base, document-upload, job-status, and analytics APIs.
- [ ] Run focused tests and Ruff.
- [ ] Commit with `feat: add validated dual knowledge importer`.

### Task 4: Isolated end-to-end RAG verification

**Files:**
- Modify: `backend/tests/test_product_knowledge_quality.py`
- Create: `data/evaluation/product-knowledge-smoke.csv`

**Interfaces:**
- Uses temporary SQLite, upload, Chroma, and model directories with mock LLM/hash embeddings.
- Produces proof for 50 ready documents, 0 failed documents, 100% source coverage, and 50 extracted products across both libraries.

- [ ] Add integration assertions that Xiaomi queries cite only the core library and competitor queries cite only the comparison library.
- [ ] Run the new tests, verify any failing retrieval case, and minimally adjust test questions or metadata extraction without weakening isolation.
- [ ] Run Ruff and the full backend suite.
- [ ] Commit with `test: verify curated RAG libraries end to end`.

### Task 5: Merge, Docker rebuild, import, and browser acceptance

**Files:**
- Modify: `README.md`
- Modify: `docs/testing/test-report.md`
- Modify: `docs/demo-script.md`

**Interfaces:**
- Uses the current named Docker data volume and teammate frontend source already present in the PR lineage.
- Exposes frontend at `http://localhost:8080` and backend health at `http://localhost:8000/api/v1/health`.

- [ ] Record the validated dual-library commands and quality boundaries in README and test documentation.
- [ ] Run full backend tests, frontend tests, TypeScript build, secret scan, and `git diff --check`.
- [ ] Commit documentation with `docs: record curated knowledge deployment`.
- [ ] Merge `codex/rag-knowledge-quality` into local `main`, preserving the teammate and member commits.
- [ ] Back up the Docker data volume, rebuild the backend and teammate frontend, start both services, and run the Python importer with local credentials without printing secrets.
- [ ] Verify health, two knowledge-base analytics responses, representative core/comparison answers and sources, then open the frontend for user acceptance.
