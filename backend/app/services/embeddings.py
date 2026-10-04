from functools import lru_cache
import os
from app.core.config import settings

os.environ.setdefault("HF_HOME", str(settings.data_dir / "models"))
from sentence_transformers import SentenceTransformer

@lru_cache(maxsize=1)
def model():
    return SentenceTransformer(settings.embedding_model, local_files_only=True)

def encode(texts):
    return model().encode(texts, normalize_embeddings=True).tolist()
