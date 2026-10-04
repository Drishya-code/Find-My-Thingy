import hashlib, uuid
import re
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.core.config import settings
from app.database.sqlite import connect
from app.schemas import ChatRequest, ChatResponse, Source
from app.services.extract import extract
from app.services.chunking import chunk_pages
from app.services.vector_store import add, search, remove_document, collection
from app.services.memory import extract_memories
from app.services import ollama

router = APIRouter(prefix="/api")
ALLOWED = {".pdf":"pdf", ".txt":"txt", ".md":"md"}

@router.get("/health")
async def health():
    try:
        with connect() as db: db.execute("SELECT 1").fetchone()
        sqlite = True
    except Exception: sqlite = False
    try: chroma = collection.count() >= 0
    except Exception: chroma = False
    ai = await ollama.status()
    return {"backend":"ok", "sqlite":"ok" if sqlite else "error", "chromadb":"ok" if chroma else "error", "ollama":"ok" if ai["connected"] else "unavailable", "gemma_model":"ok" if ai["model_available"] else "unavailable", "model":settings.ollama_model}

@router.post("/documents/upload")
async def upload(file: UploadFile = File(...)):
    name = Path(file.filename or "document").name
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED: raise HTTPException(400, "Only PDF, TXT and Markdown files are supported.")
    payload = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(payload) > settings.max_upload_mb * 1024 * 1024: raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB limit.")
    digest=hashlib.sha256(payload).hexdigest()
    with connect() as db:
        existing=db.execute("SELECT id FROM documents WHERE sha256=?",(digest,)).fetchone()
    if existing: raise HTTPException(409, "This file is already in your library.")
    doc_id=str(uuid.uuid4()); safe=f"{doc_id}{ext}"; target=settings.data_dir/"uploads"/safe
    target.write_bytes(payload)
    now=datetime.now(timezone.utc).isoformat()
    try:
        pages=extract(target,ALLOWED[ext])
        if not pages: raise HTTPException(422,"No readable text was found in this document. Scanned PDFs are not supported yet.")
        chunks=chunk_pages(pages)
        with connect() as db:
            db.execute("INSERT INTO documents (id,filename,safe_name,file_type,size,sha256,status,chunk_count,created_at) VALUES (?,?,?,?,?,?,?,?,?)",(doc_id,name,safe,ALLOWED[ext],len(payload),digest,"processing",0,now))
        add(doc_id,name,chunks)
        with connect() as db: db.execute("UPDATE documents SET status='ready',chunk_count=? WHERE id=?",(len(chunks),doc_id))
        await extract_memories(doc_id,name,chunks)
        with connect() as db: db.execute("INSERT INTO activity(event,detail,created_at) VALUES('uploaded',?,?)",(name,now))
        return {"id":doc_id,"filename":name,"status":"ready","chunk_count":len(chunks),"size":len(payload),"created_at":now}
    except Exception as exc:
        try: remove_document(doc_id)
        except Exception: pass
        with connect() as db:
            db.execute("DELETE FROM memories WHERE document_id=?", (doc_id,))
            db.execute("DELETE FROM documents WHERE id=?", (doc_id,))
        target.unlink(missing_ok=True)
        if isinstance(exc,HTTPException): raise exc
        raise HTTPException(422,"Document processing failed. Check that the file is valid and try again.") from exc

@router.get("/documents")
def documents():
    with connect() as db: return [dict(r) for r in db.execute("SELECT id,filename,file_type,size,status,chunk_count,created_at,error FROM documents ORDER BY created_at DESC")]

@router.get("/documents/{doc_id}")
def document(doc_id:str):
    with connect() as db: row=db.execute("SELECT id,filename,file_type,size,status,chunk_count,created_at,error FROM documents WHERE id=?",(doc_id,)).fetchone()
    if not row: raise HTTPException(404,"Document not found.")
    return dict(row)

@router.delete("/documents/{doc_id}")
def delete_document(doc_id:str):
    with connect() as db: row=db.execute("SELECT safe_name,filename FROM documents WHERE id=?",(doc_id,)).fetchone()
    if not row: raise HTTPException(404,"Document not found.")
    remove_document(doc_id)
    target=(settings.data_dir/"uploads"/row["safe_name"]).resolve()
    if target.parent == (settings.data_dir/"uploads").resolve(): target.unlink(missing_ok=True)
    with connect() as db:
        db.execute("DELETE FROM memories WHERE document_id=?",(doc_id,)); db.execute("DELETE FROM documents WHERE id=?",(doc_id,))
        db.execute("DELETE FROM activity WHERE detail=?",(row['filename'],))
        db.execute("INSERT INTO activity(event,detail,created_at) VALUES('deleted','A document was removed',?)",(datetime.now(timezone.utc).isoformat(),))
    return {"deleted":True}

@router.post("/chat", response_model=ChatResponse)
async def chat(body:ChatRequest):
    hits=search(body.question,settings.retrieval_count)
    hits=[h for h in hits if 1-h["distance"] >= 0.22]
    if not hits: return {"answer":"I couldn't find enough relevant information in your saved documents to answer this reliably.","sources":[],"insufficient_context":True}
    try:
        text=await ollama.answer(body.question,hits)
    except RuntimeError as exc:
        raise HTTPException(503,str(exc)) from exc
    insufficient=bool(re.search(r"couldn.t find enough relevant information|not enough information|insufficient information", text.lower()))
    if insufficient:
        text="I couldn't find enough relevant information in your saved documents to answer this reliably."
    sources=[Source(document_id=h["metadata"]["document_id"],filename=h["metadata"]["filename"],page=h["metadata"]["page"] or None,passage=h["text"],relevance=round(1-h["distance"],3)) for h in hits]
    return {"answer":text,"sources":sources,"insufficient_context":insufficient}

@router.get("/memories")
def memories():
    with connect() as db: return [dict(r) for r in db.execute("SELECT m.id,m.content,m.kind,m.page,m.created_at,d.id document_id,d.filename FROM memories m JOIN documents d ON d.id=m.document_id ORDER BY m.created_at DESC")]

@router.delete("/memories/{memory_id}")
def delete_memory(memory_id:str):
    with connect() as db: cur=db.execute("DELETE FROM memories WHERE id=?",(memory_id,))
    if cur.rowcount==0: raise HTTPException(404,"Memory not found.")
    return {"deleted":True}

@router.get("/dashboard")
def dashboard():
    with connect() as db:
        docs=db.execute("SELECT COUNT(*) FROM documents").fetchone()[0]; mem=db.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        recent=[dict(r) for r in db.execute("SELECT event,detail,created_at FROM activity ORDER BY id DESC LIMIT 8")]
        return {"documents":docs,"memories":mem,"chunks":collection.count(),"recent_activity":recent,"recent_documents":[dict(r) for r in db.execute("SELECT id,filename,file_type,size,status,created_at FROM documents ORDER BY created_at DESC LIMIT 5")]}
