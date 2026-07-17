import time
from io import BytesIO

from docx import Document as WordDocument
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from tests.conftest import auth_headers


def create_knowledge_base(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={"name": "产品资料库"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def wait_for_job(client: TestClient, headers: dict[str, str], job_id: str) -> dict:
    for _ in range(100):
        response = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        if data["status"] in {"succeeded", "failed"}:
            return data
        time.sleep(0.02)
    raise AssertionError("processing job did not finish")


def test_text_upload_is_safely_stored_processed_and_previewed(
    client: TestClient, users: dict[str, str]
) -> None:
    headers = auth_headers(client, "operator", users["operator"])
    knowledge_base_id = create_knowledge_base(client, headers)
    text = "# 小米 14\n小米 14 支持 90W 有线快充。\n\n屏幕尺寸为 6.36 英寸。"

    response = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={"knowledge_base_id": knowledge_base_id, "chunk_size": "200", "chunk_overlap": "20"},
        files={"file": ("../../小米14.md", BytesIO(text.encode()), "text/markdown")},
    )

    assert response.status_code == 202
    body = response.json()
    job = wait_for_job(client, headers, body["job_id"])
    assert job["status"] == "succeeded", job

    document = client.get(f"/api/v1/documents/{body['document_id']}", headers=headers).json()
    chunks = client.get(f"/api/v1/documents/{body['document_id']}/chunks", headers=headers).json()
    assert document["original_filename"] == "小米14.md"
    assert ".." not in document["stored_filename"]
    assert document["status"] == "ready"
    assert chunks["total"] >= 1
    assert "90W" in "".join(item["text"] for item in chunks["items"])
    assert any("小米 14" in item["product_models"] for item in chunks["items"])


def test_unsupported_or_spoofed_upload_is_rejected(
    client: TestClient, users: dict[str, str]
) -> None:
    headers = auth_headers(client, "operator", users["operator"])
    knowledge_base_id = create_knowledge_base(client, headers)

    response = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={"knowledge_base_id": knowledge_base_id},
        files={"file": ("malware.pdf", BytesIO(b"not a pdf"), "application/pdf")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "invalid_file_signature"


def test_delete_document_removes_chunks(client: TestClient, users: dict[str, str]) -> None:
    headers = auth_headers(client, "operator", users["operator"])
    knowledge_base_id = create_knowledge_base(client, headers)
    upload = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={"knowledge_base_id": knowledge_base_id},
        files={"file": ("guide.txt", BytesIO("产品使用说明".encode()), "text/plain")},
    ).json()
    wait_for_job(client, headers, upload["job_id"])

    response = client.delete(f"/api/v1/documents/{upload['document_id']}", headers=headers)

    assert response.status_code == 204
    missing = client.get(f"/api/v1/documents/{upload['document_id']}", headers=headers)
    assert missing.status_code == 404


def test_docx_and_pdf_formats_are_processed(client: TestClient, users: dict[str, str]) -> None:
    headers = auth_headers(client, "operator", users["operator"])
    knowledge_base_id = create_knowledge_base(client, headers)
    word_buffer = BytesIO()
    word = WordDocument()
    word.add_heading("小米 14 使用说明", level=1)
    word.add_paragraph("小米 14 支持 90W 有线快充。")
    word.save(word_buffer)
    pdf_buffer = BytesIO()
    pdf = canvas.Canvas(pdf_buffer)
    pdf.drawString(72, 760, "Xiaomi 14 supports 90W wired charging.")
    pdf.save()

    uploads = [
        (
            "guide.docx",
            word_buffer.getvalue(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        ("xiaomi14-reference.pdf", pdf_buffer.getvalue(), "application/pdf"),
    ]
    for filename, content, media_type in uploads:
        response = client.post(
            "/api/v1/documents/upload",
            headers=headers,
            data={"knowledge_base_id": knowledge_base_id},
            files={"file": (filename, BytesIO(content), media_type)},
        )
        assert response.status_code == 202
        job = wait_for_job(client, headers, response.json()["job_id"])
        assert job["status"] == "succeeded", job


def test_duplicate_upload_is_rejected(client: TestClient, users: dict[str, str]) -> None:
    headers = auth_headers(client, "operator", users["operator"])
    knowledge_base_id = create_knowledge_base(client, headers)
    payload = b"same document content"

    first = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={"knowledge_base_id": knowledge_base_id},
        files={"file": ("first.txt", BytesIO(payload), "text/plain")},
    )
    second = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={"knowledge_base_id": knowledge_base_id},
        files={"file": ("second.txt", BytesIO(payload), "text/plain")},
    )

    assert first.status_code == 202
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "document_exists"
