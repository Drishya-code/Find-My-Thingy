import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import sqlite
from app.core import config
from app.api import routes

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(sqlite, "DB_PATH", tmp_path / "test.sqlite3")
    monkeypatch.setattr(config.settings, "data_dir", tmp_path)
    (tmp_path / "uploads").mkdir()
    with TestClient(app) as c:
        yield c

def test_txt_upload_duplicate_list_and_delete(client, monkeypatch):
    monkeypatch.setattr(routes, "add", lambda *_: None)
    async def no_memories(*_): return None
    monkeypatch.setattr(routes, "extract_memories", no_memories)
    payload=b"A useful local note about binary search and sorted arrays."
    first=client.post("/api/documents/upload", files={"file":("study.txt",payload,"text/plain")})
    assert first.status_code == 200
    assert first.json()["status"] == "ready"
    rows=client.get("/api/documents").json()
    assert len(rows)==1 and rows[0]["filename"]=="study.txt"
    duplicate=client.post("/api/documents/upload", files={"file":("copy.txt",payload,"text/plain")})
    assert duplicate.status_code == 409
    deleted=client.delete("/api/documents/"+first.json()["id"])
    assert deleted.status_code==200
    assert client.get("/api/documents").json()==[]

def test_invalid_type_empty_document_and_chat_refusal(client):
    bad=client.post("/api/documents/upload",files={"file":("bad.exe",b"no","application/octet-stream")})
    assert bad.status_code==400
    empty=client.post("/api/documents/upload",files={"file":("empty.txt",b" ","text/plain")})
    assert empty.status_code==422
    refusal=client.post("/api/chat",json={"question":"What is the moon made of?"})
    assert refusal.status_code==200 and refusal.json()["insufficient_context"] is True
    assert refusal.json()["sources"]==[]

def test_pdf_pages_are_preserved(tmp_path):
    import fitz
    from app.services.extract import extract
    path=tmp_path/"pages.pdf"
    pdf=fitz.open()
    for title in ("first-page-marker", "second-page-marker"):
        page=pdf.new_page(); page.insert_text((72,72),title)
    pdf.save(path); pdf.close()
    pages=extract(path,"pdf")
    assert [page for page,_ in pages]==[1,2]
    assert "first-page-marker" in pages[0][1]
    assert "second-page-marker" in pages[1][1]

def test_chat_returns_only_retrieved_source_metadata(client, monkeypatch):
    hit={"text":"Binary search halves the search interval.","distance":0.12,
         "metadata":{"document_id":"doc-1","filename":"notes.md","page":3,"chunk_index":0}}
    monkeypatch.setattr(routes,"search",lambda *_:[hit])
    async def answer(*_): return "Binary search halves the interval [1]."
    monkeypatch.setattr(routes.ollama,"answer",answer)
    response=client.post("/api/chat",json={"question":"How does binary search work?"})
    assert response.status_code==200
    data=response.json()
    assert data["sources"]==[{"document_id":"doc-1","filename":"notes.md","page":3,
                              "passage":"Binary search halves the search interval.","relevance":0.88}]

def test_ollama_failure_is_reported_without_internal_error(client, monkeypatch):
    hit={"text":"Some saved fact.","distance":0.1,"metadata":{"document_id":"d","filename":"n.txt","page":0,"chunk_index":0}}
    monkeypatch.setattr(routes,"search",lambda *_:[hit])
    async def unavailable(*_): raise RuntimeError("Could not get a response from local Ollama.")
    monkeypatch.setattr(routes.ollama,"answer",unavailable)
    response=client.post("/api/chat",json={"question":"Tell me the fact"})
    assert response.status_code==503
    assert response.json()["detail"]=="Could not get a response from local Ollama."

def test_memory_deletion_and_dashboard_counts(client):
    from datetime import datetime, timezone
    with sqlite.connect() as db:
        db.execute("INSERT INTO documents (id,filename,safe_name,file_type,size,sha256,status,chunk_count,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                   ("doc","notes.md","doc.md","md",10,"abc","ready",2,datetime.now(timezone.utc).isoformat()))
        db.execute("INSERT INTO memories VALUES (?,?,?,?,?,?)",("memory","doc","Binary search halves the range.","fact",2,datetime.now(timezone.utc).isoformat()))
    dashboard=client.get("/api/dashboard").json()
    assert dashboard["documents"]==1 and dashboard["memories"]==1
    assert client.delete("/api/memories/memory").json()=={"deleted":True}
    assert client.get("/api/memories").json()==[]
