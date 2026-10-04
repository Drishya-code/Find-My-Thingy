import re
import fitz

def clean(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.replace("\x00", "")).strip()

def extract(path, file_type: str):
    if file_type == "pdf":
        pages = []
        with fitz.open(path) as pdf:
            for i, page in enumerate(pdf):
                pages.append((i + 1, clean(page.get_text("text"))))
        return [(p, t) for p, t in pages if t]
    text = path.read_text(encoding="utf-8", errors="replace")
    return [(None, clean(text))] if clean(text) else []
