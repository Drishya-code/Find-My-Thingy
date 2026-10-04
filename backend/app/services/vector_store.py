import chromadb
from app.core.config import settings
from app.services.embeddings import encode

client = chromadb.PersistentClient(path=str(settings.data_dir / "chroma"))
collection = client.get_or_create_collection("recall_chunks", metadata={"hnsw:space": "cosine"})
DISTANCE_METRIC = (collection.metadata or {}).get("hnsw:space", "l2").lower()

def relevance(distance, metric=DISTANCE_METRIC):
    """Convert Chroma distances to a 0..1 estimate using this collection's metric."""
    distance=max(0.0,float(distance))
    if metric.lower() == "l2":
        return 1.0/(1.0+distance)
    # Chroma cosine and inner-product distances are represented as 1 - similarity.
    return max(0.0,min(1.0,1.0-distance))

def add(document_id, filename, chunks):
    if not chunks: return
    ids = [f"{document_id}:{c['index']}" for c in chunks]
    collection.add(ids=ids, documents=[c["text"] for c in chunks], embeddings=encode([c["text"] for c in chunks]),
                   metadatas=[{"document_id": document_id, "filename": filename, "chunk_index": c["index"], "page": c["page"] or 0} for c in chunks])

def search(question, count=5):
    if collection.count() == 0: return []
    result = collection.query(query_embeddings=encode([question]), n_results=min(count, collection.count()), include=["documents", "metadatas", "distances"])
    hits = []
    for text, metadata, distance in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
        hits.append({"text": text, "metadata": metadata, "distance": distance})
    return hits

def remove_document(document_id):
    collection.delete(where={"document_id": document_id})
