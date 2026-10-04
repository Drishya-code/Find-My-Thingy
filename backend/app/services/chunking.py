from app.core.config import settings

def chunk_pages(pages):
    size, overlap = settings.chunk_words, settings.chunk_overlap_words
    output = []
    for page, text in pages:
        words = text.split()
        start = 0
        while start < len(words):
            end = min(start + size, len(words))
            body = " ".join(words[start:end]).strip()
            if body:
                output.append({"text": body, "page": page, "index": len(output)})
            if end >= len(words):
                break
            start = max(start + 1, end - overlap)
    return output
