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
    class IsolatedCollection:
        def count(self): return 0
        def delete(self, **_): return None
    monkeypatch.setattr(routes, "collection", IsolatedCollection())
    monkeypatch.setattr(routes, "remove_document", lambda *_: None)
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
    assert client.get("/api/documents/"+first.json()["id"]).json()["filename"]=="study.txt"
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
                              "passage":"Binary search halves the search interval.","relevance":round(routes.relevance(0.12),3)}]

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

def test_oversized_upload_is_rejected_before_writing(client, monkeypatch):
    monkeypatch.setattr(config.settings, "max_upload_mb", 1)
    response=client.post("/api/documents/upload",files={"file":("large.txt",b"x"*(1024*1024+1),"text/plain")})
    assert response.status_code==413
    assert client.get("/api/documents").json()==[]

def test_index_failure_rolls_back_uploaded_file_and_metadata(client, monkeypatch):
    def fail_index(*_): raise RuntimeError("test index failure")
    monkeypatch.setattr(routes,"add",fail_index)
    async def no_memories(*_): return None
    monkeypatch.setattr(routes,"extract_memories",no_memories)
    response=client.post("/api/documents/upload",files={"file":("index-failure.txt",b"Unique rollback test content.","text/plain")})
    assert response.status_code==422
    assert client.get("/api/documents").json()==[]
    assert list((config.settings.data_dir/"uploads").iterdir())==[]

def test_model_refusal_is_normalized_and_still_returns_retrieved_source(client, monkeypatch):
    hit={"text":"The note contains no answer to that question.","distance":0.1,
         "metadata":{"document_id":"d","filename":"notes.txt","page":0,"chunk_index":0}}
    monkeypatch.setattr(routes,"search",lambda *_:[hit])
    async def answer(*_): return "I couldn't find enough relevant information in your saved documents to answer this reliably."
    monkeypatch.setattr(routes.ollama,"answer",answer)
    response=client.post("/api/chat",json={"question":"What is not in this note?"})
    assert response.status_code==200
    assert response.json()["insufficient_context"] is True
    assert response.json()["sources"][0]["filename"]=="notes.txt"

def test_cors_allows_localhost_and_loopback_frontend(client):
    for origin in ("http://localhost:5173","http://127.0.0.1:5173"):
        response=client.get("/api/health",headers={"Origin":origin})
        assert response.headers["access-control-allow-origin"]==origin

def test_explicit_memory_is_saved_listed_deduplicated_and_deleted(client, monkeypatch):
    response=client.post("/api/chat",json={"question":"Remember that my preferred editor is VS Code."})
    assert response.status_code==200
    assert "Saved to your memory" in response.json()["answer"]
    items=client.get("/api/memories").json()
    assert len(items)==1 and items[0]["content"]=="my preferred editor is VS Code"
    duplicate=client.post("/api/chat",json={"question":"Remember that my preferred editor is VS Code."})
    assert duplicate.status_code==200
    case_variant=client.post("/api/chat",json={"question":"Remember that MY PREFERRED EDITOR IS vs code."})
    assert case_variant.status_code==200
    assert len(client.get("/api/memories").json())==1
    assert client.get("/api/dashboard").json()["memories"]==1
    memory_id=items[0]["id"]
    assert client.delete("/api/memories/"+memory_id).json()=={"deleted":True}
    assert client.get("/api/memories").json()==[]

def test_personal_memory_is_retrieved_before_documents(client, monkeypatch):
    client.post("/api/chat",json={"question":"Remember that my preferred editor is VS Code."})
    monkeypatch.setattr(routes,"search",lambda *_: (_ for _ in ()).throw(AssertionError("document retrieval should not run")))
    async def answer(question,hits):
        assert "VS Code" in hits[0]["text"]
        return "Your preferred editor is VS Code [1]."
    monkeypatch.setattr(routes.ollama,"answer_memories",answer)
    response=client.post("/api/chat",json={"question":"What is my preferred editor?"})
    assert response.status_code==200
    assert response.json()["sources"][0]["filename"]=="Saved memory"

def test_remember_request_can_save_multiple_facts(client):
    response=client.post("/api/chat",json={"question":"Remember this: Project deadline is Friday; I use Python 3.12."})
    assert response.status_code==200
    assert {row["content"] for row in client.get("/api/memories").json()}=={"Project deadline is Friday","I use Python 3.12"}

def test_memory_persistence_failure_returns_clear_error(client,monkeypatch):
    def fail_connect(): raise sqlite3.OperationalError("storage unavailable")
    import sqlite3
    monkeypatch.setattr(routes,"connect",fail_connect)
    response=client.post("/api/chat",json={"question":"Remember that my theme is dark."})
    assert response.status_code==500
    assert response.json()["detail"]=="Could not save that fact to local memory. Check local storage and try again."

def test_invalid_chat_and_missing_resources_return_validation_errors(client):
    assert client.post("/api/chat",json={"question":""}).status_code==422
    assert client.get("/api/documents/missing").status_code==404
    assert client.delete("/api/documents/missing").status_code==404
    assert client.delete("/api/memories/missing").status_code==404

def test_weak_nearest_document_match_is_rejected(client,monkeypatch):
    monkeypatch.setattr(routes,"search",lambda *_:[{"text":"Unrelated content","distance":0.72,"metadata":{"document_id":"d","filename":"unrelated.md","page":0}}])
    response=client.post("/api/chat",json={"question":"What is the deadline?"})
    assert response.status_code==200
    assert response.json()["insufficient_context"] is True
    assert response.json()["sources"]==[]

def test_chroma_distance_conversion_uses_metric():
    assert routes.relevance(0.2,"cosine")==pytest.approx(0.8)
    assert routes.relevance(0.2,"ip")==pytest.approx(0.8)
    assert routes.relevance(1.0,"l2")==pytest.approx(0.5)

def test_synthetic_pdf_and_markdown_ingest_with_source_page_metadata(client,monkeypatch):
    monkeypatch.setattr(routes,"add",lambda *_:None)
    async def no_memories(*_): return None
    monkeypatch.setattr(routes,"extract_memories",no_memories)
    from pathlib import Path
    fixtures=Path(__file__).resolve().parents[2]/"tests"/"fixtures"
    for filename,content_type in (("test-study-notes.pdf","application/pdf"),("test-project-notes.md","text/markdown")):
        response=client.post("/api/documents/upload",files={"file":(filename,(fixtures/filename).read_bytes(),content_type)})
        assert response.status_code==200
        assert response.json()["chunk_count"]>=1
    rows=client.get("/api/documents").json()
    assert {row["filename"] for row in rows}=={"test-study-notes.pdf","test-project-notes.md"}
