import hashlib, uuid
import re
import logging
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.core.config import settings
from app.database.sqlite import connect
from app.schemas import ChatRequest, ChatResponse, Source
from app.services.extract import extract
from app.services.chunking import chunk_pages
from app.services.vector_store import add, search, remove_document, collection, relevance
from app.services.memory import extract_memories
from app.services.embeddings import encode
from app.services import ollama

router = APIRouter(prefix="/api")
logger=logging.getLogger(__name__)
ALLOWED = {".pdf":"pdf", ".txt":"txt", ".md":"md"}
REFUSAL = "I couldn't find sufficiently relevant information in your saved memories or documents."
REMEMBER = re.compile(r"^\s*(?:remember(?:\s+that|\s+this)?|don't\s+forget(?:\s+that)?|do\s+not\s+forget(?:\s+that)?|save\s+this\s+for\s+later|keep\s+this\s+in\s+my\s+memory)\s*[:,-]?\s*(.+?)\s*[.!?]*\s*$", re.I)

def _memory_intent(question):
    match = REMEMBER.match(question)
    if not match:
        return []
    content = match.group(1).strip()
    # Split explicit lists while preserving ordinary punctuation inside a fact.
    facts = [part.strip(" \t,.;:-") for part in re.split(r"\s*(?:;|\n|\band\s+(?=(?:my|i\b|the\b)))\s*", content, flags=re.I)]
    return [fact[:1000] for fact in facts if fact]

def _memory_hits(question):
    with connect() as db:
        rows = [dict(row) for row in db.execute("""
            SELECT id,content,kind,created_at,'personal' document_id,'Saved memory' filename,0 page FROM personal_memories
            UNION ALL
            SELECT m.id,m.content,m.kind,m.created_at,d.id document_id,d.filename,m.page
            FROM memories m JOIN documents d ON d.id=m.document_id
            ORDER BY created_at DESC
        """)]
    if not rows:
        return []
    if re.search(r"what did i ask you to remember|what do you remember|list my memories|what have i asked you to remember", question, re.I):
        return [{"text":row["content"],"distance":0.0,"metadata":{"document_id":row["document_id"],"filename":row["filename"],"page":row["page"] or 0,"chunk_index":0}} for row in rows[:5]]
    vectors = encode([question, *(row["content"] for row in rows)])
    query = vectors[0]
    scored = []
    for row, vector in zip(rows, vectors[1:]):
        # Embeddings are normalized by encode(), so their dot product is cosine
        # similarity. A separate cutoff prevents returning an unrelated nearest fact.
        similarity = sum(a * b for a, b in zip(query, vector))
        if similarity >= settings.memory_min_similarity:
            scored.append((similarity, row))
    scored.sort(key=lambda item: (item[0], item[1]["created_at"]), reverse=True)
    return [{"text":row["content"],"distance":1-score,"metadata":{"document_id":row["document_id"],"filename":row["filename"],"page":row["page"] or 0,"chunk_index":0}} for score,row in scored[:5]]

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
        logger.error("Document processing failed (document_id=%s, error_type=%s)",doc_id,type(exc).__name__)
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
    facts = _memory_intent(body.question)
    if facts:
        now=datetime.now(timezone.utc).isoformat()
        saved=[]
        try:
            with connect() as db:
                for fact in facts:
                    memory_id=str(uuid.uuid4())
                    db.execute("INSERT OR IGNORE INTO personal_memories(id,content,kind,created_at) VALUES(?,?,?,?)",(memory_id,fact,"fact",now))
                    existing=db.execute("SELECT id,content FROM personal_memories WHERE content=? COLLATE NOCASE",(fact,)).fetchone()
                    if not existing: raise RuntimeError("saved row verification returned no record")
                    saved.append(existing["content"])
                persisted=db.execute("SELECT COUNT(*) FROM personal_memories WHERE content IN ("+",".join("?" for _ in saved)+")",saved).fetchone()[0]
        except Exception as exc:
            logger.error("Personal memory persistence failed (error_type=%s)",type(exc).__name__)
            raise HTTPException(500,"Could not save that fact to local memory. Check local storage and try again.") from exc
        if persisted != len(set(s.lower() for s in saved)):
            raise HTTPException(500,"The memory could not be verified after saving. Please try again.")
        return {"answer":f"Saved to your memory: {'; '.join(saved)}","sources":[],"insufficient_context":False}
    try:
        memories=_memory_hits(body.question)
    except RuntimeError as exc:
        raise HTTPException(503,str(exc)) from exc
    if memories:
        try: text=await ollama.answer_memories(body.question,memories)
        except RuntimeError as exc: raise HTTPException(503,str(exc)) from exc
        sources=[Source(document_id=h["metadata"]["document_id"],filename=h["metadata"]["filename"],page=h["metadata"]["page"] or None,passage=h["text"],relevance=round(relevance(h["distance"]),3)) for h in memories]
        return {"answer":text,"sources":sources,"insufficient_context":False}
    hits=search(body.question,settings.retrieval_count)
    # Chroma returns distances rather than similarities. Convert using the
    # metric attached to the collection and reject weak nearest neighbors.
    hits=[h for h in hits if relevance(h["distance"]) >= settings.retrieval_min_similarity]
    if not hits: return {"answer":REFUSAL,"sources":[],"insufficient_context":True}
    try:
        text=await ollama.answer(body.question,hits)
    except RuntimeError as exc:
        raise HTTPException(503,str(exc)) from exc
    insufficient=bool(re.search(r"couldn.t find enough relevant information|not enough information|insufficient information", text.lower()))
    if insufficient:
        text=REFUSAL
    sources=[Source(document_id=h["metadata"]["document_id"],filename=h["metadata"]["filename"],page=h["metadata"]["page"] or None,passage=h["text"],relevance=round(relevance(h["distance"]),3)) for h in hits]
    return {"answer":text,"sources":sources,"insufficient_context":insufficient}

@router.get("/memories")
def memories():
    with connect() as db:
        extracted=[dict(r) for r in db.execute("SELECT m.id,m.content,m.kind,m.page,m.created_at,d.id document_id,d.filename FROM memories m JOIN documents d ON d.id=m.document_id")]
        personal=[dict(r) for r in db.execute("SELECT id,content,kind,NULL page,created_at,'personal' document_id,'Saved memory' filename FROM personal_memories")]
    return sorted(extracted+personal,key=lambda r:r["created_at"],reverse=True)

@router.delete("/memories/{memory_id}")
def delete_memory(memory_id:str):
    with connect() as db:
        cur=db.execute("DELETE FROM memories WHERE id=?",(memory_id,))
        if cur.rowcount==0: cur=db.execute("DELETE FROM personal_memories WHERE id=?",(memory_id,))
    if cur.rowcount==0: raise HTTPException(404,"Memory not found.")
    return {"deleted":True}

@router.get("/dashboard")
def dashboard():
    with connect() as db:
        docs=db.execute("SELECT COUNT(*) FROM documents").fetchone()[0]; mem=db.execute("SELECT (SELECT COUNT(*) FROM memories)+(SELECT COUNT(*) FROM personal_memories)").fetchone()[0]
        recent=[dict(r) for r in db.execute("SELECT event,detail,created_at FROM activity ORDER BY id DESC LIMIT 8")]
        return {"documents":docs,"memories":mem,"chunks":collection.count(),"recent_activity":recent,"recent_documents":[dict(r) for r in db.execute("SELECT id,filename,file_type,size,status,created_at FROM documents ORDER BY created_at DESC LIMIT 5")]}
